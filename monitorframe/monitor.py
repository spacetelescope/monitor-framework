import abc
import os
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import warnings

from datetime import datetime
from plotly.subplots import make_subplots
from typing import Iterable, Any

from .database import BaseResultsModel
from .notifications import Email


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

    def __init__(self, find_new_data: bool = True):
        """Initialization of the Monitor."""
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
            self.figure = make_subplots(*self.subplot_layout)

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

    def run_analysis(self):
        """Execute tracking, outlier detection, and prepare notification."""
        self.results = self.track()
        self.outliers = self.find_outliers()
        self.notification = self.set_notification()
        self._set_mailer()

    def write_figure(self):
        """Plot figure and write to html file."""
        self.figure.write_html(self.output)

    def plot(self):
        """Create plots and update figure attribute."""
        if self.plottype == 'scatter':
            self.basic_scatter()

        if self.plottype == 'line':
            self.basic_line()

        if self.plottype == 'image':
            self.basic_image()

        self.figure.update_layout(self.basic_layout)

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
        )

    def basic_scatter(self):
        """Create a scatter plot."""
        self.figure = px.scatter(
            self.data,
            x=self.x,
            y=self.y,
            color=self.z,
            color_continuous_scale=px.colors.sequential.Viridis,
            hover_data=self.labels,
        )

        if self.outliers is not None:
            self.figure.add_scatter(
                x=self.data[self.x][self.outliers],
                y=self.data[self.y][self.outliers],
                mode='markers',
                marker=dict(color='red', opacity=0.7, size=8),
                name='Outliers',
                hovertext=self.data.hover_text[self.outliers] if 'hover_text' in self.data else None,
                hoverinfo='text'
            )

        self.figure.update_layout(
            coloraxis_colorbar_len=0.8,
            coloraxis_colorbar_yanchor='bottom',
            coloraxis_colorbar_y=0
        )

    def basic_line(self):
        """Create a line plot."""
        self.figure = px.line(
            self.data,
            x=self.x,
            y=self.y,
            color=self.z,
            hover_data=self.labels,
        )

    def basic_image(self):
        """Create a heat-map plot and update the figure attribute. Requires that x, y and z attributes are set.
        z must be a 2D image.
        """
        self.figure = px.density_heatmap(
            self.data,
            x=self.x,
            y=self.y,
            z=self.z,
            color_continuous_scale=px.colors.sequential.Viridis,
            hover_data=self.labels,
        )

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
