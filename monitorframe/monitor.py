import plotly.offline as off
import plotly.graph_objs as go
import pandas as pd
import smtplib
import os
import numpy as np
import abc
import warnings

from email.mime.text import MIMEText
from datetime import datetime
from plotly import tools
from typing import Union, List, Dict, Iterable, Any

from monitorframe.database import BaseModel, SETTINGS

ROW_DATA = List[dict]
COL_DATA = Dict[str, list]
VALID_GET = Union[ROW_DATA, COL_DATA]
EMAIL_TO = Union[str, list]


class MonitorInterface(abc.ABC):

    @abc.abstractmethod
    def track(self):
        pass

    @abc.abstractmethod
    def plot(self):
        pass

    @abc.abstractmethod
    def store_results(self):
        pass


class DataInterface(abc.ABC):

    @abc.abstractmethod
    def get_data(self):
        pass


class PandasMeta(abc.ABCMeta):
    def __new__(mcs, classnames, bases, class_dict):
        class_dict['get_data'] = mcs.wrap(class_dict['get_data'])

        return super(PandasMeta, mcs).__new__(mcs, classnames, bases, class_dict)

    @staticmethod
    def wrap(get_data):
        def to_pandas(self):
            data = get_data(self)
            df = pd.DataFrame(data)

            return df

        return to_pandas


class BaseDataModel(DataInterface, metaclass=PandasMeta):
    """Baseclass for monitor data models.

    Intended to be subclassed with one required method: get_data. Results from get_data will be used to generate a
    pandas DataFrame which the monitors use for the data source.
    """
    def __init__(self):
        self.data = self.get_data()

    @abc.abstractmethod
    def get_data(self) -> VALID_GET:
        """Retrieve monitor data. Should return row-wise or column-wise data."""


class Email:
    """Class representation for constructing and sending an email notification."""
    def __init__(self, username: str, subject: str, content: str, recipients: EMAIL_TO):
        self.sender = f'{username}@stsci.edu'
        self.subject = subject
        self.content = content
        self.recipients = self._set_recipients(recipients)

        self.message = self.build_message()

    @staticmethod
    def _set_recipients(recipients_input):
        """Set recipient or format list of recipients."""
        if isinstance(recipients_input, Iterable):
            return ''.join(recipients_input)

        elif isinstance(recipients_input, str):
            return recipients_input

        else:
            raise TypeError(
                f'recipients must be either iterable or a string. Recieved {type(recipients_input)} instead.'
            )

    def build_message(self) -> MIMEText:
        """Create MIMEText object."""

        message = MIMEText(self.content)
        message['Subject'] = self.subject
        message['From'] = self.sender
        message['To'] = self.recipients

        return message

    def send(self):
        """Send constructed email."""

        with smtplib.SMTP('smtp.stsci.edu') as mailer:
            mailer.send_message(self.message)


class BaseMonitor(MonitorInterface):
    """Baseclass for monitors. Intended to be subclassed as a framework for monitors.

    Required methods:
    -----------------
        track - method that returns the monitor's results

        notification_string - If notifications are active, this method defines the output for the notification


    Optional methods:
    -----------------
        find_outliers - method for identifying outlying data points. Should return a mask array.

        filter_data - method for filtering the retrieved data for monitoring purposes.

        define_plot - method for setting arguments to be used with the basic plotting methods


    Built-in methods:
    -----------------
        notify - Sends an email notification using text built from the notification_string method and based on the
        notification_settings attribute.

        monitor - Plots figure attribute and sends notification

        basic_scatter - Using arguments defined in define_plot, update figure attribute with a basic scatter plot

        basic_line - Using arguments defined in define_plot, update figure attribute with a basic line plot

        basic_image - Using arguments defined in define_plot, update figure attribute with a basic heatmap plot

        plot - Based on the class attribute, plottype, update figure attribute with selected plot.
        If more complex or custom plots are required, this method should be overridden.


    Class attributes:
    -----------------
        name: Required. Name of the monitor. Used in plots and saving output to files.

        data_model: Required. Data model that defines how data is retrieved.

        notification_settings: Optional. Dictionary defining notification settings. Should include the following
        keywords:

            - active: bool, turn notifications on or off.

            - username: str, username of the sender

            - recipients: str or iterable, list of email addresses to send the results

        plottype: Optional. Either 'line', 'scatter', or 'image'.

        subplots: Optional. Switch for configureing the figure attribute to organize plots into subplots

        subplot_layout: Optional. (rows, cols) configuration for subplots

        labels: Optional.  List of keywords that should be used as hover tool labels.
    """
    data_model = None
    notification_settings = None
    subplots = False
    subplot_layout = None
    labels = None
    output = None
    name = None

    def __init__(self):
        """Instantiation of the Monitor. Gather data, filter it, set plotting parameters."""
        self.x = None
        self.y = None
        self.z = None
        self.plottype = None
        self.hover_text = None
        self.mailer = None
        self.results = None
        self.outliers = None
        self.notification = None
        self.data = None
        self.filtered_data = None
        self._table = None
        self.datetimecol = None
        self.resultcol = None

        self.date = datetime.today()

        if SETTINGS['database']:
            self._define_table()

        # Create figure; If a subplot is required, create a subplot figure
        if self.subplots:
            self.figure = tools.make_subplots(*self.subplot_layout)

        else:
            self.figure = go.Figure()

        # Add date to the name of the monitor; Create a filename from the name given
        if not self.name:
            self.name = self.__class__.__name__

        self.name += f': {self.date.date().isoformat()}'
        self._filename = '_'.join(self.name.split(': ')).replace(' ', '')

        # Set output file path
        if not self.output:
            self.output = f'{os.path.join(os.getcwd(), f"{self._filename}.html")}'

        elif os.path.isdir(self.output):
            self.output = os.path.join(self.output, f"{self._filename}.html")

        # Execute tracking, outlier identification, notifications and set plot arguments
        if self.data_model is None:
            raise NotImplementedError('"data_model" must be defined in a monitor.')

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.__class__.__name__} Monitor object>'

    def _set_mailer(self):
        if self.notification_settings and self.notification_settings['active'] is True:
            self.mailer = Email(
                self.notification_settings['username'],
                self.name,
                self.notification,
                self.notification_settings['recipients']
            )

    def _define_table(self):
        self._table = BaseModel
        self._table.define_table_name(self.__class__.__name__)
        self.datetime_col = self._table.datetime
        self.result_col = self._table.result

    @property
    def query(self):
        if not self._table.table_exists():
            return

        return self._table.select()

    def initialize_data(self):
        model = self.data_model()
        self.data = model.data

        self.define_hover_labels()

        # Filter data if filter exists
        # noinspection PyNoneFunctionAssignment
        self.filtered_data = self.filter_data()

        self.define_plot()

    def run_analysis(self):
        self.results = self.track()
        # noinspection PyNoneFunctionAssignment
        self.outliers = self.find_outliers()
        self.notification = self.set_notification()
        self._set_mailer()

    def write_figure(self):
        off.plot(self.figure, filename=self.output, auto_open=False)

    def plot(self):
        """Create plots and update figure attribute."""
        if self.plottype == 'scatter':
            self.basic_scatter()

        elif self.plottype == 'line':
            self.basic_line()

        else:
            self.basic_image()

        self.figure['layout'].update(self.basic_layout)

    def notify(self):
        """Send notification email."""
        self.mailer.send()

    def monitor(self):
        """Build plots, add to figure, notify based on notification settings."""
        if self.data is None:
            self.initialize_data()

        self.run_analysis()
        self.plot()
        self.write_figure()
        self.store_results()

        if self.notification_settings and self.notification_settings['active'] is True:
            self.notify()

    @abc.abstractmethod
    def track(self) -> Any:
        """Returns monitoring results. Sets the results attribute."""
        pass

    def set_notification(self):
        if self.notification_settings and self.notification_settings['active'] is True:
            raise NotImplementedError(
                'With notification settings activated, the monitoring results message must be constructed.'
            )

        else:
            pass

    def find_outliers(self):
        """Returns mask that defines outliers. Sets the outliers attribute."""
        pass

    def filter_data(self):
        """Returns a filtered dataframe. Sets the filtered_data attribute."""
        pass

    def define_plot(self):
        """Sets the x, y, z, and plottype attributes used in the basic plotting methods."""
        pass

    def define_hover_labels(self):
        # Create hover tool text
        if self.labels:
            self.data['hover_text'] = [
                '<br>'.join(str(row).replace('\n', '<br>').split('<br>')[:-1])
                for _, row in self.data[self.labels].iterrows()
            ]

    @property
    def basic_layout(self):
        """Return a basic layout. Requiers x and y attributes to be set."""
        return go.Layout(
            title=self.name,
            hovermode='closest',
            xaxis=dict(title=self.x.name),
            yaxis=dict(title=self.y.name),

        )

    def basic_scatter(self):
        """Create a scatter plot."""
        self._basic_scatter('markers')

    def basic_line(self):
        """Create a line plot."""
        self._basic_scatter('lines')

    def _basic_scatter(self, mode: str):
        """Create Scatter trace object. Update the figure attribute. Requires that x and y attributes are set."""
        scatter = go.Scatter(
            x=self.x,
            y=self.y,
            mode=mode,
            marker=dict(
                color=self.z,
                colorscale='Viridis',
                colorbar=dict(len=0.75, title=self.z.name),
                showscale=True
            ) if self.z is not None else None,  # z is not used as a spatial dimension, but as a color dimension.
            name='Monitor',
            text=self.data.hover_text,
        )

        if self.outliers is not None:
            outliers = go.Scatter(
                x=self.x[self.outliers],
                y=self.y[self.outliers],
                mode='markers',
                marker=dict(color='red'),
                name='Outliers',
                text=self.data.hover_text[self.outliers],
            )

            self.figure.add_traces([scatter, outliers])

        else:
            self.figure.add_trace(scatter)

    def basic_image(self):
        """Create a heatmap plot and update the figure attribute. Requires that x, y and z attributes are set.
        z must be a 2D image.
        """
        image_plot = go.Heatmap(
            x=self.x,
            y=self.y,
            z=self.z,
            colorscale='Viridis',
            zmin=0,
            zmax=np.median(self.z),
            zsmooth='best'
        )

        self.figure.add_trace(image_plot)

    def _store_in_db(self, results):
        if isinstance(results, Iterable):
            results = list(results)

        # noinspection PyProtectedMember
        with self._table._meta.database.atomic():
            if not self._table.table_exists():
                self._table.create_table()

            try:
                new_results = self._table.create(datetime=self.date.isoformat(), result={'results': results})
                new_results.save()

            except TypeError:
                warnings.warn(
                    'Results could not be stored automatically. To store results, implement a custom store_results '
                    'method'
                )

    def format_results(self):
        pass

    def store_results(self):
        if self._table is not None:
            # noinspection PyNoneFunctionAssignment
            jsonified = self.format_results()
            self._store_in_db(self.results if jsonified is None else jsonified)

        else:
            raise NotImplementedError(
                'If not using built-in database support for storage, store_results must be overridden'
            )
