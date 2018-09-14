#!/usr/bin/env python3

import sys
import time
import logging
import db
from peewee import OperationalError, InterfaceError
from . import old_db

from .data_importer import DataImporter

class OldDbImporter( DataImporter ):

    def __init__(self, settings):
        super().__init__(settings)
        self.reference_sets = []
        self.id_map = {'collection':{},
                       'study':{},
                       'dataset':{},
                       'dataset_version':{},
                       }

    def _select_reference_set(self):
        if len(self.reference_sets) == 1:
            logging.info(("Only one reference set is available, "
                          "will default to this set for all datasets"))
            return self.reference_sets[0].id
        else:
            print("Select a reference set to use with this dataset")
            retval = -1
            reflen = len(self.reference_sets)-1
            while retval not in [r.id for r in self.reference_sets]:
                for reference_set in self.reference_sets:
                    print("  {}  : {}".format(reference_set.id, reference_set.name))
                try:
                    retval = int(input("Please select a reference: "))
                except ValueError:
                    print("Please select a number between 0 and {}".format(reflen))
            return retval

    def _move_collections(self):
        logging.info("Moving Collections")
        for collection in old_db.Collection.select():
            logging.info(" - Moving '{}'".format(collection.name))

            try:
                new_id = db.Collection.get(name = collection.name,
                                           ethnicity = collection.ethnicity).id
            except db.Collection.DoesNotExist:
                new_id = (db.Collection
                            .insert(name = collection.name,
                                    ethnicity = collection.ethnicity)
                            .execute())

            self.id_map['collection'][collection.collection] = new_id

    def _move_studies(self):
        logging.info("Moving Studies")
        for study in old_db.Study.select():
            logging.info(" - Moving '{}'".format(study.title))

            try:
                new_id = db.Study.get(pi_name          = study.pi_name,
                                      pi_email         = study.pi_email,
                                      contact_name     = study.contact_name,
                                      contact_email    = study.contact_email,
                                      title            = study.title,
                                      description      = study.description,
                                      publication_date = study.publication_date,
                                      ref_doi          = study.ref_doi).id
            except db.Study.DoesNotExist:
                new_id = (db.Study
                            .insert(pi_name          = study.pi_name,
                                    pi_email         = study.pi_email,
                                    contact_name     = study.contact_name,
                                    contact_email    = study.contact_email,
                                    title            = study.title,
                                    description      = study.description,
                                    publication_date = study.publication_date,
                                    ref_doi          = study.ref_doi)
                            .execute())

            self.id_map['study'][study.study] = new_id

    def _move_datasets(self):
        logging.info("Moving Datasets")
        for dataset in old_db.Dataset.select():
            logging.info(" - Moving '{}'".format(dataset.short_name))
            study_ref_id = self.id_map['study'][dataset.study.study]
            try:
                # short_name is unique, so we only really need to check that.
                new_id = db.Dataset.get(study         = study_ref_id,
                                        short_name    = dataset.short_name).id
            except db.Dataset.DoesNotExist:
                target_reference_id = self._select_reference_set()
                new_id = (db.Dataset
                            .insert(study         = study_ref_id,
                                    reference_set = target_reference_id,
                                    short_name    = dataset.short_name,
                                    full_name     = dataset.full_name,
                                    browser_uri   = dataset.browser_uri,
                                    beacon_uri    = dataset.beacon_uri,
                                    avg_seq_depth = dataset.avg_seq_depth,
                                    seq_type      = dataset.seq_type,
                                    seq_tech      = dataset.seq_tech,
                                    seq_center    = dataset.seq_center,
                                    dataset_size  = dataset.dataset_size)
                            .execute())

            self.id_map['dataset'][dataset.dataset] = new_id

    def _move_dataset_logos(self):
        logging.info("Moving Dataset Logos")
        for dataset_file in old_db.DatasetLogo.select():
            logging.info(" - Moving '{}'".format(dataset_file.mimetype))
            dataset_ref_id = self.id_map['dataset'][dataset_file.dataset.dataset]
            try:
                db.DatasetLogo.get(dataset  = dataset_ref_id,
                                   mimetype = dataset_file.mimetype,
                                   data     = dataset_file.data)
            except db.DatasetLogo.DoesNotExist:
                db.DatasetLogo.insert(dataset  = dataset_ref_id,
                                      mimetype = dataset_file.mimetype,
                                      data     = dataset_file.data).execute()

    def _move_dataset_versions(self):
        logging.info("Moving Dataset Versions")
        for dataset_version in old_db.DatasetVersion.select():
            logging.info(" - Moving '{}:{}'".format(dataset_version.dataset.short_name, dataset_version.version))
            dataset_ref_id = self.id_map['dataset'][dataset_version.dataset.dataset]
            try:
                new_id = db.DatasetVersion.get(dataset           = dataset_ref_id,
                                               version           = dataset_version.version,
                                               description       = dataset_version.description,
                                               terms             = dataset_version.terms,
                                               var_call_ref      = dataset_version.var_call_ref,
                                               available_from    = dataset_version.available_from,
                                               ref_doi           = dataset_version.ref_doi,
                                               data_contact_name = dataset_version.data_contact_name,
                                               data_contact_link = dataset_version.data_contact_link).id
            except db.DatasetVersion.DoesNotExist:
                new_id = (db.DatasetVersion
                            .insert(dataset           = dataset_ref_id,
                                    version           = dataset_version.version,
                                    description       = dataset_version.description,
                                    terms             = dataset_version.terms,
                                    var_call_ref      = dataset_version.var_call_ref,
                                    available_from    = dataset_version.available_from,
                                    ref_doi           = dataset_version.ref_doi,
                                    data_contact_name = dataset_version.data_contact_name,
                                    data_contact_link = dataset_version.data_contact_link)
                            .execute())

            self.id_map['dataset_version'][dataset_version.dataset_version] = new_id

    def _move_dataset_files(self):
        logging.info("Moving Dataset Files")
        for dataset_file in old_db.DatasetFile.select():
            logging.info(" - Moving '{}'".format(dataset_file.name))
            dataset_version_ref_id = self.id_map['dataset_version'][dataset_file.dataset_version.dataset_version]
            try:
                db.DatasetFile.get(dataset_version = dataset_version_ref_id,
                                   name            = dataset_file.name,
                                   uri             = dataset_file.uri,
                                   file_size       = dataset_file.bytes)
            except db.DatasetFile.DoesNotExist:
                db.DatasetFile.insert(dataset_version = dataset_version_ref_id,
                                      name            = dataset_file.name,
                                      uri             = dataset_file.uri,
                                      file_size       = dataset_file.bytes).execute()

    def _move_sample_sets(self):
        logging.info("Moving Sample Sets")
        for sample_set in old_db.SampleSet.select():
            logging.info(" - Moving '{}'".format(sample_set.phenotype))
            dataset_ref_id = self.id_map['dataset'][sample_set.dataset.dataset]
            collection_ref_id = self.id_map['collection'][sample_set.collection.collection]
            try:
                db.SampleSet.get(dataset     = dataset_ref_id,
                                 collection  = collection_ref_id,
                                 sample_size = sample_set.sample_size,
                                 phenotype   = sample_set.phenotype)
            except db.SampleSet.DoesNotExist:
                db.SampleSet.insert(dataset     = dataset_ref_id,
                                    collection  = collection_ref_id,
                                    sample_size = sample_set.sample_size,
                                    phenotype   = sample_set.phenotype).execute()

    def _move_database(self):
        self._move_collections()
        self._move_studies()
        self._move_datasets()
        self._move_dataset_logos()
        self._move_dataset_versions()
        self._move_sample_sets()
        self._move_dataset_files()

    def prepare_data(self):
        """
        Connects to the old and new databases.
        """
        logging.info("Checking connection to old database")
        try:
            old_db.Collection.get()
        except OperationalError:
            logging.error("Could not connect to old database")
            sys.exit(1)
        logging.info("Checking connection to new database")
        try:
            db.ReferenceSet.get()
            for reference_set in db.ReferenceSet.select():
                self.reference_sets += [reference_set]
        except db.ReferenceSet.DoesNotExist:
            logging.error(("Connection works, but no reference sets are available."
                           "use '--add_reference' to add a new reference set and"
                           "Then use this tool again."))
            sys.exit(1)
        except (OperationalError, InterfaceError):
            logging.error("Could not connect to new database")
            sys.exit(1)

    def start_import(self):
        start = time.time()
        self._move_database()

        logging.info("Moved data in {}".format(self._time_since(start)))
