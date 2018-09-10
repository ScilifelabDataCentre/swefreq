#!/usr/bin/env python3

import os
import time
import logging
import db
from .data_importer import DataImporter

class DbSNPImporter( DataImporter ):
    """
    Downloads and imports a dbSNP-dataset into the swefreq database.
    """

    URL=("ftp://ftp.ncbi.nlm.nih.gov/snp/organisms/human_9606_{a.dbsnp_version}"
         "_{a.dbsnp_reference}/database/data/organism_data/{a.dbsnp_version}_"
         "SNPChrPosOnRef_{a.dbsnp_number}.bcp.gz")

    def __init__(self, settings):
        super().__init__(settings)
        self.settings.dbsnp_number = 105
        if settings.dbsnp_reference.startswith("GRCh38"):
            self.settings.dbsnp_number = 108
        self.total = None

    def count_entries(self):
        start = time.time()
        self.total = 0
        logging.info("Counting valid lines in file (for progress bar)")
        for line in self.in_file:
            line = line.decode('ascii').strip()
            if line.startswith("#"):
                continue

            if line.count("\t") < 2:
                continue

            if self.chrom and not line.split("\t")[1] == str(self.chrom):
                continue

            self.total += 1
        self.in_file.rewind()
        logging.info("Found {} lines in {}".format(self.total, self._time_since(start)))

    def prepare_data(self):
        url = DbSNPImporter.URL.format(a=self.settings)
        filename = url.split("/")[-1]
        try:
            os.stat( os.path.join(self.download_dir, filename) )
            self.in_file = self._open( os.path.join(self.download_dir, filename) )
        except FileNotFoundError:
            self.in_file = self._download_and_open(url)

    def prepare_version(self):
        version_id = "{a.dbsnp_version}_{a.dbsnp_reference}".format(a=self.settings)
        dbsnp_version, created = db.DbSNP_version.get_or_create(version_id = version_id)
        if created:
            logging.info("Created dbsnp_version '{}'".format(version_id))
        else:
            logging.info("dbsnp_version '{}' already in database".format(version_id))
        return dbsnp_version

    def start_import(self):
        """
        dbsnp-file header is 'rsid', 'chrom', 'position'
        """
        dbsnp_version = self.prepare_version()

        start = time.time()
        last_progress = 0.0
        logging.info("Inserting dbSNP data into database.")

        counter = 0
        batch = []
        with db.database.atomic():
            for line in self.in_file:
                line = line.decode('ascii').strip()
                if line.startswith("#"):
                    continue

                try:
                    rsid, chrom, position = line.split("\t")[:3]
                except ValueError:
                    # we don't care for incomplete entries
                    continue

                if self.chrom and not chrom == self.chrom:
                    continue

                batch += [{ 'version':dbsnp_version,
                            'rsid':rsid,
                            'chrom':chrom,
                            'pos':position}]
                counter += 1

                if self.total != None:
                    progress = counter / self.total
                    while progress > last_progress + 0.01:
                        if not last_progress:
                            logging.info("Estimated time to completion: {}".format(self._time_to(start, progress)))
                            if self.total != None:
                                self._print_progress_bar()
                        self._tick()
                        last_progress += 0.01

                if len(batch) >= self.batch_size:
                    db.DbSNP.insert_many(batch).execute()
                    batch = []
            db.database.commit()
            if batch:
                db.DbSNP.insert_many(batch)
            if self.total != None:
                self._tick(True)
        logging.info("Inserted {} valid lines in {}".format(counter, self._time_since(start)))
