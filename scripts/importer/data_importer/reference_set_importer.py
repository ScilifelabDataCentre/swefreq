#!/usr/bin/env python3

import os
import re
import gzip
import time
import shutil
import logging
import zipfile
import db
from peewee import IntegrityError, fn
from .data_importer import DataImporter

class ReferenceSetImporter( DataImporter ):

    GENCODE = "ftp://ftp.sanger.ac.uk/pub/gencode/Gencode_human/release_{a.gencode_version}/gencode.v{a.gencode_version}.annotation.gtf.gz"
    DBNSFP = "ftp://dbnsfp:dbnsfp@dbnsfp.softgenetics.com/dbNSFPv{a.dbnsfp_version}.zip"
    ENSEMBL = ("ensembldb.ensembl.org", "anonymous", "")

    def __init__(self, settings):
        super().__init__(settings)

        # counters for statistics and progress
        self.numbers = {'genes':None,
                        'transcripts':None,
                        'features':None}
        self.counters = {'genes':0,
                        'transcripts':0,
                        'features':0}

        # dictionaries to hold data while processing
        self.genes = []
        self.transcripts = []
        self.features = []

        # file handlers for later
        self.gencode = None
        self.dbnsfp  = None
        self.omim    = None
        self.ensembl = None

    def _insert_features(self):
        logging.info("Inserting features into database")
        start = time.time()
        self._print_progress_bar()
        last_progress = 0
        batch = []
        with db.database.atomic():
            for i, feature in enumerate(self.features):
                batch += [{'gene':self.gene_db_ids[feature['gene_id']],
                        'transcript':self.transcript_db_ids[feature['transcript_id']],
                        'chrom':feature['chrom'],
                        'start':feature['start'],
                        'stop':feature['stop'],
                        'strand':feature['strand'],
                        'feature_type':feature['feature_type']}]

                if len(batch) % self.batch_size == 0:
                    if not self.settings.dry_run:
                        db.Feature.insert_many(batch).execute()
                    batch = []

                progress = i / len(self.features)
                while progress - last_progress > 0.01:
                    last_progress += 0.01
                    self._tick()
            if len(batch):
                if not self.settings.dry_run:
                    db.Feature.insert_many(batch).execute()
                batch = []
        self._tick(True)

        logging.info("Features inserted in {}".format( self._time_since(start) ))

    def _insert_genes(self):
        logging.info("Inserting genes into database")
        start = time.time()
        self.gene_db_ids = {}
        self._print_progress_bar()
        last_progress = 0
        for i, gene in enumerate(self.genes):
            # As far as I know I can't batch insert these and still get the id's back

            db_gene = db.Gene(  reference_set = self.db_reference,
                                gene_id = gene['gene_id'],
                                name = gene['name'],
                                full_name = gene.get('full_name', None),
                                other_names = gene.get('other_names', None),
                                canonical_transcript = gene.get('canonical_transcript', None),
                                chrom = gene['chrom'],
                                start = gene['start'],
                                stop = gene['stop'],
                                strand = gene['strand']
                            )

            if self.settings.dry_run:
                self.gene_db_ids[gene['gene_id']] = 0
            else:
                db_gene.save()
                self.gene_db_ids[gene['gene_id']] = db_gene.id

            progress = i / len(self.genes)
            while progress - last_progress > 0.01:
                last_progress += 0.01
                self._tick()
        self._tick(True)

        logging.info("Genes inserted in {}".format( self._time_since(start) ))

    def _insert_reference(self):
        version_id = "{a.dbsnp_version}_{a.dbsnp_reference}".format(a=self.settings)

        if self.settings.dry_run:
            try:
                dbsnp_version = db.DbSNP_version.get(version_id = version_id)
                logging.info("Using dbsnp_version '{}'".format(version_id))
            except db.DbSNP_version.DoesNotExist:
                dbsnp_version = db.DbSNP_version.select(fn.Max(db.DbSNP_version.version_id)).get()
                logging.info("Created dbsnp_version '{}'".format(version_id))
        else:
            dbsnp_version, created = db.DbSNP_version.get_or_create(version_id = version_id)
            if created:
                logging.info("Created dbsnp_version '{}'".format(version_id))
            else:
                logging.info("Using dbsnp_version '{}'".format(version_id))

        omim_filename = self.settings.omim_file.split("/")[-1]
        logging.info("inserting reference header")
        self.db_reference = db.ReferenceSet(name = self.settings.ref_name,
                            ensembl_version = self.settings.ensembl_version,
                            gencode_version = self.settings.gencode_version,
                            dbnsfp_version  = self.settings.dbnsfp_version,
                            omim_version    = omim_filename,
                            dbsnp_version   = dbsnp_version.id)


        if self.settings.dry_run:
            max_id = db.ReferenceSet.select(fn.Max(db.ReferenceSet.id)).get()
            if max_id.id is None:
                self.db_reference.id = 0
            else:
                self.db_reference.id = max_id.id + 1
        else:
            self.db_reference.save()
        logging.info("Reference {} created".format(self.db_reference.id))

    def _insert_transcripts(self):
        logging.info("Inserting transcripts into database")
        start = time.time()

        self.transcript_db_ids = {}
        self._print_progress_bar()
        last_progress = 0
        for i, transcript in enumerate(self.transcripts):
            db_transcript = db.Transcript( transcript_id = transcript['transcript_id'],
                                            gene = self.gene_db_ids[transcript['gene_id']],
                                            mim_annotation = transcript.get('mim_annotation', None),
                                            mim_gene_accession = transcript.get('mim_gene_accession', None),
                                            chrom = transcript['chrom'],
                                            start = transcript['start'],
                                            stop = transcript['stop'],
                                            strand = transcript['strand']
                                        )


            if self.settings.dry_run:
                self.transcript_db_ids[transcript['transcript_id']] = 0
            else:
                db_transcript.save()
                self.transcript_db_ids[transcript['transcript_id']] = db_transcript.id

            progress = i / len(self.transcripts)
            while progress - last_progress > 0.01:
                last_progress += 0.01
                self._tick()
        self._tick(True)

        logging.info("Transcripts inserted in {}".format( self._time_since(start) ))

    def _open_dbnsfp(self):
        """
        Downloads (if needed) and opens the given dbNSFP file.

        Only a small part, 'dbNSFP2.9_gene' of the ~13Gb file is needed, but in
        order to get it we have to download the entire file, extract the part
        that we want, and then discard the dbNSFP package.
        """
        logging.info("----- Opening dbNSFP file -----")
        url = ReferenceSetImporter.DBNSFP.format(a=self.settings)
        filename = url.split("/")[-1]
        match = re.match("^\d+.\d+", self.settings.dbnsfp_version)
        if match:
            dbnsfp_gene_version = match.group(0)
        else:
            raise ValueError("Cannot parse dbNSFP version")
        dbnsfp_file = "dbNSFP{}_gene".format(dbnsfp_gene_version)
        logging.info("Using dbNSFP gene file: {}".format(dbnsfp_file))
        dbnsfp_path = os.path.join( self.download_dir, dbnsfp_file )
        dbnsfp_gzip = "{}.gz".format(dbnsfp_path)
        try:
            os.stat( dbnsfp_gzip )
        except FileNotFoundError:
            try:
                package_file = os.path.join( self.download_dir, filename)
                os.stat( package_file )
            except FileNotFoundError:
                self._download( url )
            logging.info("extracting {} from {}".format(dbnsfp_file, package_file))
            package = zipfile.ZipFile(package_file)
            package.extract(dbnsfp_file, self.download_dir)
            logging.info("gzipping {}".format(dbnsfp_file))
            with open( dbnsfp_path, 'rb') as f_in:
                with gzip.open( dbnsfp_gzip, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            logging.info("removing non-zipped file and package file.")
            os.remove(dbnsfp_path)
            os.remove(package_file)
        self.dbnsfp = self._open( dbnsfp_gzip )

    def _open_ensembl(self):
        """
        Connects to the given ensembl database.
        """
        logging.info("----- Opening ensembl database connection -----")
        self.ensembl = self._connect(*(ReferenceSetImporter.ENSEMBL + (self.settings.ensembl_version,)))

    def _open_gencode(self):
        """
        Downloads (if needed) and opens the given gencode file
        """
        logging.info("----- Opening gencode file -----")
        url = ReferenceSetImporter.GENCODE.format(a=self.settings)
        filename = url.split("/")[-1]
        try:
            os.stat( os.path.join(self.download_dir, filename) )
            self.gencode = self._open( os.path.join(self.download_dir, filename) )
        except FileNotFoundError:
            self.gencode = self._download_and_open(url)

    def _open_omim(self):
        """
        We can't download OMIM files, so we just open the given OMIM file
        """
        logging.info("----- Opening OMIM file -----")
        self.omim = self._open( self.settings.omim_file )

    def _read_dbnsfp(self):
        start = time.time()
        header = None
        logging.info("Adding dbNSFP annotation")

        dbnsfp_cache = {}
        for line in self.dbnsfp:
            raw = bytes(line).decode('utf8').strip().split("\t")
            if not header:
                header = raw
                if header:
                    continue

            values = {}
            for i, value in enumerate(raw):
                values[header[i]] = value

            dbnsfp_cache[ values['Ensembl_gene'] ] = {
                'other_names': values['Gene_other_names'],
                'full_name': values['Gene_full_name']
            }
        for i, gene in enumerate(self.genes):
            if gene['gene_id'] in dbnsfp_cache:
                for key, item in dbnsfp_cache[gene['gene_id']].items():
                    if item in ['', '.']:
                        item = None
                    self.genes[i][key] = item

        logging.info("dbNSFP information added in {}.".format( self._time_since(start) ))

    def _read_ensembl(self):
        """
        Reads the ensembl information into the gene dictionary
        """
        query = """SELECT g.stable_id,
                          t.stable_id
                     FROM gene g
                     JOIN transcript t
                   ON (g.canonical_transcript_id = t.transcript_id)
                """
        start = time.time()

        canonical_dict = {}
        logging.info("Pre-fetching all canonical transcripts")
        self.ensembl.execute(query)
        for transcript in self.ensembl.fetchall():
            canonical_dict[transcript[0]] = transcript[1]

        last_progress = 0.0
        if self.numbers['genes'] != None:
            self._print_progress_bar()

        for i, gene in enumerate(self.genes):
            if gene['gene_id'] in canonical_dict:
                self.genes[i]['canonical_transcript'] = canonical_dict[gene['gene_id']]

            self.counters['genes'] += 1
            if self.numbers['genes'] != None:
                progress = i / self.numbers['genes']
                while progress - last_progress > 0.01:
                    last_progress += 0.01
                    self._tick()
        if self.numbers['genes'] != None:
            self._tick(True)
        logging.info("Canonical transcript information from ensembl added in {}.".format( self._time_since(start) ))

    def _read_omim(self):
        start = time.time()
        logging.info("Adding OMIM annotations")

        cache = {}
        header = None
        for line in self.omim:
            raw = bytes(line).decode('utf8').strip().split("\t")
            if not header:
                header = [r.strip() for r in raw]
                if header:
                    continue

            values = {}
            for i, value in enumerate(raw):
                values[header[i]] = value

            if 'MIM Gene Description' not in values:
                continue

            if 'Ensembl Transcript ID' in cache:
                logging.warning(("The Ensembl Transcript ID '{}' was found twice"
                                " in the OMIM file. this was not planned for."))
            cache[values['Ensembl Transcript ID']] = \
                        {'mim_gene_accession':int(values['MIM Gene Accession']),
                        'mim_annotation':values['MIM Gene Description'].strip().capitalize(),
                        }

        counter = 0
        empty = {'mim_gene_accession':None, 'mim_annotation':None}
        for i, transcript in enumerate(self.transcripts):
            if transcript['transcript_id'] in cache:
                self.transcripts[i].update(cache[transcript['transcript_id']])
                counter += 1
            else:
                self.transcripts[i].update(empty)

        logging.info("OMIM information added in {}.".format( self._time_since(start) ))

    def count_entries(self):
        logging.info("Counting features in gencode file (for progress bar)")
        start = time.time()
        self.numbers['genes'] = 0
        self.numbers['transcripts'] = 0
        self.numbers['features'] = 0
        for row in self.gencode:
            raw = bytes(row).decode('ascii').strip()
            if raw[0] == "#":
                continue
            values = raw.split("\t")
            if len(values) < 2:
                continue

            if self.chrom and values[0][3:] not in self.chrom:
                continue

            if values[2] == 'gene':
                self.numbers['genes'] += 1
            elif values[2] == 'transcript':
                self.numbers['transcripts'] += 1
            elif values[2] in ['CDS', 'exon', 'UTR']:
                self.numbers['features'] += 1

        self.gencode.rewind()

        pad = max([len("{:,}".format(self.numbers[t])) for t in ["genes", "transcripts", "features"]])
        logging.info("Parsed file in {:3.1f}s".format(time.time()-start))
        logging.info("Genes      : {0:>{pad},}".format(self.numbers['genes'], pad=pad))
        logging.info("Transcripts: {0:>{pad},}".format(self.numbers['transcripts'], pad=pad))
        logging.info("Features   : {0:>{pad},}".format(self.numbers['features'], pad=pad))

    def prepare_data(self):
        self._open_gencode()
        self._open_dbnsfp()
        self._open_omim()
        self._open_ensembl()

    def start_import(self):
        start = time.time()
        logging.info("Reading gencode data into buffers.")
        last_progress = 0.0
        if self.numbers['genes'] != None:
            self._print_progress_bar()
        for line in self.gencode:
            line = bytes(line).decode('ascii').strip()
            if line.startswith("#"):
                continue
            try:
                values = line.split("\t")

                if self.chrom and values[0][3:] not in self.chrom:
                    continue

                info = dict(x.strip().split() for x in values[8].split(';') if x != '')
                info = {k: v.strip('"') for k, v in info.items()}

                data = {'chrom':values[0][3:],
                        'start':int(values[3]),
                        'stop':int(values[4]),
                        'strand':values[6],
                        'gene_id':info['gene_id'].split('.')[0]}

                # only progress for genes to keep it simple
                if self.numbers['genes'] != None:
                    progress = self.counters['genes'] / self.numbers['genes']
                    while progress - last_progress > 0.01:
                        last_progress += 0.01
                        self._tick()
                if values[2] == 'gene':
                    data['name'] = info['gene_name']
                    self.genes += [data]
                    self.counters['genes'] += 1
                    continue

                data['transcript_id'] = info['transcript_id'].split('.')[0]
                if values[2] == 'transcript':
                    self.transcripts += [data]
                    self.counters['transcripts'] += 1
                    continue

                if values[2] in ['exon', 'CDS', 'UTR']:
                    data['feature_type'] = values[2]
                    self.features += [data]
                    self.counters['features'] += 1
                    continue

            except Exception as e:
                logging.error("{}".format(e))
                break
        if self.numbers['genes'] != None:
            self._tick(True)
        logging.info("Gencode data read into buffers in {}.".format( self._time_since(start) ))
        self._read_ensembl()
        self._read_dbnsfp()
        self._read_omim()
        self._insert_reference()
        self._insert_genes()
        self._insert_transcripts()
        self._insert_features()
