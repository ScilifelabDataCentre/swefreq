-- Script for creating the swefreq tables. To run this file use:
-- mysql databasename <swefreq.sql
-- Possibly with mysql credentials


CREATE TABLE IF NOT EXISTS user (
    user_pk             INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    name                VARCHAR(100)    DEFAULT NULL,
    email               VARCHAR(100)    NOT NULL,
    affiliation         VARCHAR(100)    DEFAULT NULL,
    country             VARCHAR(100)    DEFAULT NULL,
    CONSTRAINT UNIQUE (email)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS study (
    study_pk            INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    pi_name             VARCHAR(100)    NOT NULL,
    pi_email            VARCHAR(100)    NOT NULL,
    contact_name        VARCHAR(100)    NOT NULL,
    contact_email       VARCHAR(100)    NOT NULL,
    title               VARCHAR(100)    NOT NULL,
    description         TEXT            DEFAULT NULL,
    publication_date    DATE            NOT NULL,
    ref_doi             VARCHAR(100)    DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS dataset (
    dataset_pk          INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    study_pk            INTEGER         NOT NULL,
    short_name          VARCHAR(50)     NOT NULL,
    full_name           VARCHAR(100)    NOT NULL,
    browser_uri         VARCHAR(200)    DEFAULT NULL,
    beacon_uri          VARCHAR(200)    DEFAULT NULL,
    avg_seq_depth       FLOAT           DEFAULT NULL,
    seq_type            VARCHAR(50)     DEFAULT NULL,
    seq_tech            VARCHAR(50)     DEFAULT NULL,
    seq_center          VARCHAR(100)    DEFAULT NULL,
    dataset_size        INTEGER         UNSIGNED NOT NULL,
    CONSTRAINT UNIQUE (short_name),
    CONSTRAINT FOREIGN KEY (study_pk) REFERENCES study(study_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS dataset_version (
    dataset_version_pk  INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    dataset_pk          INTEGER         NOT NULL,
    version             VARCHAR(20)     NOT NULL,
    description         TEXT            NOT NULL,
    terms               TEXT            NOT NULL,
    var_call_ref        VARCHAR(50)     DEFAULT NULL,
    available_from      TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    ref_doi             VARCHAR(100)    DEFAULT NULL,
    CONSTRAINT FOREIGN KEY (dataset_pk) REFERENCES dataset(dataset_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS collection (
    collection_pk       INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    name                VARCHAR(100)    NOT NULL,
    ethnicity           VARCHAR(50)     DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS sample_set (
    sample_set_pk       INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    dataset_pk          INTEGER         NOT NULL,
    collection_pk       INTEGER         NOT NULL,
    sample_size         INTEGER         NOT NULL,
    phenotype           VARCHAR(50)     NOT NULL,
    CONSTRAINT FOREIGN KEY (dataset_pk) REFERENCES dataset(dataset_pk),
    CONSTRAINT FOREIGN KEY (collection_pk) REFERENCES collection(collection_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS user_log (
    user_log_pk         INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    user_pk             INTEGER         NOT NULL,
    dataset_version_pk  INTEGER         NOT NULL,
    action  ENUM ('consent','download',
                  'access_requested','access_granted','access_revoked',
                  'private_link')       DEFAULT NULL,
    ts                  TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT FOREIGN KEY (user_pk)    REFERENCES user(user_pk),
    CONSTRAINT FOREIGN KEY (dataset_version_pk)
        REFERENCES dataset(dataset_version_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE OR REPLACE VIEW _user_log_summary AS
    SELECT MAX(user_log_pk) AS user_log_pk, user_pk, dataset_version_pk,
        action, MAX(ts) AS ts
    FROM user_log
    GROUP BY user_pk, dataset_pk, action;

CREATE TABLE IF NOT EXISTS dataset_access (
    dataset_access_pk   INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    dataset_pk          INTEGER         NOT NULL,
    user_pk             INTEGER         NOT NULL,
    wants_newsletter    BOOLEAN         DEFAULT false,
    is_admin            BOOLEAN         DEFAULT false,
    CONSTRAINT UNIQUE (dataset_pk, user_pk),
    CONSTRAINT FOREIGN KEY (dataset_pk) REFERENCES dataset(dataset_pk),
    CONSTRAINT FOREIGN KEY (user_pk)    REFERENCES user(user_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE OR REPLACE VIEW dataset_access_current AS
    SELECT DISTINCT
        access.*,
        TRUE AS has_access,
        (consent.action IS NOT NULL) AS has_consented,
        request.ts AS access_requested
    FROM dataset_access AS access
    JOIN ( SELECT user_pk, dataset_version_pk, MAX(ts) AS ts
           FROM user_log WHERE action = "access_requested"
           GROUP BY user_pk, dataset_version_pk ) AS request
        ON access.user_pk = request.user_pk AND
           access.dataset_version_pk = request.dataset_version_pk
    LEFT JOIN user_log AS consent
        ON access.user_pk = consent.user_pk AND
           access.dataset_version_pk = consent.dataset_version_pk AND
           consent.action = 'consent'
    WHERE (access.user_pk, access.dataset_version_pk) IN (
        -- gets user_pk for all users with current access
        -- from https://stackoverflow.com/a/39190423/4941495
        SELECT granted.user_pk, granted.dataset_version_pk
        FROM _user_log_summary AS granted
        LEFT JOIN _user_log_summary AS revoked
                ON granted.user_pk = revoked.user_pk AND
                   granted.dataset_version_pk = revoked.dataset_version_pk AND
                   revoked.action  = 'access_revoked'
        WHERE granted.action = 'access_granted' AND
            (revoked.user_pk IS NULL OR granted.ts > revoked.ts)
        GROUP BY granted.user_pk, granted.dataset_version_pk, granted.action
    );

CREATE OR REPLACE VIEW dataset_access_pending AS
    SELECT DISTINCT
        access.*,
        FALSE AS has_access,
        (consent.action IS NOT NULL) AS has_consented,
        request.ts AS access_requested
    FROM dataset_access AS access
    JOIN ( SELECT user_pk, dataset_version_pk, MAX(ts) AS ts
           FROM user_log WHERE action = "access_requested"
           GROUP BY user_pk, dataset_version_pk ) AS request
        ON access.user_pk = request.user_pk AND
           access.dataset_version_pk = request.dataset_version_pk
    LEFT JOIN user_log AS consent
        ON access.user_pk = consent.user_pk AND
           access.dataset_version_pk = consent.dataset_version_pk AND
           consent.action = 'consent'
    WHERE (access.user_pk, access.dataset_version_pk) IN (
        -- get user_pk for all users that have pending access requests
        SELECT requested.user_pk, requested.dataset_version_pk
        FROM _user_log_summary AS requested
        LEFT JOIN _user_log_summary AS granted
                ON requested.user_pk = granted.user_pk AND
                   requested.dataset_version_pk = granted.dataset_version_pk AND
                   granted.action  = 'access_granted'
        LEFT JOIN _user_log_summary AS revoked
                ON requested.user_pk = revoked.user_pk AND
                   requested.dataset_version_pk = revoked.dataset_version_pk AND
                   revoked.action  = 'access_revoked'
        WHERE requested.action = 'access_requested' AND
                (granted.user_pk IS NULL OR requested.ts > granted.ts) AND
                (revoked.user_pk IS NULL OR requested.ts > revoked.ts)
        GROUP BY requested.user_pk,
                 requested.dataset_version_pk,
                 requested.action
    );

CREATE TABLE IF NOT EXISTS dataset_file (
    dataset_file_pk     INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    dataset_version_pk  INTEGER         NOT NULL,
    name                VARCHAR(100)    NOT NULL,
    uri                 VARCHAR(200)    NOT NULL,
    CONSTRAINT FOREIGN KEY (dataset_version_pk)
        REFERENCES dataset_version(dataset_version_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS dataset_logo (
    dataset_logo_pk     INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    dataset_pk          INTEGER         NOT NULL,
    mimetype            VARCHAR(50)     NOT NULL,
    data                MEDIUMBLOB      NOT NULL,
    CONSTRAINT UNIQUE (dataset_pk),
    CONSTRAINT FOREIGN KEY (dataset_pk) REFERENCES dataset(dataset_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

CREATE TABLE IF NOT EXISTS linkhash (
    linkhash_pk         INTEGER         NOT NULL PRIMARY KEY AUTO_INCREMENT,
    dataset_version_pk  INTEGER         NOT NULL,
    user_pk             INTEGER         NOT NULL,
    hash                VARCHAR(64)     NOT NULL,
    expires_on          TIMESTAMP       NOT NULL,
    CONSTRAINT FOREIGN KEY (dataset_version_pk)
        REFERENCES dataset_version(dataset_version_pk),
    CONSTRAINT FOREIGN KEY (user_pk) REFERENCES user(user_pk)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;

-- dataset_version_current, a view that only contains the (most) current
-- version of each entry dataset_version

CREATE OR REPLACE VIEW dataset_version_current AS
    SELECT * FROM dataset_version
    WHERE (dataset_pk, dataset_version_pk) IN (
        SELECT dataset_pk, MAX(dataset_version_pk) FROM dataset_version
        WHERE available_from < now()
        GROUP BY dataset_pk );
