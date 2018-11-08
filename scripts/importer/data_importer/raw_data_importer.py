#!/usr/bin/env python3

import re
import sys
import json
import time
import logging

from datetime import datetime

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
        while(alt[-1] == ref[-1] and min(len(alt),len(ref)) > 1):
            alt = alt[:-1]
            ref = ref[:-1]
        # strip off identical prefixes and increment position
        while(alt[0] == ref[0] and min(len(alt),len(ref)) > 1):
            alt = alt[1:]
            ref = ref[1:]
            pos += 1
        return pos, ref, alt

class RawDataImporter( DataImporter ):

    def __init__(self, settings):
        super().__init__(settings)
        self.dataset_version = None
        self.counter = {'coverage':None,
                        'variants':None}

    def _select_dataset_version(self):
        datasets = []

        try:
            ds = db.Dataset.get(short_name = self.settings.dataset)
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
        logging.info("Inserted {} coverage records in {}".format(counter, self._time_since(start)))

    def _insert_variants(self):
        logging.info("Inserting variants")
        header = [("chrom",str), ("pos", int), ("rsid", str), ("ref", str),
                  ("alt", str), ("site_quality", float), ("filter_string", str)]
        start = time.time()
        batch = []
        last_progress = 0.0
        counter = 0
        vep_field_names = None
        dp_mids = None
        gq_mids = None
        with db.database.atomic():
            for filename in self.settings.variant_file:
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
                        continue

                    if vep_field_names is None:
                        logging.error("VEP_field_names is empty. Make sure VCF header is present.")
                        sys.exit(1)

                    base = {}
                    for i, item in enumerate(line.strip().split("\t")):
                        if i == 0:
                            base['dataset_version'] = self.dataset_version
                        if i < 7:
                            base[header[i][0]] = header[i][1](item)
                        else:
                            info = dict([(x.split('=', 1)) if '=' in x else (x, x) for x in re.split(';(?=\w)', item)])

                    if base["chrom"].startswith('GL') or base["chrom"].startswith('MT'):
                        continue

                    consequence_array = info['CSQ'].split(',') if 'CSQ' in info else []
                    annotations = [dict(zip(vep_field_names, x.split('|'))) for x in consequence_array if len(vep_field_names) == len(x.split('|'))]

                    alt_alleles = base['alt'].split(",")
                    for i, alt in enumerate(alt_alleles):
                        vep_annotations = [ann for ann in annotations if int(ann['ALLELE_NUM']) == i + 1]

                        data = dict(base)
                        data['alt'] = alt
                        data['rsid'] = int(data['rsid'].strip('rs')) if data['rsid'].startswith('rs') else None
                        data['allele_num']   = int(info['AN_Adj'])
                        data['allele_count'] = int(info['AC_Adj'].split(',')[i])
                        data['allele_freq']  = None
                        if 'AF' in info and data['allele_num'] > 0:
                            data['allele_freq'] = data['allele_count']/float(info['AN_Adj'])

                        data['vep_annotations'] = json.dumps(vep_annotations)
                        data['genes']           = list({annotation['Gene'] for annotation in vep_annotations})
                        data['transcripts']     = list({annotation['Feature'] for annotation in vep_annotations})

                        data['orig_alt_alleles'] = [
                            '{}-{}-{}-{}'.format(data['chrom'], *get_minimal_representation(base['pos'], base['ref'], x)) for x in alt_alleles
                        ]
                        # I don't think this is needed.
                        #data['hom_count']        = 
                        data['variant_id']       = '{}-{}-{}-{}'.format(data['chrom'], data['pos'], data['ref'], data['alt'])
                        data['quality_metrics']  = json.dumps(dict([(x, info[x]) for x in METRICS if x in info]))
                        batch += [data]

                    counter += 1

                    if len(batch) >= self.settings.batch_size:
                        if not self.settings.dry_run:
                            db.Variant.insert_many(batch).execute()
                        batch = []
                        # Update progress
                        if self.counter['variants'] != None:
                            progress = counter / self.counter['variants']
                            while progress > last_progress + 0.01:
                                if not last_progress:
                                    logging.info("Estimated time to completion: {}".format(self._time_to(start, progress)))
                                    self._print_progress_bar()
                                self._tick()
                                last_progress += 0.01
            if batch and not self.settings.dry_run:
                db.Variant.insert_many(batch)
        self.dataset_version.num_variants = counter
        self.dataset_version.save()
        if self.counter['variants'] != None:
            self._tick(True)
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
        self._insert_variants()
        self._insert_coverage()
