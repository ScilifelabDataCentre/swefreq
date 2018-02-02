INSERT INTO study (study_pk, pi_name, pi_email, contact_name, contact_email, title, description, publication_date, ref_doi)
    VALUES (1000001, 'PI_STUDY1', 'pi1@example.com', 'Contact Study 1', 'contact1@example.com', 'Study 1', 'Study 1 description', '2017-01-01', 'study1DOI'),
           (1000002, 'PI_STUDY2', 'pi2@example.com', 'Contact Study 2', 'contact2@example.com', 'Study 2', 'Study 2 description', '2017-02-01', 'study2DOI');

INSERT INTO collection (collection_pk, name, ethnicity) VALUES
    (1000001, 'Collection1', 'CollEth1'),
    (1000002, 'Collection2', 'CollEth2'),
    (1000003, 'Collection3', 'CollEth3');

INSERT INTO dataset (dataset_pk, study_pk, short_name, full_name, browser_uri, beacon_uri, avg_seq_depth, seq_type, seq_tech, seq_center, dataset_size, mongodb_collection)
    VALUES (1000001, 1000001, 'Dataset 1', 'Dataset 1 Long name', 'http://example.com/browser1', 'http://example.com/beacon1', 1.0, 'SeqType1', 'SeqTech1', 'SeqCenter1', 1001, 'na'),
           (1000002, 1000002, 'Dataset 2', 'Dataset 2 Long name', 'http://example.com/browser2', 'http://example.com/beacon2', 2.0, 'SeqType2', 'SeqTech2', 'SeqCenter2', 1002, 'na');

INSERT INTO sample_set (sample_set_pk, dataset_pk, collection_pk, sample_size, phenotype)
    VALUES (1000001, 1000001, 1000001, 10, 'SamplePheno1'),
           (1000002, 1000001, 1000002, 15, 'SamplePheno2 Coll1'),
           (1000003, 1000002, 1000003, 20, 'SamplePheno2 Coll2');

INSERT INTO dataset_version (dataset_version_pk, dataset_pk, version, description, terms, var_call_ref, available_from, ref_doi)
    VALUES (1000001, 1000001, 'Version 1-1', 'Dataset 1-1, description', 'Dataset 1-1, terms', 'CallRef11', '2017-01-01', 'datset11DOI'),
           (1000002, 1000002, 'Version 2-1', 'Dataset 2-1, description', 'Dataset 2-1, terms', 'CallRef21', '2017-02-01', 'datset21DOI'),
           (1000003, 1000002, 'Version 2-2', 'Dataset 2-2, description', 'Dataset 2-2, terms', 'CallRef22', '2017-02-02', 'datset22DOI'),
           (1000004, 1000002, 'InvVer  2-3', 'Dataset 2-3, description', 'Dataset 2-3, terms', 'CallRef23', '2030-02-03', 'datset23DOI');

INSERT INTO dataset_file(dataset_file_pk, dataset_version_pk, name, uri, bytes)
    VALUES (1000001, 1000001, 'File11-1', '/release/file111.txt', 100),
           (1000002, 1000001, 'File11-2', '/release/file112.txt', 100000),
           (1000003, 1000002, 'File21-1', '/release/file211.txt', 1000000000),
           (1000004, 1000003, 'File22-1', '/release/file221.txt', 973826482736),
           (1000005, 1000004, 'File23-1', '/release/file231.txt', 239847293874293874);

INSERT INTO user(user_pk, name, email, affiliation, country, identity, identity_type) VALUES
    (1000100, 'Not req yet',          'email0',  'i',         '', 'email0',  'elixir'),
    (1000101, 'Requested access',     'email1',  'w1',        '', 'email1',  'google'),
    (1000102, 'Approved access',      'email2',  'c1',        '', 'email2',  'elixir'),
    (1000103, 'Denied access',        'email3',  'i',         '', 'email3',  'google'),
    (1000104, 'Approved then denied', 'email4',  'i',         '', 'email4',  'elixir'),
    (1000105, 'R->A->D->R',           'email5',  'w1',        '', 'email5',  'google'),
    (1000106, 'R->A->D->R->A',        'email6',  'c1',        '', 'email6',  'elixir'),
    (1000107, 'R->A->D->R->D',        'email7',  'i',         '', 'email7',  'google'),
    (1000108, 'Combo1 w1 w2',         'email8',  'w1 w2',     '', 'email8',  'elixir'),
    (1000109, 'Combo2 w1 c2',         'email9',  'w1 c2',     '', 'email9',  'google'),
    (1000110, 'Combo3 c1 w2',         'email10', 'c1 w2',     '', 'email10', 'elixir'),
    (1000111, 'Combo4 c1 c2',         'email11', 'c1 c2',     '', 'email11', 'google'),
    (1000112, 'Combo5 c1 i2',         'email12', 'c1 i2',     '', 'email12', 'elixir'),
    (1000113, 'Admin1',               'admin1',  'Rootspace', '', 'admin1',  'google'),
    (1000114, 'Admin2',               'admin2',  'Rootspace', '', 'admin2',  'elixir'),
    (1000115, 'Admin12',              'admin12', 'Rootspace', '', 'admin12', 'google');

INSERT INTO dataset_access(user_pk, dataset_pk) VALUES
    (1000100, 1000001), (1000101, 1000001), (1000102, 1000001), (1000103, 1000001), (1000104, 1000001), (1000105, 1000001),
    (1000106, 1000001), (1000107, 1000001), (1000108, 1000001), (1000108, 1000002), (1000109, 1000001), (1000109, 1000002),
    (1000110, 1000001), (1000110, 1000002), (1000111, 1000001), (1000111, 1000002), (1000112, 1000001), (1000112, 1000002);

INSERT INTO dataset_access(user_pk, dataset_pk, is_admin) VALUES
    (1000113, 1000001, 1), (1000114, 1000002, 1), (1000115, 1000001, 1), (1000115, 1000002, 1);

INSERT INTO user_access_log(user_pk, dataset_pk, action, ts) VALUES
    (1000101, 1000001, 'access_requested', '2017-01-01'),
    (1000102, 1000001, 'access_requested', '2017-01-02'),
    (1000103, 1000001, 'access_requested', '2017-01-03'),
    (1000104, 1000001, 'access_requested', '2017-01-04'),
    (1000105, 1000001, 'access_requested', '2017-01-05'),
    (1000106, 1000001, 'access_requested', '2017-01-06'),
    (1000107, 1000001, 'access_requested', '2017-01-07'),
    (1000102, 1000001, 'access_granted',   '2017-01-08'),
    (1000103, 1000001, 'access_revoked',   '2017-01-09'),
    (1000104, 1000001, 'access_granted',   '2017-01-10'),
    (1000104, 1000001, 'access_revoked',   '2017-01-11'),
    (1000105, 1000001, 'access_granted',   '2017-01-12'),
    (1000105, 1000001, 'access_revoked',   '2017-01-13'),
    (1000105, 1000001, 'access_requested', '2017-01-14'),
    (1000106, 1000001, 'access_granted',   '2017-01-15'),
    (1000106, 1000001, 'access_revoked',   '2017-01-16'),
    (1000106, 1000001, 'access_requested', '2017-01-17'),
    (1000106, 1000001, 'access_granted',   '2017-01-18'),
    (1000107, 1000001, 'access_granted',   '2017-01-19'),
    (1000107, 1000001, 'access_revoked',   '2017-01-20'),
    (1000107, 1000001, 'access_requested', '2017-01-21'),
    (1000107, 1000001, 'access_revoked',   '2017-01-22'),
    (1000108, 1000001, 'access_requested', '2017-01-23'),
    (1000108, 1000002, 'access_requested', '2017-01-24'),
    (1000109, 1000001, 'access_requested', '2017-01-25'),
    (1000109, 1000002, 'access_requested', '2017-01-26'),
    (1000109, 1000002, 'access_granted',   '2017-01-27'),
    (1000110, 1000001, 'access_requested', '2017-01-28'),
    (1000110, 1000002, 'access_requested', '2017-01-29'),
    (1000110, 1000001, 'access_granted',   '2017-01-30'),
    (1000111, 1000001, 'access_requested', '2017-01-31'),
    (1000111, 1000002, 'access_requested', '2017-02-01'),
    (1000111, 1000001, 'access_granted',   '2017-02-02'),
    (1000111, 1000002, 'access_granted',   '2017-02-03'),
    (1000112, 1000001, 'access_requested', '2017-02-04'),
    (1000112, 1000002, 'access_requested', '2017-02-05'),
    (1000112, 1000001, 'access_granted',   '2017-02-06'),
    (1000112, 1000002, 'access_granted',   '2017-02-07'),
    (1000112, 1000002, 'access_revoked',   '2017-02-08'),
    (1000113, 1000001, 'access_requested', '2017-02-09'),
    (1000113, 1000001, 'access_granted',   '2017-02-10'),
    (1000114, 1000002, 'access_requested', '2017-02-11'),
    (1000114, 1000002, 'access_granted',   '2017-02-12'),
    (1000115, 1000001, 'access_requested', '2017-02-13'),
    (1000115, 1000001, 'access_granted',   '2017-02-14'),
    (1000115, 1000002, 'access_requested', '2017-02-15'),
    (1000115, 1000002, 'access_granted',   '2017-02-16');

SELECT "Waiting", user.name, user.affiliation as visibility, user.user_pk,
       dataset_access_pending.dataset_pk,
       dataset_access_pending.dataset_access_pk
FROM dataset_access_pending JOIN user ON (dataset_access_pending.user_pk = user.user_pk)
WHERE dataset_pk > 1000000;

SELECT "Current", user.name, user.affiliation as visibility, user.user_pk, dataset_access_current.dataset_pk,
       dataset_access_current.dataset_access_pk
FROM dataset_access_current JOIN user ON (dataset_access_current.user_pk = user.user_pk)
WHERE dataset_pk > 1000000;
