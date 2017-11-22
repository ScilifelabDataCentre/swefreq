-- Patches a database that is using the master checkout of the
-- swefreq.sql schema definition to the develop version.

-- Add some unique constraints
ALTER TABLE study ADD
    CONSTRAINT UNIQUE (pi_email, title);
ALTER TABLE dataset_version ADD
    CONSTRAINT UNIQUE (dataset_pk, version);
ALTER TABLE collection ADD
    CONSTRAINT UNIQUE (name, ethnicity);
ALTER TABLE sample_set ADD
    CONSTRAINT UNIQUE (dataset_pk, collection_pk);
ALTER TABLE dataset_file ADD
    CONSTRAINT UNIQUE (uri);
