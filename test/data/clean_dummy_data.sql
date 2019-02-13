-- Delete test data
DELETE FROM users.user_access_log WHERE id > 1000000 OR dataset > 1000000;
DELETE FROM users.dataset_access  WHERE id > 1000000 OR dataset > 1000000;
DELETE FROM users.users           WHERE id > 1000000;
DELETE FROM data.dataset_files    WHERE id > 1000000;
DELETE FROM data.dataset_versions WHERE id > 1000000;
DELETE FROM data.sample_sets      WHERE id > 1000000;
DELETE FROM data.datasets         WHERE id > 1000000;
DELETE FROM data.reference_sets   WHERE id > 1000000;
DELETE FROM data.dbsnp_versions   WHERE id > 1000000;
DELETE FROM data.collections      WHERE id > 1000000;
DELETE FROM data.studies          WHERE id > 1000000;

-- Reset auto increment counters
ALTER SEQUENCE data.dataset_files_id_seq    RESTART WITH 1;
ALTER SEQUENCE data.dataset_versions_id_seq RESTART WITH 1;
ALTER SEQUENCE data.collections_id_seq      RESTART WITH 1;
ALTER SEQUENCE data.sample_sets_id_seq      RESTART WITH 1;
ALTER SEQUENCE data.datasets_id_seq         RESTART WITH 1;
ALTER SEQUENCE data.studies_id_seq          RESTART WITH 1;
ALTER SEQUENCE users.users_id_seq           RESTART WITH 1;
ALTER SEQUENCE users.user_access_log_id_seq RESTART WITH 1;
ALTER SEQUENCE users.dataset_access_id_seq  RESTART WITH 1;
