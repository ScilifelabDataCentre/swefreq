#!/usr/bin/env python3

import settings
from peewee import (BigIntegerField,
                    BlobField,
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
                )
from playhouse.postgres_ext import ArrayField, BinaryJSONField

database = PostgresqlDatabase(  settings.psql_name,
                                user     = settings.psql_user,
                                password = settings.psql_pass,
                                host     = settings.psql_host,
                                port     = settings.psql_port)

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
    other_names = ArrayField(CharField, null=True)
    canonical_transcript = CharField(null=True, max_length=15)
    chrom = CharField(max_length=10)
    start = IntegerField(db_column="start_pos")
    stop = IntegerField(db_column="stop_pos")
    strand = EnumField(choices=['+','-'])


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

    name       = CharField(null = True)
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

    study              = ForeignKeyField(Study, related_name='datasets')
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

    dataset     = ForeignKeyField(Dataset, related_name='sample_sets')
    collection  = ForeignKeyField(Collection, related_name='sample_sets')
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


class DatasetFile(BaseModel):
    class Meta:
        db_table = 'dataset_files'
        schema = 'data'

    dataset_version = ForeignKeyField(DatasetVersion, db_column="dataset_version", related_name='files')
    name            = CharField(db_column="basename")
    uri             = CharField()
    bytes           = IntegerField()


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
    genes = ArrayField(CharField)
    transcripts = ArrayField(CharField)
    orig_alt_alleles = ArrayField(CharField)
    hom_count = IntegerField()
    allele_freq = FloatField()
    filter_string = CharField()
    variant_id = CharField()
    allele_count = IntegerField()
    allele_num = IntegerField()
    quality_metrics = BinaryJSONField()
    vep_annotations = BinaryJSONField()

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
    chrom = CharField(max_length=10)
    cov1 = FloatField()
    cov5 = FloatField()
    cov10 = FloatField()
    cov15 = FloatField()
    cov20 = FloatField()
    cov25 = FloatField()
    cov30 = FloatField()
    cov50 = FloatField()
    cov100 = FloatField()


class Metrics(BaseModel):
    class Meta:
        db_table = "metrics"
        schema = 'data'

    dataset_version = ForeignKeyField(DatasetVersion, db_column="dataset_version")
    metric = CharField()
    mids = ArrayField(IntegerField)
    hist = ArrayField(IntegerField)
