-- Delete test data
DELETE FROM user_access_log WHERE user_pk         > 1000000 OR dataset_pk > 1000000;
DELETE FROM dataset_access  WHERE user_pk         > 1000000 OR dataset_pk > 1000000;
DELETE FROM user            WHERE user_pk         > 1000000;
DELETE FROM dataset_file    WHERE dataset_file_pk > 1000000;
DELETE FROM dataset_version WHERE dataset_pk      > 1000000;
DELETE FROM sample_set      WHERE sample_set_pk   > 1000000;
DELETE FROM collection      WHERE collection_pk   > 1000000;
DELETE FROM dataset         WHERE dataset_pk      > 1000000;
DELETE FROM study           WHERE study_pk        > 1000000;

-- Reset auto increment counters
ALTER TABLE user_access_log AUTO_INCREMENT = 1;
ALTER TABLE dataset_access  AUTO_INCREMENT = 1;
ALTER TABLE user            AUTO_INCREMENT = 1;
ALTER TABLE dataset_file    AUTO_INCREMENT = 1;
ALTER TABLE dataset_version AUTO_INCREMENT = 1;
ALTER TABLE collection      AUTO_INCREMENT = 1;
ALTER TABLE sample_set      AUTO_INCREMENT = 1;
ALTER TABLE dataset         AUTO_INCREMENT = 1;
ALTER TABLE study           AUTO_INCREMENT = 1;
