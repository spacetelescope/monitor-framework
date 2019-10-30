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

NEW_DATA_WITH_ARRAYS = {
    'a': [1, 2, 3],
    'b': [4, 5, 6],
    'list_arr': [[7, 8, 9], [10, 11, 12], [13, 14, 15]],
    'np_arr': [np.array([7, 8, 9]), np.array([10, 11, 12]), np.array([13, 14, 15])],
    'floats': [[1.123, 2.234, -3.345], [1.123, 2.234, -3.345], [1.123, 2.234, -3.345]],
    'bytestr': [[b'a', b'b', b'c'], [b'd', b'e', b'f'], [b'g', b'h', b'i']]
}

TEST_ARRAY_KEYS = ['list_arr', 'np_arr', 'floats', 'bytestr']


@pytest.fixture(params=[NEW_DATA, NEW_DATA_WITH_ARRAYS])
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
        if datamodel_test_instance._array_types:
            assert datamodel_test_instance._array_types == TEST_ARRAY_KEYS

        else:
            assert not datamodel_test_instance._array_types

    def test_ingest_format(self, datamodel_test_instance):
        """Test that for array columns, the elements are converted into strings."""

        if datamodel_test_instance._array_types:
            for key in TEST_ARRAY_KEYS:
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
        if datamodel_test_instance._array_types:
            expected = [
                'a',
                'b',
                'bytestr',
                'bytestr_dtype',
                'floats',
                'floats_dtype',
                'list_arr',
                'list_arr_dtype',
                'np_arr',
                'np_arr_dtype'
            ]

            assert sorted(datamodel_test_instance.model._meta.columns.keys()) == expected

        else:
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
            df = datamodel_test_instance.query_to_pandas(query, TEST_ARRAY_KEYS)

            # Check that the columns are converted into the specified dtype successfully
            for key in TEST_ARRAY_KEYS:
                value = NEW_DATA_WITH_ARRAYS[key]

                assert (type(df.loc[0, key]) == np.ndarray) and df.loc[0, key].dtype == df.loc[0, f'{key}_dtype']
                assert np.array_equal(df.loc[0, key], np.array(value[0]))

        else:
            # Check that the query is converted without array elements
            query_df = datamodel_test_instance.query_to_pandas(query)
            assert query_df.equals(datamodel_test_instance.new_data)
