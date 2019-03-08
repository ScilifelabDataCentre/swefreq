#!/usr/bin/env python3
import re
import sys
import json
import time
import logging

from datetime import datetime

import modules.browser.lookups
import db
from .data_importer import DataImporter

METRICS = [
    'BaseQRankSum',
    'ClippingRankSum',
    'DP',
    'FS',
    'InbreedingCoeff',
    'MQ',
    'MQRankSum',
    'QD',
    'ReadPosRankSum',
    'VQSLOD'
]

def get_minimal_representation(pos, ref, alt):
    """
    Get the minimal representation of a variant, based on the ref + alt alleles in a VCF
    This is used to make sure that multiallelic variants in different datasets,
    with different combinations of alternate alleles, can always be matched directly.

    Note that chromosome is ignored here - in xbrowse, we'll probably be dealing with 1D coordinates
    Args:
        pos (int): genomic position in a chromosome (1-based)
        ref (str): ref allele string
        alt (str): alt allele string
    Returns:
        tuple: (pos, ref, alt) of remapped coordinate
    """
    pos = int(pos)
    # If it's a simple SNV, don't remap anything
    if len(ref) == 1 and len(alt) == 1:
        return pos, ref, alt
    else:
        # strip off identical suffixes
        while(alt[-1] == ref[-1] and min(len(alt), len(ref)) > 1):
            alt = alt[:-1]
            ref = ref[:-1]
        # strip off identical prefixes and increment position
        while(alt[0] == ref[0] and min(len(alt), len(ref)) > 1):
            alt = alt[1:]
            ref = ref[1:]
            pos += 1
        return pos, ref, alt


class RawDataImporter(DataImporter):
    def __init__(self, settings):
        super().__init__(settings)
        self.dataset_version = None
        self.dataset = None
        self.sampleset = None
        self.counter = {'coverage':None,
                        'variants':None}

    def _set_dataset_info(self):
        """ Save dataset information given as parameters """
        if self.settings.beacon_description:
            self.dataset.description = self.settings.beacon_description
            self.dataset.save()
        if self.settings.assembly_id:
            self.dataset_version.var_call_ref = self.settings.assembly_id
            self.dataset_version.save()
        if self.settings.sampleset_size:
            self.sampleset.sample_size = self.settings.sampleset_size
            self.sampleset.save()
        if self.settings.dataset_size:
            self.dataset.dataset_size = self.settings.dataset_size
            self.dataset.save()

    def _select_dataset_version(self):
        datasets = []

        try:
            ds = db.Dataset.get(short_name=self.settings.dataset)
        except db.Dataset.DoesNotExist:
            print("Select a Dataset to use with this data")
            for dataset in db.Dataset.select():
                print("  {}  : {}".format(dataset.id, dataset.short_name))
                datasets += [dataset]

            selection = -1
            while selection not in [d.id for d in datasets]:
                if selection != -1:
                    print("Please select a number in {}".format([d.id for d in datasets]))
                try:
                    selection = int(input("Please select a dataset: "))
                except ValueError:
                    print("Please select a number in {}".format([d.id for d in datasets]))
            ds = [d for d in datasets if d.id == selection][0]
        logging.info("Using dataset {}".format(ds.short_name))
        self.dataset = ds

        if self.settings.set_vcf_sampleset_size or self.settings.sampleset_size:
            try:
                samplesets = db.SampleSet.select()
                self.sampleset = [s for s in samplesets if s.dataset.id == self.dataset.id][0]
            except IndexError:
                logging.warning("No sample set found for data set {}".format(self.dataset.id))
                logging.warning("Sample size will not be set")
                self.settings.set_vcf_sampleset_size = False
                self.settings.sampleset_size = 0

        versions = []
        for version in db.DatasetVersion.select().where(db.DatasetVersion.dataset == ds):
            versions += [version]

        if not versions:
            raise db.DatasetVersion.DoesNotExist("At least one dataset version required for dataset")

        if len(versions) == 1:
            logging.info("Only one available dataset version, using: {}".format(versions[0].version))
            self.dataset_version = versions[0]
            return

        if self.settings.version:
            # name based version picking
            if self.settings.version.lower() in [v.version.lower() for v in versions]:
                selected = [v for v in versions if v.version.lower() == self.settings.version.lower()][0]
                self.dataset_version = selected
                logging.info("Using dataset version {}".format(self.dataset_version.version))
                return

            # date-based version picking
            # note that this only works if the version string is formatted like:
            # yyyymmdd or yyyy-mm-dd

            target = self.settings.version
            version_dates = []
            for v in versions:
                try:
                    version_dates += [(datetime.strptime(v.version, "%Y-%m-%d"), v)]
                except ValueError:
                    try:
                        version_dates += [(datetime.strptime(v.version, "%Y%m%d"), v)]
                    except ValueError:
                        pass
            if target not in ["latest", "next"]:
                try:
                    target = datetime.strptime(target, "%Y-%m-%d")
                except ValueError:
                    pass
                try:
                    target = datetime.strptime(target, "%Y%m%d")
                except ValueError:
                    pass
                for date, version in version_dates:
                    if target == date:
                        self.dataset_version = version
                        logging.info("Using dataset version {}".format(self.dataset_version.version))
                        return
            else:
                today = datetime.today()
                if target == "latest":
                    try:
                        target, version = max([i for i in version_dates if i[0] < today])
                        self.dataset_version = version
                        logging.info("Using dataset version {}".format(self.dataset_version.version))
                        return
                    except ValueError:
                        pass
                elif target == "next":
                    try:
                        target, version = min([i for i in version_dates if i[0] > today])
                        self.dataset_version = version
                        logging.info("Using dataset version {}".format(self.dataset_version.version))
                        return
                    except ValueError:
                        logging.warning("No future dataset versions found!")

        print("Select a Version of this dataset to use")
        for version in versions:
            print("  {}  : {}".format(version.id, version.version))

        selection = -1
        while selection not in [v.id for v in versions]:
            if selection != -1:
                print("Please select a number in {}".format([v.id for v in versions]))
            try:
                selection = int(input("Please select a version: "))
            except ValueError:
                print("Please select a number in {}".format([v.id for v in versions]))

        logging.info("Using dataset version {}".format(self.dataset_version))
        self.dataset_version = [v for v in versions if v.id == selection][0]

    def _insert_coverage(self):
        """
        Header columns are chromosome, position, mean coverage, median coverage,
        and then coverage under 1, 5 10, 15, 20, 25, 30, 50, 100.
        """
        start = time.time()
        header = [('chrom', str), ('pos', int), ('mean', float),
                  ('median', float), ('cov1', float), ('cov5', float),
                  ('cov10', float), ('cov15', float), ('cov20', float), ('cov25', float),
                  ('cov30', float), ('cov50', float), ('cov100', float)]
        logging.info("Inserting Coverage")
        batch = []
        last_progress = 0.0
        counter = 0
        with db.database.atomic():
            for filename in self.settings.coverage_file:
                for line in self._open(filename):
                    line = bytes(line).decode('utf8').strip()
                    if line.startswith("#"):
                        continue

                    data = {}
                    for i, item in enumerate(line.strip().split("\t")):
                        if i == 0:
                            data['dataset_version'] = self.dataset_version
                        data[header[i][0]] = header[i][1](item)

                    if self.counter['coverage'] != None:
                        counter += 1

                    batch += [data]
                    if len(batch) >= self.settings.batch_size:
                        # re-format coverage for batch
                        for i, item in enumerate(batch):
                            batch[i]['coverage'] = [item['cov1'], item['cov5'], item['cov10'],
                                                    item['cov15'], item['cov20'], item['cov25'],
                                                    item['cov30'], item['cov50'], item['cov100']]
                            del batch[i]['cov1']
                            del batch[i]['cov5']
                            del batch[i]['cov10']
                            del batch[i]['cov15']
                            del batch[i]['cov20']
                            del batch[i]['cov25']
                            del batch[i]['cov30']
                            del batch[i]['cov50']
                            del batch[i]['cov100']

                        if not self.settings.dry_run:
                            db.Coverage.insert_many(batch).execute()
                        batch = []
                        # Update progress
                        if self.counter['coverage'] != None:
                            progress = counter / self.counter['coverage']
                            while progress > last_progress + 0.01:
                                if not last_progress:
                                    logging.info("Estimated time to completion: {}".format(self._time_to(start, progress)))
                                    self._print_progress_bar()
                                self._tick()
                                last_progress += 0.01
            if batch and not self.settings.dry_run:
                db.Coverage.insert_many(batch)
        if self.counter['coverage'] != None:
            self._tick(True)
        if not self.settings.dry_run:
            logging.info("Inserted {} coverage records in {}".format(counter, self._time_since(start)))

    def _insert_variants(self):
        """
        Insert variants from a VCF file
        """
        logging.info("Inserting variants%s", " (dry run)" if self.settings.dry_run else "")
        header = [("chrom", str), ("pos", int), ("rsid", str), ("ref", str),
                  ("alt", str), ("site_quality", float), ("filter_string", str)]
        start = time.time()
        batch = []
        genes = []
        transcripts = []

        last_progress = 0.0
        counter = 0
        samples = 0
        vep_field_names = None
        dp_mids = None
        gq_mids = None
        with db.database.atomic():
            for filename in self.settings.variant_file:
                ref_dbid = db.get_reference_dbid_dataset(self.settings.dataset)
                ref_genes = {gene.gene_id: gene.id for gene in (db.Gene.select(db.Gene.id, db.Gene.gene_id)
                                                                .where(db.Gene.reference_set == ref_dbid))}
                ref_transcripts = {tran.transcript_id: tran.id for tran in (db.Transcript
                                                                            .select(db.Transcript.id,
                                                                                    db.Transcript.transcript_id)
                                                                            .join(db.Gene)
                                                                            .where(db.Gene.reference_set == ref_dbid))}
                for line in self._open(filename):
                    line = bytes(line).decode('utf8').strip()

                    if line.startswith("#"):
                        # Check for some information that we need
                        if line.startswith('##INFO=<ID=CSQ'):
                            vep_field_names = line.split('Format: ')[-1].strip('">').split('|')
                        if line.startswith('##INFO=<ID=DP_HIST'):
                            dp_mids = map(float, line.split('Mids: ')[-1].strip('">').split('|'))
                        if line.startswith('##INFO=<ID=GQ_HIST'):
                            gq_mids = map(float, line.split('Mids: ')[-1].strip('">').split('|'))
                        if line.startswith('#CHROM'):
                            samples = len(line.split('\t')[9:])
                        continue

                    if not self.settings.beacon_only:
                        if vep_field_names is None:
                            logging.error("VEP_field_names is empty. Make sure VCF header is present.")
                            sys.exit(1)

                    base = {}
                    for i, item in enumerate(line.strip().split("\t")):
                        if i == 0:
                            base['dataset_version'] = self.dataset_version
                        if i < 7:
                            base[header[i][0]] = header[i][1](item)
                        elif i == 7 or not self.settings.beacon_only:
                            # only parse column 7 (maybe also for non-beacon-import?)
                            info = dict([(x.split('=', 1)) if '=' in x else (x, x) for x in re.split(';(?=\w)', item)])

                    if base["chrom"].startswith('GL') or base["chrom"].startswith('MT'):
                        continue

                    consequence_array = info['CSQ'].split(',') if 'CSQ' in info else []
                    if not self.settings.beacon_only:
                        annotations = [dict(zip(vep_field_names, x.split('|'))) for x in consequence_array if len(vep_field_names) == len(x.split('|'))]

                    alt_alleles = base['alt'].split(",")
                    if base['rsid'].startswith('rs'):
                        rsids = [int(rsid.strip('rs')) for rsid in base['rsid'].split(';')]
                    else:
                        rsids = [None]

                    for i, alt in enumerate(alt_alleles):
                        if not self.settings.beacon_only:
                            vep_annotations = [ann for ann in annotations if int(ann['ALLELE_NUM']) == i + 1]

                        data = dict(base)
                        data['alt'] = alt

                        if len(rsids) <= i:
                            data['rsid'] = rsids[-1]  # same id as the last alternate
                        else:
                            data['rsid'] = rsids[i]

                        an, ac = 'AN_Adj', 'AC_Adj'
                        if 'AN_Adj' not in info:
                            an = 'AN'
                        if 'AC_Adj' not in info:
                            ac = 'AC'

                        data['allele_num'] = int(info[an])
                        data['allele_freq'] = None
                        if 'NS' in info and not samples:
                            # save this unless we already know the sample size
                            samples = int(info['NS'])

                        data['allele_count'] = int(info[ac].split(',')[i])
                        if 'AF' in info and data['allele_num'] > 0:
                            data['allele_freq'] = data['allele_count']/float(info[an])

                        if not self.settings.beacon_only:
                            data['vep_annotations'] = vep_annotations

                            genes.append(list(set({annotation['Gene'] for annotation in vep_annotations if annotation['Gene'][:4] == 'ENSG'})))
                            transcripts.append(list(set({annotation['Feature'] for annotation in vep_annotations if annotation['Feature'][:4] == 'ENST'})))

                        data['orig_alt_alleles'] = [
                            '{}-{}-{}-{}'.format(data['chrom'], *get_minimal_representation(base['pos'], base['ref'], x)) for x in alt_alleles
                        ]
                        try:
                            data['hom_count'] = int(info['AC_Hom'])
                        except KeyError:
                            pass # null is better than 0, as 0 has a meaning
                        except ValueError:
                            data['hom_count'] = int(info['AC_Hom'].split(',')[0]) # parsing Swegen sometimes give e.g. 14,0
                        data['variant_id'] = '{}-{}-{}-{}'.format(data['chrom'], data['pos'], data['ref'], data['alt'])
                        data['quality_metrics'] = dict([(x, info[x]) for x in METRICS if x in info])
                        batch += [data]

                    counter += 1

                    if len(batch) >= self.settings.batch_size:
                        if not self.settings.dry_run:
                            if not self.settings.beacon_only:
                                try:
                                    curr_id = db.Variant.select(db.Variant.id).order_by(db.Variant.id.desc()).limit(1).get().id
                                except db.Variant.DoesNotExist:
                                    # assumes next id will be 1 if table is empty
                                    curr_id = 0

                            db.Variant.insert_many(batch).execute()

                            if not self.settings.beacon_only:
                                last_id = db.Variant.select(db.Variant.id).order_by(db.Variant.id.desc()).limit(1).get().id
                                if  last_id-curr_id == len(batch):
                                    indexes = list(range(curr_id+1, last_id+1))
                                else:
                                    indexes = []
                                    for entry in batch:
                                        indexes.append(db.Variant.select(db.Variant.id).where(db.Variant.variant_id == entry['variant_id']).get().id)
                                self.add_variant_genes(indexes, genes, ref_genes)
                                self.add_variant_transcripts(indexes, transcripts, ref_transcripts)

                        genes = []
                        transcripts = []
                        batch = []
                        # Update progress
                        if self.counter['variants'] != None:
                            progress = counter / self.counter['variants']
                            while progress > last_progress + 0.01:
                                if not last_progress:
                                    self._print_progress_bar()
                                self._tick()
                                last_progress += 0.01


            if batch and not self.settings.dry_run:
                if not self.settings.dry_run:
                    if not self.settings.beacon_only:
                        try:
                            curr_id = db.Variant.select(db.Variant.id).order_by(db.Variant.id.desc()).limit(1).get().id
                        except db.Variant.DoesNotExist:
                            # assumes next id will be 1 if table is empty
                            curr_id = 0

                    db.Variant.insert_many(batch).execute()
                    
                    if not self.settings.beacon_only:
                        last_id = db.Variant.select(db.Variant.id).order_by(db.Variant.id.desc()).limit(1).get().id
                        if  last_id-curr_id == len(batch):
                            indexes = list(range(curr_id+1, last_id+1))
                        else:
                            indexes = []
                            for entry in batch:
                                indexes.append(db.Variant.select(db.Variant.id).where(db.Variant.variant_id == entry['variant_id']).get().id)
                        self.add_variant_genes(indexes, genes, ref_genes)
                        self.add_variant_transcripts(indexes, transcripts, ref_transcripts)

        if self.settings.set_vcf_sampleset_size and samples:
            self.sampleset.sample_size = samples
            self.sampleset.save()

        self.dataset_version.num_variants = counter
        self.dataset_version.save()
        if self.counter['variants'] != None:
            self._tick(True)
        if not self.settings.dry_run:
            logging.info("Inserted {} variant records in {}".format(counter, self._time_since(start)))

    def count_entries(self):
        start = time.time()
        if self.settings.coverage_file:
            self.counter['coverage'] = 0
            logging.info("Counting coverage lines")
            for filename in self.settings.coverage_file:
                for line in self._open(filename):
                    line = bytes(line).decode('utf8').strip()
                    if line.startswith("#"):
                        continue
                    self.counter['coverage'] += 1
            logging.info("Found {:,} coverage lines".format(self.counter['coverage']))

        if self.settings.variant_file:
            self.counter['variants'] = 0
            logging.info("Counting variant lines")
            for filename in self.settings.variant_file:
                for line in self._open(filename):
                    line = bytes(line).decode('utf8').strip()
                    if line.startswith("#"):
                        continue
                    self.counter['variants'] += 1
            logging.info("Found {:,} variants".format(self.counter['variants']))

        logging.info("Counted input data lines in {} ".format(self._time_since(start)))

    def prepare_data(self):
        self._select_dataset_version()

    def start_import(self):
        self._set_dataset_info()
        self._insert_variants()
        if not self.settings.beacon_only:
            self._insert_coverage()

    def add_variant_genes(self, variant_indexes:list, genes_to_add:list, ref_genes:dict):
        batch = []
        for i in range(len(variant_indexes)):
            connected_genes = [{'variant':variant_indexes[i], 'gene':ref_genes[gene]} for gene in genes_to_add[i] if gene]
            batch += connected_genes
        if not self.settings.dry_run:
            db.VariantGenes.insert_many(batch).execute()

    def add_variant_transcripts(self, variant_indexes:list, transcripts_to_add:list, ref_transcripts:dict):
        batch = []
        for i in range(len(variant_indexes)):
            connected_transcripts = [{'variant':variant_indexes[i], 'transcript':ref_transcripts[transcript]}
                                     for transcript in transcripts_to_add[i]]
            batch += connected_transcripts
        if not self.settings.dry_run:
            db.VariantTranscripts.insert_many(batch).execute()
