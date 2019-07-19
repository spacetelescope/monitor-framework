import plotly.offline as off
import plotly.graph_objs as go
import pandas as pd
import smtplib
import os
import numpy as np
import abc
import warnings

from itertools import repeat
from email.mime.text import MIMEText
from datetime import datetime
from plotly import tools
from typing import Union, List, Dict, Iterable, Any
import peewee

from .database import BaseResultsModel, DATA_DB, MODELS


class MonitorInterface(abc.ABC):

    @abc.abstractmethod
    def get_data(self) -> Any:
        pass

    @abc.abstractmethod
    def track(self) -> Any:
        pass

    @abc.abstractmethod
    def plot(self):
        pass

    @abc.abstractmethod
    def store_results(self):
        pass


class DataInterface(abc.ABC):

    @abc.abstractmethod
    def get_new_data(self) -> Union[List[dict], Dict[str, list]]:
        pass

    @abc.abstractmethod
    def ingest(self):
        pass

    @abc.abstractmethod
    def create_model(self) -> peewee.Model:
        pass


class PandasMeta(abc.ABCMeta):
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

    Intended to be subclassed with one required method: get_data. Results from get_data will be used to generate a
    pandas DataFrame which the monitors use for the data source.
    """
    _database = DATA_DB

    def __init__(self, find_new=True):
        self._array_types = None
        self.new_data = None
        self._formatted_data = None

        self.table_name = self.__class__.__name__

        # Read in and ingest new data
        if find_new:
            self.new_data = self.get_new_data()
            self._array_types = self._find_array_types()
            self._formatted_data = self._format_for_ingest()

        self.model = self.create_model()

    # noinspection PyUnresolvedReferences
    # noinspection PyCompatibility
    # self.new_data will be a pandas DataFrame object
    def _find_array_types(self):
        """Find datatypes in the dataframe that are likely arrays of some kind."""
        supported = [list, np.ndarray]  # Supported array types

        example = self.new_data.iloc[0]  # All rows should be the same.. otherwise ingestion won't even get this far

        # Assuming that "object" types that aren't strings are arrays
        return [key for key, dtype in self.data.dtypes.iteritems() if dtype == 'O' and type(example[key]) in supported]

    # noinspection PyUnresolvedReferences
    # self.new_data will be a pandas DataFrame object
    def _format_for_ingest(self):
        """Format new data for ingest. Primarily, if there are arrays as elements in any column, convert those to
        strings.
        """
        if self._array_types:  # If there are array elements, convert to string. Else, do nothing
            ingestible = self.new_data.copy()

            for key in self._array_types:
                ingestible[key] = ingestible[key].astype(str)

            return ingestible

        return self.new_data

    # noinspection PyUnresolvedReferences
    # self._formatted_data will be a pandas DataFrame object
    def ingest(self):
        """Ingest new data into database."""
        with self._database as db:
            self._formatted_data.to_sql(self.table_name, db, if_exists='append', index=False)

    def get_model(self) -> Union[peewee.Model, None]:
        """Create model object for accessing stored data."""
        try:
            return MODELS[self.table_name]

        except KeyError:
            return

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
                    lambda x: np.array(x.strip('[]').split(', '), dtype=float) if ',' in x
                    else np.array(x.strip('[]').split(), dtype=float)
                )

        return df


class Email:
    """Class representation for constructing and sending an email notification."""
    def __init__(self, username: str, subject: str, content: str, recipients: Union[str, list]):
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
    output = None
    name = None

    # Plot stuff
    subplots = False
    subplot_layout = None
    labels = None
    plottype = None
    x = None
    y = None
    z = None

    def __init__(self, find_new_data=True):
        """Initialization of the Monitor."""
        self.hover_text = None
        self.mailer = None
        self.results = None
        self.outliers = None
        self.notification = None
        self.data = None
        self._table = None
        self.datetimecol = None
        self.resultcol = None

        self.model = self.data_model(find_new=find_new_data)
        self.date = datetime.today()
        self._define_results_table()

        # Create figure; If a subplot is required, create a subplot figure
        if self.subplots:
            self.figure = tools.make_subplots(*self.subplot_layout)

        else:
            self.figure = go.Figure()

        # Add date to the name of the monitor; Create a filename from the name given
        if not self.name:
            self.name = self.__class__.__name__

        self.name += f': {self.date.date().isoformat()}'

        # For the filename, replace the colon with an underscore and remove any spaces
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

    def _define_results_table(self):
        self._table = BaseResultsModel
        self._table.define_table_name(self.__class__.__name__)
        self.datetime_col = self._table.datetime
        self.result_col = self._table.result

    @property
    def results_table(self):
        if not self._table.table_exists():
            return

        return self._table.select()

    def initialize_data(self):
        """Retrieve monitor data and prepare figure options."""
        self.data = self.get_data()
        self.define_hover_labels()
        self.define_plot()

    def run_analysis(self):
        """Execute tracking, outlier detection, and prepare notification."""
        self.results = self.track()
        self.outliers = self.find_outliers()
        self.notification = self.set_notification()
        self._set_mailer()

    def write_figure(self):
        """Plot figure and write to html file."""
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

    def find_outliers(self) -> pd.DataFrame:
        """Returns mask that defines outliers. Sets the outliers attribute."""
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
        """Return a basic layout. Requires x and y attributes to be set."""
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
        """Create a heat-map plot and update the figure attribute. Requires that x, y and z attributes are set.
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
        """Format results for storage."""
        pass

    def store_results(self):
        """Store monitoring results. If not using the results database, this method must be overridden."""
        if self._table is not None:
            # noinspection PyNoneFunctionAssignment
            jsonified = self.format_results()
            self._store_in_db(self.results if jsonified is None else jsonified)

        else:
            raise NotImplementedError(
                'If not using built-in database support for storage, store_results must be overridden'
            )
