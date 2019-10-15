from peewee import Model, DateTimeField
from playhouse.sqlite_ext import JSONField, SqliteExtDatabase

from . import SETTINGS

DATA_DB_SETTINGS = SETTINGS['data']['db_settings']
RESULTS_DB_SETTINGS = SETTINGS['results']['db_settings']

DATA_DB = SqliteExtDatabase(**DATA_DB_SETTINGS)
RESULTS_DB = SqliteExtDatabase(**RESULTS_DB_SETTINGS)

# TODO: Add outliers table


class BaseResultsModel(Model):

    class Meta:
        database = RESULTS_DB
        table_name = None

    @classmethod
    def define_table_name(cls, table_name):
        cls._meta.table_name = table_name

    datetime = DateTimeField(primary_key=True, verbose_name='Monitor execution date and time')
    result = JSONField(verbose_name='Monitoring results')
