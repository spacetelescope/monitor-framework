from peewee import Model, DateTimeField
from playhouse.sqlite_ext import JSONField, SqliteExtDatabase

from .database_config import SETTINGS

DB = SqliteExtDatabase(**SETTINGS)


class BaseModel(Model):

    class Meta:
        database = DB
        table_name = None

    @classmethod
    def define_table_name(cls, table_name):
        cls._meta.table_name = table_name

    datetime = DateTimeField(primary_key=True, verbose_name='Monitor execution date and time')
    result = JSONField(verbose_name='Monitoring results')
