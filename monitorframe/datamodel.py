import abc
import numpy as np
import pandas as pd
import peewee

from itertools import repeat
from playhouse.reflection import generate_models
from typing import List, Dict, Union

from .database import DATA_DB


class DataInterface(abc.ABC):

    @abc.abstractmethod
    def get_new_data(self) -> Union[List[dict], Dict[str, list]]:
        pass

    @abc.abstractmethod
    def ingest(self):
        pass


class PandasMeta(abc.ABCMeta):
    """Meta class for BaseDataModel that wraps the get_new_data method to return a pandas dataframe created from the
     get_new_data method.
     """
    def __new__(mcs, classnames, bases, class_dict):
        class_dict['get_new_data'] = mcs.wrap(class_dict['get_new_data'])

        return super(PandasMeta, mcs).__new__(mcs, classnames, bases, class_dict)

    @staticmethod
    def wrap(get_new_data):
        def to_pandas(self):
            data = get_new_data(self)
            df = pd.DataFrame(data)

            return df

        return to_pandas


# noinspection PyAbstractClass
# Partial implementation
class BaseDataModel(DataInterface, metaclass=PandasMeta):
    """Baseclass for monitor data models.

    Intended to be subclassed with one required method: get_new_data. Results from get_data will be used to generate a
    pandas DataFrame which the monitors use for the data source.
    """
    _database = DATA_DB
    primary_key = None

    def __init__(self, find_new=True):
        self.new_data = None
        self.model = None
        self.table_name = self.__class__.__name__

        # Attempt to create a database table model
        self._generate_model()

        # Read in and ingest new data
        if find_new:
            self.new_data = self.get_new_data()

    def _generate_model(self):
        """Return the database table model object if the table exists in the database."""
        if self._database.table_exists(self.table_name):
            with self._database as db:
                self.model = generate_models(
                    db, literal_column_names=True, table_names=[self.table_name]
                )[self.table_name]

    # noinspection PyUnresolvedReferences
    # noinspection PyCompatibility
    # self.new_data will be a pandas DataFrame object
    @property
    def _array_types(self):
        """Find datatypes in the dataframe that are likely arrays of some kind."""
        if self.new_data is not None and not self.new_data.empty:
            supported = [list, np.ndarray, np.chararray]  # Supported array types
            example = self.new_data.iloc[0]  # All rows should be the same.. otherwise ingestion won't even get this far

            # Assuming that "object" types that aren't strings are arrays
            return [
                key for key, dtype in self.new_data.dtypes.iteritems()
                if dtype == 'O' and type(example[key]) in supported
            ]

        return

    # noinspection PyUnresolvedReferences
    # self.new_data will be a pandas DataFrame object
    @property
    def _formatted_data(self):
        """Format new data for ingest. Primarily, if there are arrays as elements in any column, convert those to
        strings.
        """
        if self.new_data is not None and not self.new_data.empty:
            if self._array_types:  # If there are array elements, convert to string. Else, do nothing
                ingestible = self.new_data.copy()

                for key in self._array_types:
                    ingestible[key] = ingestible[key].astype(str)

                return ingestible

            return self.new_data

        return

    def _set_primary_key(self):
        # Create SQL command based on dataframe
        # noinspection PyUnresolvedReferences
        insert = pd.io.sql.get_schema(self._formatted_data, self.table_name)

        # Find where the pimary key is in the sql string
        key_loc = insert.index(self.primary_key)  # Raise a ValueError if the key isn't found
        end_loc = insert[key_loc:].find(',')  # sql syntax: "column name" dtype,
        replace_string = insert[key_loc: key_loc + end_loc]

        insert = insert.replace(replace_string, replace_string + ' PRIMARY KEY')

        # Create the table with the primary key
        with self._database as db:
            db.execute_sql(insert)

    @abc.abstractmethod
    def get_new_data(self) -> Union[List[dict], Dict[str, list]]:
        """Retrieve monitor data. Should return row-wise or column-wise data."""
        pass

    # noinspection PyUnresolvedReferences
    # self._formatted_data will be a pandas DataFrame object
    def ingest(self):
        """Ingest new data into database."""
        # If a primary key is specified and the table doesn't exist, create the table with the primary key
        if self.primary_key and not self._database.table_exists(self.table_name):
            self._set_primary_key()

        # Insert the dataframe into the database
        with self._database as db:
            if self._formatted_data is not None:
                self._formatted_data.to_sql(self.table_name, db, if_exists='append', index=False)

        # If the model wasn't created due to the table not existing, create the model.
        if self.model is None:
            self._generate_model()

    def query_to_pandas(self, query: peewee.ModelSelect, array_cols: list = None, array_dtypes: list = None
                        ) -> pd.DataFrame:
        """Convert a model query to a pandas dataframe."""
        df = pd.DataFrame(query.dicts())

        if not array_cols:
            array_cols = self._array_types  # Try to use the new data to infer what the format should be

        if array_cols:
            if not array_dtypes:
                array_dtypes = repeat(float, len(array_cols))

            # Convert array columns to numpy arrays. Assume the dtype should be a float if not specified
            for key, dtype in zip(array_cols, array_dtypes):
                df[key] = df[key].apply(
                    lambda x: np.array(x.strip('[]').replace("'", '').split(', '), dtype=dtype) if ',' in x
                    else np.array(x.strip('[]').replace("'", '').split(), dtype=dtype)
                )

        return df
