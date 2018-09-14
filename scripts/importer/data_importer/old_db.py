from peewee import (
        BlobField,
        CharField,
        DateTimeField,
        Field,
        FloatField,
        ForeignKeyField,
        IntegerField,
        Model,
        MySQLDatabase,
        PrimaryKeyField,
        TextField,
        fn,
    )
import settings

mysql_database = MySQLDatabase(
        settings.mysql_schema,
        host=settings.mysql_host,
        user=settings.mysql_user,
        password=settings.mysql_passwd,
        port=settings.mysql_port
    )


class MySQLModel(Model):
    class Meta:
        database = mysql_database


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


class User(MySQLModel):
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


class Study(MySQLModel):
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


class Dataset(MySQLModel):
    dataset            = PrimaryKeyField(db_column='dataset_pk')
    study              = ForeignKeyField(Study, db_column='study_pk', to_field='study', related_name='datasets')
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


class DatasetVersion(MySQLModel):
    dataset_version   = PrimaryKeyField(db_column='dataset_version_pk')
    dataset           = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='versions')
    version           = CharField()
    description       = TextField()
    terms             = TextField()
    var_call_ref      = CharField(null=True)
    available_from    = DateTimeField()
    ref_doi           = CharField(null=True)
    data_contact_name = CharField(null=True)
    data_contact_link = CharField(null=True)

    class Meta:
        db_table = 'dataset_version'


class Collection(MySQLModel):
    collection = PrimaryKeyField(db_column = 'collection_pk')
    name       = CharField(null = True)
    ethnicity  = CharField(null = True)

    class Meta:
        db_table = 'collection'


class SampleSet(MySQLModel):
    sample_set  = PrimaryKeyField(db_column='sample_set_pk')
    dataset     = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='sample_sets')
    collection  = ForeignKeyField(Collection, db_column='collection_pk', to_field='collection', related_name='sample_sets')
    sample_size = IntegerField()
    phenotype   = CharField(null=True)

    class Meta:
        db_table = 'sample_set'


class DatasetFile(MySQLModel):
    dataset_file    = PrimaryKeyField(db_column='dataset_file_pk')
    dataset_version = ForeignKeyField(DatasetVersion, db_column='dataset_version_pk', to_field='dataset_version', related_name='files')
    name            = CharField()
    uri             = CharField()
    bytes           = IntegerField()

    class Meta:
        db_table = 'dataset_file'


class UserAccessLog(MySQLModel):
    user_access_log = PrimaryKeyField(db_column='user_access_log_pk')
    user            = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='access_logs')
    dataset         = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='access_logs')
    action          = EnumField(null=True, values=['access_requested','access_granted','access_revoked','private_link'])
    ts              = DateTimeField()

    class Meta:
        db_table = 'user_access_log'


class UserConsentLog(MySQLModel):
    user_consent_log = PrimaryKeyField(db_column='user_access_log_pk')
    user             = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='consent_logs')
    dataset_version  = ForeignKeyField(DatasetVersion, db_column='dataset_version_pk', to_field='dataset_version', related_name='consent_logs')
    ts               = DateTimeField()

    class Meta:
        db_table = 'user_consent_log'


class UserDownloadLog(MySQLModel):
    user_download_log = PrimaryKeyField(db_column='user_download_log_pk')
    user              = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='download_logs')
    dataset_file      = ForeignKeyField(DatasetFile, db_column='dataset_file_pk', to_field='dataset_file', related_name='download_logs')
    ts                = DateTimeField()

    class Meta:
        db_table = 'user_download_log'


class DatasetAccess(MySQLModel):
    dataset_access   = PrimaryKeyField(db_column='dataset_access_pk')
    dataset          = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='access')
    user             = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='access')
    wants_newsletter = IntegerField(null=True)
    is_admin         = IntegerField(null=True)

    class Meta:
        db_table = 'dataset_access'


class DatasetAccessCurrent(DatasetAccess):
    dataset          = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='access_current')
    user             = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='access_current')
    has_access       = IntegerField()
    access_requested = DateTimeField()

    class Meta:
        db_table = 'dataset_access_current'


class DatasetAccessPending(DatasetAccess):
    dataset          = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='access_pending')
    user             = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='access_pending')
    has_access       = IntegerField()
    access_requested = DateTimeField()

    class Meta:
        db_table = 'dataset_access_pending'


class DatasetLogo(MySQLModel):
    dataset_logo = PrimaryKeyField(db_column='dataset_logo_pk')
    dataset      = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='logo')
    mimetype     = CharField()
    data         = BlobField()

    class Meta:
        db_table = 'dataset_logo'


class Linkhash(MySQLModel):
    linkhash        = PrimaryKeyField(db_column='linkhash_pk')
    dataset_version = ForeignKeyField(DatasetVersion, db_column='dataset_version_pk', to_field='dataset_version', related_name='link_hashes')
    user            = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='link_hashes')
    hash            = CharField()
    expires_on      = DateTimeField()

    class Meta:
        db_table = 'linkhash'


class DatasetVersionCurrent(DatasetVersion):
    dataset = ForeignKeyField(Dataset, db_column='dataset_pk', to_field='dataset', related_name='current_version')

    class Meta:
        db_table = 'dataset_version_current'


class SFTPUser(MySQLModel):
    sftp_user     = PrimaryKeyField(db_column='sftp_user_pk')
    user          = ForeignKeyField(User, db_column='user_pk', to_field='user', related_name='sftp_user')
    user_uid      = IntegerField(unique=True)
    user_name     = CharField(null=False)
    password_hash = CharField(null=False)
    account_expires = DateTimeField(null=False)

    class Meta:
        db_table = 'sftp_user'


def get_next_free_uid():
    """
    Returns the next free uid >= 10000, and higher than the current uid's
    from the sftp_user table in the database.
    """
    default = 10000
    next_uid = default
    try:
        current_max_uid = SFTPUser.select(fn.MAX(SFTPUser.user_uid)).get().user_uid
        if current_max_uid:
            next_uid = current_max_uid+1
    except SFTPUser.DoesNotExist:
        pass

    return next_uid


def get_admin_datasets(user):
    return DatasetAccess.select().where( DatasetAccess.user == user, DatasetAccess.is_admin)


def get_dataset(dataset):
    dataset = Dataset.select().where( Dataset.short_name == dataset).get()
    return dataset


def build_dict_from_row(row):
    d = {}
    for field in row._meta.sorted_fields: #pylint: disable=protected-access
        column = field.db_column
        if column.endswith("_pk"):
            continue
        d[column] = getattr(row, column)
    return d
