-------------------------------------------------------------------------------
--  
--

--------------------------------------------------------------------------------
-- Beacon consent codes. 
--
-- These tables are only used by the beacon, and are thus copied directly from
-- the default beacon schema.

CREATE TABLE beacon.consent_code_category_table (
	id serial PRIMARY KEY,
	name character varying(11)
);

INSERT INTO beacon.consent_code_category_table(name) VALUES ('PRIMARY');
INSERT INTO beacon.consent_code_category_table(name) VALUES ('SECONDARY');
INSERT INTO beacon.consent_code_category_table(name) VALUES ('REQUIREMENT');

CREATE TABLE beacon.consent_code_table (
	id serial PRIMARY KEY,
	name character varying(100) NOT NULL,
	abbr character varying(20) NOT NULL,
	description character varying(400) NOT NULL,
	additional_constraint_required boolean NOT NULL,
	category_id int NOT NULL REFERENCES beacon.consent_code_category_table(id)
);

INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('No restrictions', 'NRES', 'No restrictions on data use.', false, 1);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('General research use and clinical care', 'GRU(CC)', 'For health/medical/biomedical purposes, including the study of population origins or ancestry.', false, 1);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Health/medical/biomedical research and clinical care', 'HMB(CC)', 'Use of the data is limited to health/medical/biomedical purposes; does not include the study of population origins or ancestry.', false, 1);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Disease-specific research and clinical care', 'DS-[XX](CC)', 'Use of the data must be related to [disease].', true, 1);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Population origins/ancestry research', 'POA', 'Use of the data is limited to the study of population origins or ancestry.', false, 1);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Oher research-specific restrictions', 'RS-[XX]', 'Use of the data is limited to studies of [research type] (e.g., pediatric research).', true, 2);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Research use only', 'RUO', 'Use of data is limited to research purposes (e.g., does not include its use in clinical care).', false, 2);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('No “general methods” research', 'NMDS', 'Use of the data includes methods development research (e.g., development of software or algorithms) ONLY within the bounds of other data use limitations.', false, 2);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Genetic studies only', 'GSO', 'Use of the data is limited to genetic studies only (i.e., no “phenotype-only” research).', false, 2);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Not-for-profit use only', 'NPU', 'Use of the data is limited to not-for-profit organizations.', false, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Publication required', 'PUB', 'Requestor agrees to make results of studies using the data available to the larger scientific community.', false, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Collaboration required', 'COL-[XX]', 'Requestor must agree to collaboration with the primary study investigator(s).', true, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Ethics approval required', 'IRB', 'Requestor must provide documentation of local IRB/REC approval.', false, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Geographical restrictions', 'GS-[XX]', 'Use of the data is limited to within [geographic region].', true, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Publication moratorium/embargo', 'MOR-[XX]', 'Requestor agrees not to publish results of studies until [date].', true, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Time limits on use', 'TS-[XX]', 'Use of data is approved for [x months].', true, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('User-specific restrictions', 'US', 'Use of data is limited to use by approved users.', false, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Project-specific restrictions', 'PS', 'Use of data is limited to use within an approved project.', false, 3);
INSERT INTO beacon.consent_code_table(name, abbr, description, additional_constraint_required, category_id) VALUES ('Institution-specific restrictions', 'IS', 'Use of data is limited to use within an approved institution.', false, 3);
