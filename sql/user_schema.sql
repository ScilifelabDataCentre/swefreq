--------------------------------------------------------------------------------
-- Swefreq user schema                                                        --
--                                                                            --
-- This schema contains the user tables, including the access rights to the   --
-- datasets (in the data schema) in the Swefreq system.                       --
--                                                                            --
--------------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS users;

--------------------------------------------------------------------------------
-- User fields
--

CREATE TYPE identity_enum AS ENUM('google', 'elixir');

CREATE TABLE IF NOT EXISTS users.users (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    username            varchar(100)              DEFAULT NULL,
    email               varchar(100) UNIQUE       NOT NULL,
    affiliation         varchar(100)              DEFAULT NULL,
    country             varchar(100)              DEFAULT NULL,
    identity            varchar(100)              NOT NULL,
    identity_type       identity_enum             NOT NULL,
    UNIQUE (identity, identity_type)
);

CREATE TABLE IF NOT EXISTS users.sftp_users (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user_id             integer             NOT NULL REFERENCES users.users,
    user_uid            integer      UNIQUE NOT NULL CHECK (user_uid >= 10000),
    user_name           varchar(50)         NOT NULL,
    password_hash       varchar(100)        NOT NULL,
    account_expires     timestamp           NOT NULL
);

CREATE TABLE IF NOT EXISTS users.linkhash (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset_version integer             NOT NULL REFERENCES data.dataset_versions,
    user_id         integer             NOT NULL REFERENCES users.users,
    "hash"          varchar(64) UNIQUE  NOT NULL,
    expires_on      timestamp           NOT NULL
);

CREATE TABLE IF NOT EXISTS users.dataset_access (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    dataset          integer         NOT NULL REFERENCES data.datasets,
    user_id          integer         NOT NULL REFERENCES users.users,
    wants_newsletter boolean         DEFAULT false,
    is_admin         boolean         DEFAULT false,
    UNIQUE (dataset, user_id)
);

CREATE TYPE access_action AS ENUM('access_granted', 'access_revoked',
                                  'access_requested', 'private_link');

CREATE TABLE IF NOT EXISTS users.user_access_log (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user_id     integer         NOT NULL REFERENCES users.users,
    dataset     integer         NOT NULL REFERENCES data.datasets,
    ts          timestamp       NOT NULL DEFAULT current_timestamp,
    "action"    access_action   DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS users.user_consent_log (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user_id         integer         NOT NULL REFERENCES users.users,
    dataset_version integer         NOT NULL REFERENCES data.dataset_versions,
    ts              timestamp       NOT NULL DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS users.user_download_log (
    id integer PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
    user_id         integer         NOT NULL REFERENCES users.users,
    dataset_file    integer         NOT NULL REFERENCES data.dataset_files,
    ts              timestamp       NOT NULL DEFAULT current_timestamp
);

--------------------------------------------------------------------------------
-- User views
--

CREATE OR REPLACE VIEW users.user_access_log_summary AS
    SELECT MAX(id) AS id,
           user_id,
           dataset,
           "action",
           MAX(ts) AS ts
    FROM users.user_access_log
    GROUP BY user_id, dataset, "action"
;

CREATE OR REPLACE VIEW users.dataset_access_current AS
    SELECT DISTINCT
        access.*,
        TRUE AS has_access,
        request.ts AS access_requested
    FROM users.dataset_access AS access
    JOIN ( SELECT user_id, dataset, MAX(ts) AS ts
           FROM users.user_access_log WHERE action = 'access_requested'
           GROUP BY user_id, dataset ) AS request
        ON access.user_id = request.user_id AND
           access.dataset = request.dataset
    WHERE (access.user_id, access.dataset) IN (
        SELECT granted.user_id, granted.dataset
        FROM users.user_access_log_summary AS granted
        LEFT JOIN users.user_access_log_summary AS revoked
                ON granted.user_id = revoked.user_id AND
                   granted.dataset = revoked.dataset AND
                   revoked.action  = 'access_revoked'
        WHERE granted.action = 'access_granted' AND
            (revoked.user_id IS NULL OR granted.ts > revoked.ts)
        GROUP BY granted.user_id, granted.dataset, granted.action
    );

CREATE OR REPLACE VIEW users.dataset_access_pending AS
    SELECT DISTINCT
        access.*,
        FALSE AS has_access,
        request.ts AS access_requested
    FROM users.dataset_access AS access
    JOIN ( SELECT user_id, dataset, MAX(ts) AS ts
           FROM users.user_access_log WHERE action = 'access_requested'
           GROUP BY user_id, dataset ) AS request
        ON access.user_id = request.user_id AND
           access.dataset = request.dataset
    WHERE (access.user_id, access.dataset) IN (
        -- get user_id for all users that have pending access requests
        SELECT requested.user_id, requested.dataset
        FROM users.user_access_log_summary AS requested
        LEFT JOIN users.user_access_log_summary AS granted
                ON requested.user_id = granted.user_id AND
                   requested.dataset = granted.dataset AND
                   granted.action  = 'access_granted'
        LEFT JOIN users.user_access_log_summary AS revoked
                ON requested.user_id = revoked.user_id AND
                   requested.dataset = revoked.dataset AND
                   revoked.action  = 'access_revoked'
        WHERE requested.action = 'access_requested' AND
                (granted.user_id IS NULL OR requested.ts > granted.ts) AND
                (revoked.user_id IS NULL OR requested.ts > revoked.ts)
        GROUP BY requested.user_id, requested.dataset, requested.action
    );
