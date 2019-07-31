import pytest
import os

from monitorframe.monitor import BaseMonitor
from monitorframe.datamodel import BaseDataModel

NEW_DATA = {
    'a': ['A', 'B', 'C'],
    'b': [4, 5, 6],
    'c': [7, 8, 9],
    'd': [10, 11, 12]
}

NOTIFICATIONS = {
    'notification_settings': {'active': True, 'username': 'testuser', 'recipients': 'testrecipient@stsci.edu'},
}

OUTPUT_DIR = {'output': '.'}
OUTPUT_PATH = {'output': './test_output.html'}
NAME = {'name': 'Test Monitor Name'}
SUBPLOTS = {'subplots': True, 'subplot_layout': (2, 1)}
LABELS = {'labels': ['a']}
SIMPLE_SCATTER = {'x': 'b', 'y': 'c', 'plottype': 'scatter'}
SIMPLE_LINE = {'x': 'b', 'y': 'c', 'plottype': 'line'}
SIMPLE_IMAGE = {'x': 'b', 'y': 'c', 'z': 'd', 'plottype': 'image'}


@pytest.fixture
def datamodel_test_instance():

    class DataModelTestObject(BaseDataModel):
        primary_key = 'a'

        def get_new_data(self):
            return NEW_DATA

    return DataModelTestObject


@pytest.fixture(
    params=[NOTIFICATIONS, OUTPUT_DIR, OUTPUT_PATH, NAME, SUBPLOTS, LABELS, SIMPLE_SCATTER, SIMPLE_LINE, SIMPLE_IMAGE]
)
def monitor_test_instance(datamodel_test_instance, request):

    class MonitorTestObject(BaseMonitor):
        data_model = datamodel_test_instance
        notification_settings = request.param.get('notification_settings', None)
        output = request.param.get('output', None)
        name = request.param.get('name', None)
        subplots = request.param.get('subplots', False)
        subplot_layout = request.param.get('subplot_layout', None)
        labels = request.param.get('labels', None)
        plottype = request.param.get('plottype', None)
        x = request.param.get('x', None)
        y = request.param.get('y', None)
        z = request.param.get('z', None)

        def get_data(self):
            return self.model.new_data

        def track(self):
            return self.data.c * 2

        def set_notification(self):
            return 'notification'

        def find_outliers(self):
            return self.data.c >= 8

    monitor_test_instance = MonitorTestObject()

    yield monitor_test_instance

    if monitor_test_instance.model.model:
        monitor_test_instance.model.model.drop_table()

    if monitor_test_instance.results_table is not None:
        monitor_test_instance._table.drop_table()

    if os.path.exists(monitor_test_instance.output):
        os.remove(monitor_test_instance.output)


class TestMonitor:

    def test_monior_init(self, monitor_test_instance):
        assert monitor_test_instance.model.new_data is not None

        assert (
                monitor_test_instance._table is not None and
                monitor_test_instance._table._meta.table_name == monitor_test_instance.__class__.__name__
        )

        assert monitor_test_instance.datetime_col is not None
        assert monitor_test_instance.result_col is not None

        if monitor_test_instance.subplots:
            assert 'xaxis2' in monitor_test_instance.figure.layout

        if (
                monitor_test_instance.name !=
                monitor_test_instance.__class__.__name__ + f': {monitor_test_instance.date.date().isoformat()}'
        ):
            assert (
                    monitor_test_instance.name ==
                    'Test Monitor Name' + f': {monitor_test_instance.date.date().isoformat()}'
            )

        assert monitor_test_instance._filename == '_'.join(monitor_test_instance.name.split(': ')).replace(' ', '')

    def test_set_mailer(self, monitor_test_instance):
        if monitor_test_instance.notification_settings is not None:
            monitor_test_instance.initialize_data()
            monitor_test_instance.run_analysis()
            monitor_test_instance._set_mailer()
            assert monitor_test_instance.mailer is not None
            assert monitor_test_instance.mailer.sender == 'testuser@stsci.edu'
            assert monitor_test_instance.mailer.subject == monitor_test_instance.name
            assert monitor_test_instance.mailer.content == monitor_test_instance.notification
            assert monitor_test_instance.mailer.recipients == 'testrecipient@stsci.edu'

    def test_results_table(self, monitor_test_instance):
        assert monitor_test_instance.results_table is None

        monitor_test_instance.store_results()

        assert monitor_test_instance.results_table is not None

    def test_initialize_data(self, monitor_test_instance):
        monitor_test_instance.initialize_data()

        assert monitor_test_instance.data is not None

        if monitor_test_instance.labels is not None:
            assert 'hover_text' in monitor_test_instance.data

    def test_run_analysis(self, monitor_test_instance):
        monitor_test_instance.initialize_data()
        monitor_test_instance.run_analysis()

        assert monitor_test_instance.results is not None
        assert monitor_test_instance.outliers is not None

        if monitor_test_instance.notification_settings is not None:
            assert monitor_test_instance.notification is not None
            assert monitor_test_instance.mailer is not None

    def test_plot(self, monitor_test_instance):
        if monitor_test_instance.x is not None and monitor_test_instance.y is not None:
            monitor_test_instance.initialize_data()
            monitor_test_instance.run_analysis()
            monitor_test_instance.plot()

            if monitor_test_instance.plottype == 'scatter':
                assert len(monitor_test_instance.figure.data) == 2 if monitor_test_instance.plottype == 'scatter' else 1

    def test_write_figure(self, monitor_test_instance):
        if monitor_test_instance.x is not None and monitor_test_instance.y is not None:
            monitor_test_instance.initialize_data()
            monitor_test_instance.plot()
            monitor_test_instance.write_figure()

            assert os.path.exists(monitor_test_instance.output)

    def test_monitor(self, monitor_test_instance):
        if monitor_test_instance.notification_settings is None:
            monitor_test_instance.monitor()

            assert monitor_test_instance.data is not None

            if monitor_test_instance.labels is not None:
                assert 'hover_text' in monitor_test_instance.data

            assert monitor_test_instance.results is not None
            assert monitor_test_instance.outliers is not None
            assert os.path.exists(monitor_test_instance.output)
            assert monitor_test_instance.results_table is not None

    def test_define_hover_labels(self, monitor_test_instance):
        monitor_test_instance.initialize_data()

        if monitor_test_instance.labels is not None:
            assert monitor_test_instance.data.hover_text[0] == 'a    A'
