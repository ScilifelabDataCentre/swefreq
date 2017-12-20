from peewee import *
import settings

database = MySQLDatabase(
        settings.mysql_schema,
        host=settings.mysql_host,
        user=settings.mysql_user,
        password=settings.mysql_passwd,
        port=settings.mysql_port
    )


class BaseModel(Model):
    class Meta:
        database = database


class EnumField(Field):
    db_field = 'string' # The same as for CharField

    def __init__(self, values=None, *args, **kwargs):
        self.values = values or []
        super().__init__(*args, **kwargs)

    def db_value(self, value):
        if value not in self.values:
            raise ValueError("Illegal value for '{}'".format(self.db_column))
        return value

    def python_value(self, value):
        if value not in self.values:
            raise ValueError("Illegal value for '{}'".format(self.db_column))
        return value


class User(BaseModel):
    user          = PrimaryKeyField(db_column='user_pk')
    name          = CharField(null=True)
    email         = CharField(unique=True)
    identity      = CharField(unique=True)
    identity_type = EnumField(null=False, values=['google', 'elixir'])
    affiliation   = CharField(null=True)
    country       = CharField(null=True)

    def is_admin(self, dataset):
        return DatasetAccess.select().where(
                DatasetAccess.dataset == dataset,
                DatasetAccess.user == self,
                DatasetAccess.is_admin
            ).count()

    def has_access(self, dataset):
        return DatasetAccessCurrent.select().where(
                DatasetAccessCurrent.dataset == dataset,
                DatasetAccessCurrent.user    == self,
            ).count()

    def has_requested_access(self, dataset):
        return DatasetAccessPending.select().where(
                DatasetAccessPending.dataset == dataset,
                DatasetAccessPending.user    == self
            ).count()

    class Meta:
        db_table = 'user'


class Study(BaseModel):
    study            = PrimaryKeyField(db_column='study_pk')
    pi_name          = CharField()
    pi_email         = CharField()
    contact_name     = CharField()
    contact_email    = CharField()
    title            = CharField()
    description      = TextField(null=True)
    publication_date = DateTimeField()
    ref_doi          = CharField(null=True)

    class Meta:
        db_table = 'study'


class Dataset(BaseModel):
    dataset            = PrimaryKeyField(db_column='dataset_pk')
    study              = ForeignKeyField(db_column='study_pk', rel_model=Study, to_field='study', related_name='datasets')
    short_name         = CharField()
    full_name          = CharField()
    browser_uri        = CharField(null=True)
    beacon_uri         = CharField(null=True)
    avg_seq_depth      = FloatField(null=True)
    seq_type           = CharField(null=True)
    seq_tech           = CharField(null=True)
    seq_center         = CharField(null=True)
    dataset_size       = IntegerField()
    mongodb_collection = CharField(null=False)

    def has_image(self):
        try:
            DatasetLogo.get(DatasetLogo.dataset == self)
            return True
        except DatasetLogo.DoesNotExist:
            return False

    class Meta:
        db_table = 'dataset'


class DatasetVersion(BaseModel):
    dataset_version = PrimaryKeyField(db_column='dataset_version_pk')
    dataset         = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='versions')
    version         = CharField()
    description     = TextField()
    terms           = TextField()
    var_call_ref    = CharField(null=True)
    available_from  = DateTimeField()
    ref_doi         = CharField(null=True)

    class Meta:
        db_table = 'dataset_version'


class Collection(BaseModel):
    collection = PrimaryKeyField(db_column = 'collection_pk')
    name       = CharField(null = True)
    ethnicity  = CharField(null = True)

    class Meta:
        db_table = 'collection'


class SampleSet(BaseModel):
    sample_set  = PrimaryKeyField(db_column='sample_set_pk')
    dataset     = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='sample_sets')
    collection  = ForeignKeyField(db_column='collection_pk', rel_model=Collection, to_field='collection', related_name='sample_sets')
    sample_size = IntegerField()
    phenotype   = CharField(null=True)

    class Meta:
        db_table = 'sample_set'


class DatasetFile(BaseModel):
    dataset_file    = PrimaryKeyField(db_column='dataset_file_pk')
    dataset_version = ForeignKeyField(db_column='dataset_version_pk', rel_model=DatasetVersion, to_field='dataset_version', related_name='files')
    name            = CharField()
    uri             = CharField()
    bytes           = IntegerField()

    class Meta:
        db_table = 'dataset_file'


class UserAccessLog(BaseModel):
    user_access_log = PrimaryKeyField(db_column='user_access_log_pk')
    user            = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='access_logs')
    dataset         = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='access_logs')
    action          = EnumField(null=True, values=['access_requested','access_granted','access_revoked','private_link'])
    ts              = DateTimeField()

    class Meta:
        db_table = 'user_access_log'


class UserConsentLog(BaseModel):
    user_consent_log = PrimaryKeyField(db_column='user_access_log_pk')
    user             = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='consent_logs')
    dataset_version  = ForeignKeyField(db_column='dataset_version_pk', rel_model=DatasetVersion, to_field='dataset_version', related_name='consent_logs')
    ts               = DateTimeField()

    class Meta:
        db_table = 'user_consent_log'


class UserDownloadLog(BaseModel):
    user_download_log = PrimaryKeyField(db_column='user_download_log_pk')
    user              = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='download_logs')
    dataset_file      = ForeignKeyField(db_column='dataset_file_pk', rel_model=DatasetFile, to_field='dataset_file', related_name='download_logs')
    ts                = DateTimeField()

    class Meta:
        db_table = 'user_download_log'


class DatasetAccess(BaseModel):
    dataset_access   = PrimaryKeyField(db_column='dataset_access_pk')
    dataset          = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='access')
    user             = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='access')
    wants_newsletter = IntegerField(null=True)
    is_admin         = IntegerField(null=True)

    class Meta:
        db_table = 'dataset_access'


class DatasetAccessCurrent(DatasetAccess):
    dataset          = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='access_current')
    user             = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='access_current')
    has_access       = IntegerField()
    access_requested = DateTimeField()

    class Meta:
        db_table = 'dataset_access_current'


class DatasetAccessPending(DatasetAccess):
    dataset          = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='access_pending')
    user             = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='access_pending')
    has_access       = IntegerField()
    access_requested = DateTimeField()

    class Meta:
        db_table = 'dataset_access_pending'


class DatasetLogo(BaseModel):
    dataset_logo = PrimaryKeyField(db_column='dataset_logo_pk')
    dataset      = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='logo')
    mimetype     = CharField()
    data         = BlobField()

    class Meta:
        db_table = 'dataset_logo'


class Linkhash(BaseModel):
    linkhash        = PrimaryKeyField(db_column='linkhash_pk')
    dataset_version = ForeignKeyField(db_column='dataset_version_pk', rel_model=DatasetVersion, to_field='dataset_version', related_name='link_hashes')
    user            = ForeignKeyField(db_column='user_pk', rel_model=User, to_field='user', related_name='link_hashes')
    hash            = CharField()
    expires_on      = DateTimeField()

    class Meta:
        db_table = 'linkhash'


class DatasetVersionCurrent(DatasetVersion):
    dataset = ForeignKeyField(db_column='dataset_pk', rel_model=Dataset, to_field='dataset', related_name='current_version')

    class Meta:
        db_table = 'dataset_version_current'


def get_dataset(dataset):
    dataset = Dataset.select().where( Dataset.short_name == dataset).get()
    return dataset


def get_dataset_version(dataset, version=None):
    if version:
        dataset_version = (DatasetVersion
                            .select(DatasetVersion, Dataset)
                            .join(Dataset)
                            .where(DatasetVersion.version == version,
                                   Dataset.short_name == dataset)).get()
    else:
        dataset_version = (DatasetVersionCurrent
                            .select(DatasetVersionCurrent, Dataset)
                            .join(Dataset)
                            .where(Dataset.short_name == dataset)).get()
    return dataset_version


def build_dict_from_row(row):
    d = {}
    for field in row._meta.sorted_fields:
        column = field.db_column
        if column.endswith("_pk"):
            continue
        d[column] = getattr(row, column)
    return d
