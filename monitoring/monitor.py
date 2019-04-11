import plotly.offline as off
import plotly.graph_objs as go
import pandas as pd
import smtplib
import os
import numpy as np

from email.mime.text import MIMEText
from datetime import datetime
from plotly import tools
from typing import Union, List, Dict, Iterable, Any

ROW_DATA = List[Dict]
COL_DATA = Dict[str: List]
VALID_GET = Union[ROW_DATA, COL_DATA]
EMAIL_TO = Union[str, Iterable[str]]


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


class DataModel:
    """Baseclass for monitor data models.

    Intended to be subclassed with one required method: get_data. Results from get_data will be used to generate a
    pandas DataFrame which the monitors use for the data source.
    """
    def __init__(self):
        self.data = None

        self._data = self.get_data()
        self._to_pandas()

    def _to_pandas(self):
        """Convert column or row data to a pandas dataframe."""

        self.data = pd.DataFrame.from_dict(self._data)

    def get_data(self) -> VALID_GET:
        """Retrieve monitor data. Should return row-wise or column-wise data."""

        raise NotImplementedError('"get_data" method required for use.')


class Monitor:
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
    name = None
    data_model = None
    notification_settings = None
    plottype = None
    subplots = False
    subplot_layout = None
    labels = None

    def __init__(self):
        """Instantiation of the Monitor. Gather data, filter it, set plotting parameters."""
        self.x = None
        self.y = None
        self.z = None
        self.info_keys = None
        self.hover_text = None

        # Verify required attributes have been set
        self._check_required()
        self._check_plottype()

        self._data_model = self.data_model()

        # Create hover tool text
        if self.labels:
            self.data['hover_text'] = [
                '<br>'.join(
                    str(row).replace('\n', '<br>').split('<br>')[:-1]
                ) for _, row in self.data[self.labels].iterrows()
            ]

        self.filtered_data = self.filter_data()

        self.date = datetime.today()

        # Add date to the name of the monitor; Create a filename from the name given
        self.name += f': {self.date.date().isoformat()}'
        self._filename = '_'.join(self.name.split(': ')).replace(' ', '')

        # Set output file path
        if not self.output:
            self.output = f'{os.path.abspath(f"{self._filename}.html")}'

        if os.path.isdir(self.output):
            self.output = os.path.join(self.output, f"{self._filename}.html")

        # Execute tracking, outlier identification, and set plot arguments
        self.results = self.track()
        self.outliers = self.find_outliers()
        self.define_plot()
        self.notification = self.notification_string()

        self.mailer = Email(
            self.notification_settings['username'],
            self.name,
            self.notification,
            self.notification_settings['recipients']
        )

        # Create figure; If a subplot is required, create a subplot figure
        if self.subplots:
            self.figure = tools.make_subplots(*self.subplot_layout)

        else:
            self.figure = go.Figure()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.name} Monitor object>'

    def _check_plottype(self):
        """Check that the plottype attribute is set to a valid type."""
        if self.plottype and self.plottype not in ('scatter', 'image', 'line'):
            raise KeyError(
                f'{self.plottype} is not one of: "scatter", "image", "line". Please use one of those or set to None if '
                f'constructing a custom plot'
            )

    def _check_required(self):
        """Check that the required attributes have been defined."""
        if self.name is None or self.data_model is None:
            raise KeyError('"name" and "data_model" attributes must be defined in a monitor.')

    @property
    def data(self):
        return self._data_model.data

    @property
    def basic_layout(self):
        """Return a basic layout. Requiers x and y attributes to be set."""
        return go.Layout(
            title=self.name,
            hovermode='closest',
            xaxis=dict(title=self.x.name),
            yaxis=dict(title=self.y.name),

        )

    def track(self) -> Any:
        """Returns monitoring results. Sets the results attribute."""
        raise NotImplementedError('Monitor must track something.')

    def notification_string(self):
        if self.notification_settings['active'] is True:
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
        """Sets the x, y, and z attributes used in the basic plotting methods."""
        pass

    def notify(self):
        """Send notification email."""
        self.mailer.send()

    def monitor(self):
        """Build plots, add to figure, notify based on notification settings."""
        self.plot()
        off.plot(self.figure, filename=self.output, auto_open=False)

        if self.notification_settings and self.notification_settings['active'] is True:
            self.notify()

    def basic_scatter(self):
        """Create a scatter plot."""
        self._basic_scatter('markers')

    def basic_line(self):
        """Create a line plot."""
        self._basic_scatter('lines')

    def plot(self):
        """Create plots and update figure attribute."""
        if self.plottype == 'scatter':
            self.basic_scatter()

        elif self.plottype == 'line':
            self.basic_line()

        else:
            self.basic_image()

        self.figure['layout'].update(self.basic_layout)

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
