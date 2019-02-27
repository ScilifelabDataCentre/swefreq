--------------------------------------------------------------------------------
-- Swefreq data schema                                                        --
--                                                                            --
-- This schema contains the studies and datasets, as well as the actual data  --
-- (reference-data, variants, and coverage) the goes into the Swefreq system. --
--                                                                            --
--------------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS data;

--------------------------------------------------------------------------------
-- dbSNP tables.
--
-- dbSNP datasets are quite large (~200.000.000 entries) and completely separate
-- from the rest of the reference data. In order to minimize the number of dbSNP
-- sets that need to be stored, the dbsnp_version table (which links to the
-- dataset table) allows multiple datasets to use the same dbSNP data.

CREATE TABLE IF NOT EXISTS data.dbsnp_versions (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    version_id varchar(64)
);

CREATE TABLE IF NOT EXISTS data.dbsnp (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    version_id integer REFERENCES data.dbsnp_versions,
    rsid bigint,
    chrom varchar(10),
    pos integer,
    UNIQUE(version_id, rsid)
);

--------------------------------------------------------------------------------
-- Reference Set tables
--

CREATE TABLE IF NOT EXISTS data.reference_sets (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dbsnp_version integer REFERENCES data.dbsnp_versions,
    reference_build varchar UNIQUE,  -- should be ^(GRCh[0-9]+([.]p[0-9]+)?)$
    reference_name varchar,
    ensembl_version varchar,
    gencode_version varchar,
    dbnsfp_version varchar,
    omim_version varchar
);

CREATE TABLE IF NOT EXISTS data.genes (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    reference_set integer REFERENCES data.reference_sets,
    gene_id varchar(15),
    gene_name varchar,
    full_name varchar,
    canonical_transcript varchar(15),
    chrom varchar(10),
    start_pos integer,
    end_pos integer,
    strand varchar
);

CREATE TABLE IF NOT EXISTS data.gene_other_names (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    gene integer REFERENCES data.genes,
    name varchar
);

CREATE TABLE IF NOT EXISTS data.transcripts (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    transcript_id varchar(15),
    gene integer REFERENCES data.genes,
    mim_annotation varchar,
    mim_gene_accession integer,
    chrom varchar(10),
    start_pos integer,
    stop_pos integer,
    strand varchar
);

CREATE TABLE IF NOT EXISTS data.features (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    gene integer REFERENCES data.genes,
    transcript integer REFERENCES data.transcripts,
    chrom varchar(10),
    start_pos integer,
    stop_pos integer,
    strand varchar,
    feature_type varchar
);

--------------------------------------------------------------------------------
-- Study and Dataset fields
--

CREATE TABLE IF NOT EXISTS data.collections (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    study_name varchar,
    ethnicity varchar
);

CREATE TABLE IF NOT EXISTS data.studies (
    id                  integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    pi_name             varchar(100)    NOT NULL,
    pi_email            varchar(100)    NOT NULL,
    contact_name        varchar(100)    NOT NULL,
    contact_email       varchar(100)    NOT NULL,
    title               varchar(100)    NOT NULL,
    study_description   text            DEFAULT NULL,
    publication_date    timestamp       NOT NULL,
    ref_doi             varchar(100),
    UNIQUE (pi_email, title)
);

CREATE TABLE IF NOT EXISTS data.datasets (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    study           integer                 NOT NULL REFERENCES data.studies,
    reference_set   integer                 NOT NULL REFERENCES data.reference_sets,
    short_name      varchar(50)     UNIQUE  NOT NULL,
    full_name       varchar(100)            NOT NULL,
    browser_uri     varchar(200)            DEFAULT NULL,
    beacon_uri      varchar(200)            DEFAULT NULL,
    beacon_description text                 DEFAULT NULL,
    avg_seq_depth   real                    DEFAULT NULL,
    seq_type        varchar(50)             DEFAULT NULL,
    seq_tech        varchar(50)             DEFAULT NULL,
    seq_center      varchar(100)            DEFAULT NULL,
    dataset_size    integer                 NOT NULL CHECK (dataset_size >= 0)
);

CREATE TABLE IF NOT EXISTS data.dataset_logos (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset     integer         NOT NULL REFERENCES data.datasets,
    mimetype    varchar(50)     NOT NULL,
    bytes       bytea           NOT NULL
);

CREATE TABLE IF NOT EXISTS data.sample_sets (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset         integer     NOT NULL REFERENCES data.datasets,
    "collection"    integer     NOT NULL REFERENCES data.collections,
    sample_size     integer     NOT NULL,
    phenotype       varchar(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS data.dataset_versions (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset             integer         NOT NULL REFERENCES data.datasets,
    dataset_version     varchar(20)     NOT NULL,
    dataset_description text            NOT NULL,
    terms               text            NOT NULL,
    var_call_ref        varchar(50)     DEFAULT NULL,
    available_from      timestamp       DEFAULT current_timestamp,
    ref_doi             varchar(100)    DEFAULT NULL,
    data_contact_name   varchar(100)    DEFAULT NULL,
    data_contact_link   varchar(100)    DEFAULT NULL,
    num_variants        integer         DEFAULT NULL,
    coverage_levels     integer[]       DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS data.dataset_files (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset_version     integer                 NOT NULL REFERENCES data.dataset_versions,
    basename            varchar(100)            NOT NULL,
    uri                 varchar(200)    UNIQUE  NOT NULL,
    file_size           bigint                  NOT NULL
);

--------------------------------------------------------------------------------
-- Variant and coverage data fields
--

CREATE TABLE IF NOT EXISTS data.variants (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset_version integer REFERENCES data.dataset_versions,
    variant_type varchar, -- variants go here `"enum": ["DEL", "INS", "DUP", "INV", "CNV", "SNP", "DUP:TANDEM", "DEL:ME", "INS:ME"]`
    rsid integer,
    chrom varchar(10),
    pos integer,
    ref varchar,
    alt varchar,
    site_quality real,
    orig_alt_alleles varchar[],
    hom_count integer,
    allele_freq real,
    filter_string varchar,
    variant_id varchar,
    allele_count integer,
    allele_num integer,
    quality_metrics jsonb,
    vep_annotations jsonb
);

CREATE TABLE IF NOT EXISTS data.variant_genes (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    variant integer REFERENCES data.variants,
    gene integer REFERENCES data.genes
);

CREATE TABLE IF NOT EXISTS data.variant_transcripts (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    variant integer REFERENCES data.variants,
    transcript integer REFERENCES data.transcripts
);

CREATE TABLE IF NOT EXISTS data.coverage (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset_version integer REFERENCES data.dataset_versions,
    chrom varchar(10),
    pos integer,
    mean real,
    median real,
    coverage real[]
);

CREATE TABLE IF NOT EXISTS data.metrics (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset_version integer REFERENCES data.dataset_versions,
    metric varchar,
    mids integer[],
    hist integer
);

--------------------------------------------------------------------------------
-- Data views
--

CREATE OR REPLACE VIEW data.dataset_version_current AS
    SELECT * FROM data.dataset_versions
     WHERE (dataset, id)
        IN (SELECT dataset, MAX(id) FROM data.dataset_versions
             WHERE available_from < now()
             GROUP BY dataset);

--------------------------------------------------------------------------------
-- Indexes
--

CREATE INDEX coverage_pos_chrom ON data.coverage (chrom, pos);
CREATE INDEX dbsnp_chrom_pos ON data.dbsnp (chrom, pos);
CREATE INDEX dbsnp_rsid ON data.dbsnp (rsid);
CREATE INDEX features_transcript ON data.features (transcript)
CREATE INDEX features_gene ON data.features (gene)
CREATE INDEX genes_gene_id ON data.genes (gene_id)
CREATE INDEX transcripts_transcript_id ON data.transcripts (transcript_id);
CREATE INDEX variants_chrom_pos ON data.variants (chrom, pos);
CREATE INDEX variants_rsid ON data.variants (rsid);
