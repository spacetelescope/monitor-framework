import numpy as np
import pandas as pd
import pytest

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

VALID_DATA = (
    ('data',),
    [
        (NEW_DATA,),
        (NEW_DATA_WITH_LIST,),
        (NEW_DATA_WITH_NPARRAY,),
    ]
)

VALID_DATA_WITH_ARRAYS = (
    ('data', 'array_keys'),
    [
        (NEW_DATA, []),
        (NEW_DATA_WITH_LIST, ['c']),
        (NEW_DATA_WITH_NPARRAY, ['c'])
    ]
)


class TestDataModel:

    @pytest.mark.parametrize(*VALID_DATA)
    def test_new_data_is_dataframe(self, data):

        class DataModelTestObject(BaseDataModel):
            def get_new_data(self):
                return data

        testmodel = DataModelTestObject()

        assert isinstance(testmodel.new_data, pd.DataFrame)

    @pytest.mark.parametrize(*VALID_DATA_WITH_ARRAYS)
    def test_find_array_types(self, data, array_keys):

        class DataModelTestObject(BaseDataModel):
            def get_new_data(self):
                return data

        testmodel = DataModelTestObject()

        assert testmodel._array_types == array_keys

    @pytest.mark.parametrize(*VALID_DATA_WITH_ARRAYS)
    def test_ingest_format(self, data, array_keys):

        class DataModelTestObject(BaseDataModel):
            def get_new_data(self):
                return data

        testmodel = DataModelTestObject()

        if not array_keys:
            # noinspection PyTypeChecker
            # DataFrames return mask DataFrames on boolean comparisons to other DataFrames
            assert all(testmodel.new_data == testmodel._formatted_data)

        if array_keys:
            for key in array_keys:
                assert testmodel._formatted_data[key].dtypes == 'O' and type(testmodel._formatted_data[key][0]) == str

    @pytest.mark.parametrize(*VALID_DATA)
    def test_ingest(self, data):

        class DataModelTestObject(BaseDataModel):
            def get_new_data(self):
                return data

        testmodel = DataModelTestObject()

        testmodel.ingest()
        testmodel.model.drop_table()

    def test_model_creation(self):

        class DataModelTestObject(BaseDataModel):
            def get_new_data(self):
                return NEW_DATA

        testmodel = DataModelTestObject()
        testmodel.ingest()
        query = list(testmodel.model.select().dicts())

        assert len(query) == 3

        testmodel.model.drop_table()
