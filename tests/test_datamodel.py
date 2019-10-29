import numpy as np
import pandas as pd
import pytest

from sqlite3 import IntegrityError

from monitorframe.datamodel import BaseDataModel

NEW_DATA = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'c': [7, 8, 9]
}

NEW_DATA_WITH_LIST = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'c': [[7, 8, 9], [10, 11, 12], [13, 14, 15]]
}

NEW_DATA_WITH_NPARRAY = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'c': [np.array([7, 8, 9]), np.array([10, 11, 12]), np.array([13, 14, 15])]
}

NEW_DATA_WITH_floats = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'c': [[1.123, 2.234, -3.345], [1.123, 2.234, -3.345], [1.123, 2.234, -3.345]]
}

NEW_DATA_WITH_bytestr = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'c': [[b'a', b'b', b'c'], [b'd', b'e', b'f'], [b'g', b'h', b'i']]
}

NEW_DATA_NO_ARRAYS = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'c': [7, 8, 9]
}


@pytest.fixture(params=[NEW_DATA, NEW_DATA_WITH_LIST, NEW_DATA_WITH_NPARRAY, NEW_DATA_WITH_floats, NEW_DATA_WITH_bytestr, NEW_DATA_NO_ARRAYS])
def datamodel_test_instance(request):
    """Test fixture that creates a datamodel object (from BaseDataModel) using the different data configurations in
    NEW_DATA, NEW_DATA_WITH_LIST, and NEW_DATA_WITH_NPARRAY. This fixture also includes a clean-up if a database table
    is created.

    Note: request is a special pytest argument.
    """
    # Create a simple implementation of a DataModel class for testing
    class DataModelTestObject(BaseDataModel):
        primary_key = 'a'

        def get_new_data(self):
            return request.param

    datamodel_test_instance = DataModelTestObject()

    # yield the instance
    yield datamodel_test_instance

    # Post-test cleanup
    if datamodel_test_instance.model:
        datamodel_test_instance.model.drop_table()


class TestDataModel:
    """Test class for testing the monitorframe BaseDataModel."""
    def test_new_data_is_dataframe(self, datamodel_test_instance):
        """Test that the result of get_new_data is successfully wrapped and returns a pandas DataFrame."""
        assert isinstance(datamodel_test_instance.new_data, pd.DataFrame)

    def test_find_array_types(self, datamodel_test_instance):
        """Test that the array column is found successfully."""
        test_array_keys = ['c']

        if datamodel_test_instance._array_types:
            assert datamodel_test_instance._array_types == test_array_keys

        else:
            assert not datamodel_test_instance._array_types

    def test_ingest_format(self, datamodel_test_instance):
        """Test that for array columns, the elements are converted into strings."""
        test_array_keys = ['c']

        if datamodel_test_instance._array_types:
            for key in test_array_keys:
                assert (
                               datamodel_test_instance._formatted_data[key].dtypes == 'O' and
                               type(datamodel_test_instance._formatted_data[key][0]) == str
                )

        else:
            # noinspection PyTypeChecker
            # DataFrames return mask DataFrames on boolean comparisons to other DataFrames
            assert all(datamodel_test_instance.new_data == datamodel_test_instance._formatted_data)

    def test_ingest(self, datamodel_test_instance):
        """Test that the ingest method executes successfully."""
        datamodel_test_instance.ingest()

    def test_model_creation(self, datamodel_test_instance):
        """Test that the peewee model object is created successfully (post-ingestion)."""
        datamodel_test_instance.ingest()  # The model is created via introspection. There must be a table with data.

        # Check that a peewee model can be constructed and queried
        query = list(datamodel_test_instance.model.select().dicts())
        assert len(query) == 3

        # Check that the model columns are correct
        assert sorted(datamodel_test_instance.model._meta.columns.keys()) == ['a', 'b', 'c']

    def test_ingest_fails(self, datamodel_test_instance):
        """Test that the table does not accept duplicates when a primary key is defined."""
        datamodel_test_instance.ingest()

        with pytest.raises(IntegrityError):
            datamodel_test_instance.ingest()

    def test_db_is_closed(self, datamodel_test_instance):
        """Test that the database connection closes after the ingest method executes successfully."""
        datamodel_test_instance.ingest()
        assert datamodel_test_instance._database.is_closed() is True

    def test_model_returns_none_without_table(self, datamodel_test_instance):
        """Test that the model property is None if the table doesn't exist."""
        assert datamodel_test_instance.model is None

    def test_query_to_pandas(self, datamodel_test_instance):
        """Test the query to pandas method."""
        datamodel_test_instance.ingest()
        query = datamodel_test_instance.model.select()

        if datamodel_test_instance._array_types:
            # Check that the query can be converted
            datamodel_test_instance.query_to_pandas(query, ['c'])

            # Check that the columns are converted into the specified dtype successfully
            df = datamodel_test_instance.query_to_pandas(query, ['c'], [str])
            assert (type(df.c[0]) == list or type(df.c[0]) == np.ndarray) and type(df.c[0][0]) == np.unicode_

        else:
            # Check that the query is converted without array elements
            datamodel_test_instance.query_to_pandas(query)
