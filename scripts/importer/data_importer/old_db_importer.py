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
                       'dataset_file':{},
                       'user':{}
                       }

    def _select_reference_set(self, short_name):
        if len(self.reference_sets) == 1:
            logging.info(("Only one reference set is available, {},"
                          "will default to this set for all datasets".format(self.reference_sets[0])))
            return self.reference_sets[0].id
        elif short_name.lower() in [r.name.lower() for r in self.reference_sets]:
            refset = [r for r in self.reference_sets if r.name.lower() == short_name.lower()][0]
            logging.info("Auto-selecting reference set '{}' based on name.".format(refset.name))
            return refset
        else:
            print("Select a reference set to use with this dataset")
            retval = -1
            while retval not in [r.id for r in self.reference_sets]:
                for reference_set in self.reference_sets:
                    print("  {}  : {}".format(reference_set.id, reference_set.name))
                try:
                    retval = int(input("Please select a reference: "))
                except ValueError:
                    print("Please select a number in {}".format([r.id for r in self.reference_sets]))
            return retval

    def _move_collections(self):
        logging.info("Moving Collections")
        for collection in old_db.Collection.select():
            logging.info(" - Moving '{}'".format(collection.name))

            try:
                new_id = db.Collection.get(name = collection.name,
                                           ethnicity = collection.ethnicity).id
            except db.Collection.DoesNotExist:
                if self.settings.dry_run:
                    continue
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
                if self.settings.dry_run:
                    continue
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
            try:
                study_ref_id = self.id_map['study'][dataset.study.study]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                study_ref_id = -1
            try:
                # short_name is unique, so we only really need to check that.
                new_id = db.Dataset.get(study         = study_ref_id,
                                        short_name    = dataset.short_name).id
            except db.Dataset.DoesNotExist:
                target_reference_id = self._select_reference_set(dataset.short_name)
                if self.settings.dry_run:
                    continue
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
            try:
                dataset_ref_id = self.id_map['dataset'][dataset_file.dataset.dataset]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                dataset_ref_id = -1
            try:
                db.DatasetLogo.get(dataset  = dataset_ref_id,
                                   mimetype = dataset_file.mimetype,
                                   data     = dataset_file.data)
            except db.DatasetLogo.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.DatasetLogo.insert(dataset  = dataset_ref_id,
                                      mimetype = dataset_file.mimetype,
                                      data     = dataset_file.data).execute()

    def _move_dataset_versions(self):
        logging.info("Moving Dataset Versions")
        for dataset_version in old_db.DatasetVersion.select():
            try:
                dataset_ref_id = self.id_map['dataset'][dataset_version.dataset.dataset]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                dataset_ref_id = -1
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
                if self.settings.dry_run:
                    continue
                new_id = (db.DatasetVersion
                            .insert(dataset           = dataset_ref_id,
                                    version           = dataset_version.version,
                                    description       = dataset_version.description,
                                    terms             = dataset_version.terms,
                                    var_call_ref      = dataset_version.var_call_ref,
                                    available_from    = dataset_version.available_from,
                                    ref_doi           = dataset_version.ref_doi,
                                    data_contact_name = dataset_version.data_contact_name,
                                    data_contact_link = dataset_version.data_contact_link,
                                    coverage_levels   = [1,5,10,15,20,25,30,50,100]
                                    )
                            .execute())

            self.id_map['dataset_version'][dataset_version.dataset_version] = new_id

    def _move_dataset_files(self):
        logging.info("Moving Dataset Files")
        for dataset_file in old_db.DatasetFile.select():
            logging.info(" - Moving '{}'".format(dataset_file.name))
            try:
                dataset_version_ref_id = self.id_map['dataset_version'][dataset_file.dataset_version.dataset_version]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                dataset_version_ref_id = -1
            try:
                new_id = db.DatasetFile.get(dataset_version = dataset_version_ref_id,
                                            name            = dataset_file.name,
                                            uri             = dataset_file.uri,
                                            file_size       = dataset_file.bytes).id
            except db.DatasetFile.DoesNotExist:
                if self.settings.dry_run:
                    continue
                new_id = (db.DatasetFile
                            .insert(dataset_version = dataset_version_ref_id,
                                    name            = dataset_file.name,
                                    uri             = dataset_file.uri,
                                    file_size       = dataset_file.bytes).execute())

            self.id_map['dataset_file'][dataset_file.dataset_file] = new_id

    def _move_sample_sets(self):
        logging.info("Moving Sample Sets")
        for sample_set in old_db.SampleSet.select():
            try:
                dataset_ref_id = self.id_map['dataset'][sample_set.dataset.dataset]
                collection_ref_id = self.id_map['collection'][sample_set.collection.collection]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                dataset_ref_id = -1
                collection_ref_id = -1
            try:
                db.SampleSet.get(dataset     = dataset_ref_id,
                                 collection  = collection_ref_id,
                                 sample_size = sample_set.sample_size,
                                 phenotype   = sample_set.phenotype)
            except db.SampleSet.DoesNotExist:
                if self.settings.dry_run:
                    continue
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

    def _move_users(self):
        logging.info("Moving Users")
        for user in old_db.User.select():
            try:
                new_id = (db.Users
                            .get(name          = user.name,
                                 email         = user.email,
                                 identity      = user.identity,
                                 identity_type = user.identity_type,
                                 affiliation   = user.affiliation,
                                 country       = user.country).id)
            except db.Users.DoesNotExist:
                if self.settings.dry_run:
                    continue
                new_id = (db.Users
                            .insert(name          = user.name,
                                    email         = user.email,
                                    identity      = user.identity,
                                    identity_type = user.identity_type,
                                    affiliation   = user.affiliation,
                                    country       = user.country).execute())

            self.id_map['user'][user.user] = new_id

    def _move_sftp_users(self):
        logging.info("Moving SFTP Users")
        for user in old_db.SFTPUser.select():
            try:
                user_ref_id = self.id_map['user'][user.user.user]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                user_ref_id = -1
            try:
                # user_uid is unique, so we rely on that
                db.SFTPUsers.get(user     = user_ref_id,
                                 user_uid = user.user_uid)
            except db.SFTPUsers.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.SFTPUsers.insert(user            = user_ref_id,
                                    user_uid        = user.user_uid,
                                    user_name       = user.user_name,
                                    password_hash   = user.password_hash,
                                    account_expires = user.account_expires).execute()

    def _move_user_access_logs(self):
        logging.info("Moving User Access Logs")
        for log in old_db.UserAccessLog.select():
            try:
                user_ref_id = self.id_map['user'][log.user.user]
                dataset_ref_id = self.id_map['dataset'][log.dataset.dataset]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                user_ref_id = -1
                dataset_ref_id = -1
            try:
                db.UserAccessLog.get(user    = user_ref_id,
                                     dataset = dataset_ref_id,
                                     action  = log.action,
                                     ts      = log.ts)
            except db.UserAccessLog.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.UserAccessLog.insert(user    = user_ref_id,
                                        dataset = dataset_ref_id,
                                        action  = log.action,
                                        ts      = log.ts).execute()

    def _move_user_consent_logs(self):
        logging.info("Moving User Consent Logs")
        for log in old_db.UserConsentLog.select():
            try:
                user_ref_id = self.id_map['user'][log.user.user]
                version_ref_id = self.id_map['dataset_version'][log.dataset_version.dataset_version]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                user_ref_id = -1
                version_ref_id = -1
            try:
                db.UserConsentLog.get(user            = user_ref_id,
                                     dataset_version = version_ref_id,
                                     ts              = log.ts)
            except db.UserConsentLog.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.UserConsentLog.insert(user            = user_ref_id,
                                        dataset_version = version_ref_id,
                                        ts              = log.ts).execute()

    def _move_user_download_logs(self):
        logging.info("Moving User Download Logs")
        for log in old_db.UserDownloadLog.select():
            try:
                user_ref_id = self.id_map['user'][log.user.user]
                file_ref_id = self.id_map['dataset_file'][log.dataset_file.dataset_file]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                user_ref_id = -1
                file_ref_id = -1
            try:
                db.UserDownloadLog.get(user         = user_ref_id,
                                       dataset_file = file_ref_id,
                                       ts           = log.ts)
            except db.UserDownloadLog.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.UserDownloadLog.insert(user         = user_ref_id,
                                          dataset_file = file_ref_id,
                                          ts           = log.ts).execute()

    def _move_dataset_access(self):
        logging.info("Moving Dataset Access Records")
        for access in old_db.DatasetAccess.select():
            try:
                user_ref_id = self.id_map['user'][access.user.user]
                dataset_ref_id = self.id_map['dataset'][access.dataset.dataset]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                user_ref_id = -1
                dataset_ref_id = -1
            try:
                db.DatasetAccess.get(dataset          = dataset_ref_id,
                                     user             = user_ref_id,
                                     wants_newsletter = access.wants_newsletter,
                                     is_admin         = access.is_admin)
            except db.DatasetAccess.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.DatasetAccess.insert(dataset          = dataset_ref_id,
                                        user             = user_ref_id,
                                        wants_newsletter = access.wants_newsletter,
                                        is_admin         = access.is_admin).execute()

    def _move_linkhashes(self):
        logging.info("Moving Linkhashes")
        for linkhash in old_db.Linkhash.select():
            try:
                user_ref_id = self.id_map['user'][linkhash.user.user]
                version_ref_id = self.id_map['dataset_version'][linkhash.dataset_version.dataset_version]
            except KeyError:
                if not self.settings.dry_run:
                    raise
                user_ref_id = -1
                version_ref_id = -1
            try:
                db.Linkhash.get(dataset_version = version_ref_id,
                                user            = user_ref_id,
                                hash            = linkhash.hash,
                                expires_on      = linkhash.expires_on)
            except db.Linkhash.DoesNotExist:
                if self.settings.dry_run:
                    continue
                db.Linkhash.insert(dataset_version = version_ref_id,
                                   user            = user_ref_id,
                                   hash            = linkhash.hash,
                                   expires_on      = linkhash.expires_on).execute()

    def _move_userbase(self):
        self._move_users()
        self._move_sftp_users()
        self._move_user_access_logs()
        self._move_user_consent_logs()
        self._move_user_download_logs()
        self._move_dataset_access()
        self._move_linkhashes()

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
        self._move_userbase()

        logging.info("Moved data in {}".format(self._time_since(start)))
