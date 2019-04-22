import abc

from peewee import Model, DateTimeField
from playhouse.sqlite_ext import JSONField, SqliteExtDatabase

from .database_config import SETTINGS

DB = SqliteExtDatabase(**SETTINGS)


class BaseModel(Model):

    class Meta:
        database = DB

    datetime = DateTimeField(primary_key=True, verbose_name='Monitor execution date and time')
    result = JSONField(verbose_name='Monitoring results')


class DatabaseInterface(abc.ABC):

    def create_table(self):
        class Table(BaseModel):
            class Meta:
                table_name = self.__name__

        return Table

    @abc.abstractmethod
    def store_results(self):
        pass


def cold_start(table_list):
    with DB.connection_context():
        DB.create_tables(table_list)
