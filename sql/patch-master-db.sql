-- Patches a database that is using the master checkout of the
-- swefreq.sql schema definition to the develop version.

-- Add some unique constraints
ALTER TABLE study ADD
    CONSTRAINT UNIQUE (pi_email, title);
ALTER TABLE dataset_version ADD
    CONSTRAINT UNIQUE (dataset_pk, version);
ALTER TABLE collection ADD
    CONSTRAINT UNIQUE (name);
ALTER TABLE sample_set ADD
    CONSTRAINT UNIQUE (dataset_pk, collection_pk);
ALTER TABLE dataset_file ADD
    CONSTRAINT UNIQUE (uri);

-- Add user.identity and user.identity_type

ALTER TABLE user
    ADD COLUMN (
    identity            VARCHAR(100),
    identity_type       ENUM ('google', 'elixir')),
    ADD CONSTRAINT
    UNIQUE (identity, identity_type);

-- Fill the above with existing data

UPDATE user
SET identity_type = 'google';

UPDATE user
SET identity = email;

-- Set those two columns as "NOT NULL"
ALTER TABLE user
MODIFY COLUMN
    identity            VARCHAR(100)    NOT NULL,
MODIFY COLUMN
    identity_type       ENUM ('google', 'elixir')
                                        NOT NULL;

-- Add sftp_user and associated triggers

CREATE TABLE IF NOT EXISTS sftp_user (
    sftp_user_pk        INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    user_pk             INTEGER         NOT NULL,
    user_uid            INTEGER         NOT NULL,
    user_name           VARCHAR(50)     NOT NULL,
    password_hash       VARCHAR(100)    NOT NULL,
    account_expires     TIMESTAMP       NOT NULL,
    CONSTRAINT FOREIGN KEY (user_pk) REFERENCES user(user_pk),
    CONSTRAINT UNIQUE (user_uid)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- Triggers on INSERT and UPDATE of sftp_user.user_uid to make sure the
-- new value is always 10000 or larger.

DELIMITER $$

CREATE TRIGGER check_before_insert BEFORE INSERT ON sftp_user
FOR EACH ROW
IF NEW.user_uid < 10000 THEN
    SIGNAL SQLSTATE '38001'
    SET MESSAGE_TEXT = 'Check constraint failed on sftp_user.user_uid insert';
END IF$$

CREATE TRIGGER check_before_update BEFORE UPDATE ON sftp_user
FOR EACH ROW
IF NEW.user_uid < 10000 THEN
    SIGNAL SQLSTATE '38002'
    SET MESSAGE_TEXT = 'Check constraint failed on sftp_user.user_uid update';
END IF$$

DELIMITER ;

-- End of triggers
