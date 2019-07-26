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


@pytest.fixture(params=[NEW_DATA, NEW_DATA_WITH_LIST, NEW_DATA_WITH_NPARRAY])
def datamodel_test_instance(request):

    class DataModelTestObject(BaseDataModel):
        primary_key = 'a'

        def get_new_data(self):
            return request.param

    datamodel_test_instance = DataModelTestObject()

    yield datamodel_test_instance

    if datamodel_test_instance.model:
        datamodel_test_instance.model.drop_table()


class TestDataModel:

    def test_new_data_is_dataframe(self, datamodel_test_instance):
        assert isinstance(datamodel_test_instance.new_data, pd.DataFrame)

    def test_find_array_types(self, datamodel_test_instance):
        test_array_keys = ['c']

        if datamodel_test_instance._array_types:
            assert datamodel_test_instance._array_types == test_array_keys

        else:
            assert not datamodel_test_instance._array_types

    def test_ingest_format(self, datamodel_test_instance):
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
        datamodel_test_instance.ingest()

    def test_model_creation(self, datamodel_test_instance):
        datamodel_test_instance.ingest()
        query = list(datamodel_test_instance.model.select().dicts())

        assert len(query) == 3

    def test_ingest_fails(self, datamodel_test_instance):
        datamodel_test_instance.ingest()

        with pytest.raises(IntegrityError):
            datamodel_test_instance.ingest()

    def test_db_is_closed(self, datamodel_test_instance):
        datamodel_test_instance.ingest()

        assert datamodel_test_instance._database.is_closed() is True

    def test_model_returns_none_without_table(self, datamodel_test_instance):
        assert datamodel_test_instance.model is None

    def test_query_to_pandas(self, datamodel_test_instance):
        datamodel_test_instance.ingest()

        query = datamodel_test_instance.model.select()

        if datamodel_test_instance._array_types:
            df = datamodel_test_instance.query_to_pandas(query, ['c'])
            assert (type(df.c[0]) == list or type(df.c[0]) == np.ndarray) and type(df.c[0][0]) == np.float64

            df = datamodel_test_instance.query_to_pandas(query, ['c'], [int])
            assert (type(df.c[0]) == list or type(df.c[0]) == np.ndarray) and type(df.c[0][0]) == np.int64

        else:
            datamodel_test_instance.query_to_pandas(query)
