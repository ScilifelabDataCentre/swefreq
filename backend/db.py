#!/usr/bin/env python3

import settings
from peewee import (BigIntegerField,
                    BlobField,
                    BooleanField,
                    CharField,
                    DateTimeField,
                    IntegerField,
                    Field,
                    FloatField,
                    ForeignKeyField,
                    Model,
                    PostgresqlDatabase,
                    PrimaryKeyField,
                    SQL,
                    TextField,
                    fn,
                )
from playhouse.postgres_ext import ArrayField, BinaryJSONField, PostgresqlExtDatabase

database = PostgresqlExtDatabase(settings.psql_name,
                                 user            = settings.psql_user,
                                 password        = settings.psql_pass,
                                 host            = settings.psql_host,
                                 port            = settings.psql_port,
                                 register_hstore = False)

class BaseModel(Model):
    class Meta:
        database = database


class EnumField(Field):
    db_field = 'string' # The same as for CharField

    def __init__(self, choices=None, *args, **kwargs):
        self.values = choices or []
        super().__init__(*args, **kwargs)

    def db_value(self, value):
        if value not in self.values:
            raise ValueError("Illegal value for '{}'".format(self.db_column))
        return value

    def python_value(self, value):
        if value not in self.values:
            raise ValueError("Illegal value for '{}'".format(self.db_column))
        return value

###
# Reference Tables
##

class DbSNP_version(BaseModel):
    """
    dbSNP datasets are very large, and some reference sets can use the same set,
    which is why they are given their own header-table.
    """
    class Meta:
        db_table = 'dbsnp_versions'
        schema = 'data'

    version_id = CharField()


class DbSNP(BaseModel):
    class Meta:
        db_table = 'dbsnp'
        schema = 'data'

    version = ForeignKeyField(DbSNP_version, related_name="variants")
    rsid = BigIntegerField()
    chrom = CharField(max_length=10)
    pos = IntegerField()


class ReferenceSet(BaseModel):
    """
    The gencode, ensembl, dbNSFP and omim data are combined to fill out the
    Gene, Transcript and Feature tables. DbSNP data is separate, and may be
    shared between reference sets, so it uses a foreign key instead.
    """
    class Meta:
        db_table = 'reference_sets'
        schema = 'data'

    dbsnp_version = ForeignKeyField(DbSNP_version, db_column="dbsnp_version", related_name="references")
    name = CharField(db_column="reference_name", null=True)
    ensembl_version = CharField()
    gencode_version = CharField()
    dbnsfp_version = CharField()
    omim_version = CharField()


class Gene(BaseModel):
    class Meta:
        db_table = 'genes'
        schema = 'data'

    reference_set = ForeignKeyField(ReferenceSet, db_column="reference_set", related_name="genes")
    gene_id = CharField(unique=True, max_length=15)
    name = CharField(db_column="gene_name", null=True)
    full_name = CharField(null=True)
    canonical_transcript = CharField(null=True, max_length=15)
    chrom = CharField(max_length=10)
    start = IntegerField(db_column="start_pos")
    stop = IntegerField(db_column="end_pos")
    strand = EnumField(choices=['+','-'])

class GeneOtherNames(BaseModel):
    class Meta:
        db_table = 'gene_other_names'
        schema = 'data'

    gene = ForeignKeyField(Gene, db_column="gene", related_name="other_names")
    name = CharField(null=True)

class Transcript(BaseModel):
    class Meta:
        db_table = 'transcripts'
        schema = 'data'

    transcript_id = CharField(max_length=15)
    gene = ForeignKeyField(Gene, db_column="gene", related_name="transcripts")
    mim_gene_accession = IntegerField()
    mim_annotation = CharField()
    chrom = CharField(max_length=10)
    start = IntegerField(db_column="start_pos")
    stop = IntegerField(db_column="stop_pos")
    strand = EnumField(choices = ['+', '-'])


class Feature(BaseModel):
    class Meta:
        db_table = 'features'
        schema = 'data'

    gene = ForeignKeyField(Gene, db_column="gene", related_name='exons')
    transcript = ForeignKeyField(Transcript, db_column="transcript", related_name='transcripts')
    chrom = CharField(max_length=10)
    start = IntegerField(db_column="start_pos")
    stop = IntegerField(db_column="stop_pos")
    strand = EnumField(choices = ['+', '-'])
    feature_type = CharField()

###
# Study and Dataset fields
##

class Collection(BaseModel):
    """
    A collection is a source of data which can be sampled into a SampleSet.
    """
    class Meta:
        db_table = 'collections'
        schema = 'data'

    name       = CharField(db_column="study_name", null = True)
    ethnicity  = CharField(null = True)


class Study(BaseModel):
    """
    A study is a scientific study with a PI and a description, and may include
    one or more datasets.
    """
    class Meta:
        db_table = 'studies'
        schema = 'data'

    pi_name          = CharField()
    pi_email         = CharField()
    contact_name     = CharField()
    contact_email    = CharField()
    title            = CharField()
    description      = TextField(db_column="study_description", null=True)
    publication_date = DateTimeField()
    ref_doi          = CharField(null=True)


class Dataset(BaseModel):
    """
    A dataset is part of a study, and usually include a certain population.
    Most studies only have a single dataset, but multiple are allowed.
    """
    class Meta:
        db_table = 'datasets'
        schema = 'data'

    study              = ForeignKeyField(Study, db_column="study", related_name='datasets')
    reference_set      = ForeignKeyField(ReferenceSet, db_column="reference_set", related_name='datasets')
    short_name         = CharField()
    full_name          = CharField()
    browser_uri        = CharField(null=True)
    beacon_uri         = CharField(null=True)
    avg_seq_depth      = FloatField(null=True)
    seq_type           = CharField(null=True)
    seq_tech           = CharField(null=True)
    seq_center         = CharField(null=True)
    dataset_size       = IntegerField()

    def has_image(self):
        try:
            DatasetLogo.get(DatasetLogo.dataset == self)
            return True
        except DatasetLogo.DoesNotExist:
            return False


class SampleSet(BaseModel):
    class Meta:
        db_table = 'sample_sets'
        schema = 'data'

    dataset     = ForeignKeyField(Dataset, db_column="dataset", related_name='sample_sets')
    collection  = ForeignKeyField(Collection, db_column="collection", related_name='sample_sets')
    sample_size = IntegerField()
    phenotype   = CharField(null=True)


class DatasetVersion(BaseModel):
    class Meta:
        db_table = 'dataset_versions'
        schema = 'data'

    dataset           = ForeignKeyField(Dataset, db_column="dataset", related_name='versions')
    version           = CharField(db_column="dataset_version")
    description       = TextField(db_column="dataset_description")
    terms             = TextField()
    var_call_ref      = CharField(null=True)
    available_from    = DateTimeField()
    ref_doi           = CharField(null=True)
    data_contact_name = CharField(null=True)
    data_contact_link = CharField(null=True)
    num_variants      = IntegerField(null=True)
    coverage_levels   = ArrayField(IntegerField, null=True)


class DatasetFile(BaseModel):
    class Meta:
        db_table = 'dataset_files'
        schema = 'data'

    dataset_version = ForeignKeyField(DatasetVersion, db_column="dataset_version", related_name='files')
    name            = CharField(db_column="basename")
    uri             = CharField()
    file_size       = IntegerField()


class DatasetLogo(BaseModel):
    class Meta:
        db_table = 'dataset_logos'
        schema = 'data'

    dataset      = ForeignKeyField(Dataset, db_column="dataset", related_name='logo')
    mimetype     = CharField()
    data         = BlobField(db_column="bytes")


###
# Variant and coverage data fields
##

class Variant(BaseModel):
    class Meta:
        db_table = "variants"
        schema = 'data'

    dataset_version = ForeignKeyField(DatasetVersion, db_column="dataset_version", related_name="variants")
    rsid = IntegerField()
    chrom = CharField(max_length=10)
    pos = IntegerField()
    ref = CharField()
    alt = CharField()
    site_quality = FloatField()
    orig_alt_alleles = ArrayField(CharField)
    hom_count = IntegerField()
    allele_freq = FloatField()
    filter_string = CharField()
    variant_id = CharField()
    allele_count = IntegerField()
    allele_num = IntegerField()
    quality_metrics = BinaryJSONField()
    vep_annotations = BinaryJSONField()


class VariantGenes(BaseModel):
    class Meta:
        db_table = 'variant_genes'
        schema = 'data'

    variant = ForeignKeyField(Variant, db_column="variant", related_name="genes")
    gene = ForeignKeyField(Gene, db_column="gene", related_name="variants")


class VariantTranscripts(BaseModel):
    class Meta:
        db_table = 'variant_transcripts'
        schema = 'data'

    gene = ForeignKeyField(Variant, db_column="variant", related_name="transcripts")
    transcript = ForeignKeyField(Transcript, db_column="transcript", related_name="variants")


class Coverage(BaseModel):
    """
    Coverage statistics are pre-calculated for each variant for a given
    dataset.

    The fields show the fraction of a population that reaches the
    mapping coverages given by the variable names.

    ex. cov20 = 0.994 means that 99.4% of the population had at a mapping
        coverage of at least 20 in this position.
    """
    class Meta:
        db_table = "coverage"
        schema = 'data'

    dataset_version = ForeignKeyField(DatasetVersion, db_column="dataset_version")
    chrom = CharField(max_length=10)
    pos = IntegerField()
    mean = FloatField()
    median = FloatField()
    coverage = ArrayField(FloatField, null=True)


class Metrics(BaseModel):
    class Meta:
        db_table = "metrics"
        schema = 'data'

    dataset_version = ForeignKeyField(DatasetVersion, db_column="dataset_version")
    metric = CharField()
    mids = ArrayField(IntegerField)
    hist = ArrayField(IntegerField)


class User(BaseModel):
    class Meta:
        db_table = "users"
        schema = 'users'

    name          = CharField(db_column="username", null=True)
    email         = CharField(unique=True)
    identity      = CharField(unique=True)
    identity_type = EnumField(null=False, choices=['google', 'elixir'])
    affiliation   = CharField(null=True)
    country       = CharField(null=True)

    def is_admin(self, dataset):
        return DatasetAccess.select().where(
                DatasetAccess.dataset == dataset,
                DatasetAccess.user == self,
                DatasetAccess.is_admin
            ).count()

    def has_access(self, dataset):
        return DatasetAccessCurrent.select().where(
                DatasetAccessCurrent.dataset == dataset,
                DatasetAccessCurrent.user    == self,
            ).count()

    def has_requested_access(self, dataset):
        return DatasetAccessPending.select().where(
                DatasetAccessPending.dataset == dataset,
                DatasetAccessPending.user    == self
            ).count()


class SFTPUser(BaseModel):
    class Meta:
        db_table = "sftp_users"
        schema = 'users'

    user          = ForeignKeyField(User, related_name='sftp_user')
    user_uid      = IntegerField(unique=True)
    user_name     = CharField(null=False)
    password_hash = CharField(null=False)
    account_expires = DateTimeField(null=False)


class UserAccessLog(BaseModel):
    class Meta:
        db_table = "user_access_log"
        schema = 'users'

    user            = ForeignKeyField(User, related_name='access_logs')
    dataset         = ForeignKeyField(Dataset, db_column='dataset', related_name='access_logs')
    action          = EnumField(null=True, choices=['access_granted','access_revoked','access_requested','private_link'])
    ts              = DateTimeField()


class UserConsentLog(BaseModel):
    class Meta:
        db_table = "user_consent_log"
        schema = 'users'

    user             = ForeignKeyField(User, related_name='consent_logs')
    dataset_version  = ForeignKeyField(DatasetVersion, db_column='dataset_version', related_name='consent_logs')
    ts               = DateTimeField()


class UserDownloadLog(BaseModel):
    class Meta:
        db_table = "user_download_log"
        schema = 'users'

    user              = ForeignKeyField(User, related_name='download_logs')
    dataset_file      = ForeignKeyField(DatasetFile, db_column='dataset_file', related_name='download_logs')
    ts                = DateTimeField()


class DatasetAccess(BaseModel):
    class Meta:
        db_table = "dataset_access"
        schema = 'users'

    dataset          = ForeignKeyField(Dataset, db_column='dataset', related_name='access')
    user             = ForeignKeyField(User, related_name='dataset_access')
    wants_newsletter = BooleanField(null=True)
    is_admin         = BooleanField(null=True)


class Linkhash(BaseModel):
    class Meta:
        db_table = "linkhash"
        schema = 'users'

    dataset_version = ForeignKeyField(DatasetVersion, db_column='dataset_version', related_name='link_hashes')
    user            = ForeignKeyField(User, related_name='link_hashes')
    hash            = CharField()
    expires_on      = DateTimeField()

#####
# Views
##

class DatasetVersionCurrent(DatasetVersion):
    class Meta:
        db_table = 'dataset_version_current'
        schema = 'data'

    dataset           = ForeignKeyField(Dataset, db_column="dataset", related_name='current_version')


class DatasetAccessCurrent(DatasetAccess):
    class Meta:
        db_table = 'dataset_access_current'
        schema = 'users'

    dataset          = ForeignKeyField(Dataset, db_column='dataset', related_name='access_current')
    user             = ForeignKeyField(User, related_name='access_current')
    has_access       = IntegerField()
    access_requested = DateTimeField()


class DatasetAccessPending(DatasetAccess):
    class Meta:
        db_table = 'dataset_access_pending'
        schema = 'users'

    dataset          = ForeignKeyField(Dataset, db_column='dataset', related_name='access_pending')
    user             = ForeignKeyField(User, related_name='access_pending')
    has_access       = IntegerField()
    access_requested = DateTimeField()

#####
# Help functions
##

def get_next_free_uid():
    """
    Returns the next free uid >= 10000, and higher than the current uid's
    from the sftp_user table in the database.
    """
    default = 10000
    next_uid = default
    try:
        current_max_uid = SFTPUser.select(fn.MAX(SFTPUser.user_uid)).get().user_uid
        if current_max_uid:
            next_uid = current_max_uid+1
    except SFTPUser.DoesNotExist:
        pass

    return next_uid

def get_admin_datasets(user):
    return DatasetAccess.select().where( DatasetAccess.user == user, DatasetAccess.is_admin)

def get_dataset(dataset):
    dataset = Dataset.select().where( Dataset.short_name == dataset).get()
    return dataset

def get_dataset_version(dataset, version=None):
    if version:
        dataset_version = (DatasetVersion
                            .select(DatasetVersion, Dataset)
                            .join(Dataset)
                            .where(DatasetVersion.version == version,
                                   Dataset.short_name == dataset)).get()
    else:
        dataset_version = (DatasetVersionCurrent
                            .select(DatasetVersionCurrent, Dataset)
                            .join(Dataset)
                            .where(Dataset.short_name == dataset)).get()
    return dataset_version

def build_dict_from_row(row):
    d = {}

    for field, value in row.__dict__['_data'].items():
        if field == "id":
            continue
        d[field] = value
    return d
