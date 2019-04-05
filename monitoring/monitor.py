import plotly.offline as off
import plotly.graph_objs as go
import pandas as pd
import smtplib
import os
import numpy as np
import dask
import re

from astropy.io import fits
from glob import glob
from typing import Iterable
from email.mime.text import MIMEText
from datetime import datetime
from plotly import tools


def find_all_files(data_dir='/grp/hst/cos2/cosmo'):
    pattern = r'\d{5}'
    programs = os.listdir(data_dir)

    result = [
        dask.delayed(glob)(os.path.join(data_dir, program, '*')) for program in programs if re.match(pattern, program)
    ]

    results = dask.compute(result)[0]
    results_as_list = [file for file_list in results for file in file_list]

    return results_as_list


def get_keywords_from_files(fitsfiles, keywords, extensions, exptype=None, names=None):
    assert len(keywords) == len(extensions), 'Keywords and extensions arguments must be the same length.'

    if names is not None:
        assert len(names) == len(keywords), (
            'Names argument must be the same length as keywords and extensions arguments'
        )

    @dask.delayed
    def get_keyword_values(fitsfile, keys, exts, exp_type=None, new_names=None):
        with fits.open(fitsfile) as file:
            try:
                if exptype and file[0].header['EXPTYPE'] != exp_type:
                    return

            except KeyError:
                if exptype and file[0].header['OPMODE'] != exp_type:
                    return

            if new_names is not None:
                return {
                    name: file[ext].header[key] for key, ext, name in zip(
                        keys, exts, new_names
                    )
                }

            return {key: file[ext].header[key] for key, ext in zip(keys, exts)}

    delayed_results = [get_keyword_values(fitsfile, keywords, extensions, exptype) for fitsfile in fitsfiles]

    return [item for item in dask.compute(*delayed_results, scheduler='multiprocessing') if item is not None]


class Email:

    def __init__(self, username, subject, content, recipients):
        self.sender = f'{username}@stsci.edu'
        self.subject = subject
        self.content = content
        self.recipients = self._set_recipients(recipients)

        self.message = self.build_message()

    @staticmethod
    def _set_recipients(recipients_input):
        if isinstance(recipients_input, Iterable):
            return ''.join(recipients_input)

        elif isinstance(recipients_input, str):
            return recipients_input

        else:
            raise TypeError(
                f'recipients must be either iterable or a string. Recieved {type(recipients_input)} instead.'
            )

    def build_message(self):
        message = MIMEText(self.content)
        message['Subject'] = self.subject
        message['From'] = self.sender
        message['To'] = self.recipients

        return message

    def send(self):
        with smtplib.SMTP('smtp.stsci.edu') as mailer:
            mailer.send_message(self.message)


class DataModel:
    def __init__(self):
        self.data = None
        self._data = self.get_data()
        self._to_pandas()

    def _to_pandas(self):
        self.data = pd.DataFrame.from_dict(self._data)

    def get_data(self):
        raise NotImplementedError('"get_data" method required for use.')


class Monitor:

    name = None
    data_model = None
    notification_settings = None
    plottype = None
    subplots = False
    subplot_layout = None
    labels = None

    def __init__(self):
        self.x = None
        self.y = None
        self.z = None
        self.image = None
        self.info_keys = None
        self.hover_text = None

        self._data_model = self.data_model()
        self._check_plottype()

        self.date = datetime.today()

        self.name += f' {self.date.date().isoformat()}'

        if not self.output:
            self.output = f'{os.path.abspath(f"{self.name}_{self.date.date().isoformat()}.html")}'

        if not self.name:
            raise KeyError('Monitor name not set. Please set the monitor name.')

        self.define_plot()
        self.results = self.track()
        self.outliers = self.find_outliers()

        if self.subplots:
            self.figure = tools.make_subplots(*self.subplot_layout)

        else:
            self.figure = go.Figure()

        if self.labels:
            self.hover_text = pd.Series(
                ['<br>'.join(list(row.astype(str))) for _, row in self.data[self.labels].iterrows()]
            )

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'<{self.name} Monitor object>'

    def _check_plottype(self):
        if self.plottype and self.plottype not in ('scatter', 'image', 'line'):
            raise KeyError(
                f'{self.plottype} is not one of: "scatter", "image", "line". Please use one of those or set to None if '
                f'constructing a custom plot'
            )

    @property
    def data(self):
        return self._data_model.data

    @property
    def basic_layout(self):
        return go.Layout(title=self.name, hovermode='closest')

    def basic_scatter(self):
        self._basic_scatter('markers')

    def basic_line(self):
        self._basic_scatter('lines')

    def basic_image(self):
        self._basic_image()

    def notify(self, body):
        email = Email(self.notification_settings['username'], self.name, body, self.notification_settings['recipients'])
        email.send()

    def find_outliers(self):
        pass

    def track(self):
        raise NotImplementedError('Monitor must track something.')

    def notification_string(self):
        if self.notification_settings['active'] is True:
            raise NotImplementedError(
                'With notification settings activated, the monitoring results message must be constructed.'
            )

        else:
            pass

    def monitor(self):
        self.plot()
        off.plot(self.figure, filename=self.output, auto_open=False)

        if self.notification_settings and self.notification_settings['active'] is True:
            self.notify(self.notification_string())

    def define_plot(self):
        pass

    def plot(self):
        if self.plottype == 'scatter':
            self.basic_scatter()

        elif self.plottype == 'line':
            self.basic_line()

        else:
            self.basic_image()

        self.figure['layout'].update(self.basic_layout)

    def _basic_scatter(self, mode):
        scatter = go.Scatter(
            x=self.x,
            y=self.y,
            mode=mode,
            marker=dict(
                color=self.z,
                colorscale='Viridis',
                colorbar=dict(len=0.75),
                showscale=True
            ) if self.z is not None else None,
            name='Monitor',
            text=self.hover_text,
        )

        if self.outliers is not None:
            outliers = go.Scatter(
                x=self.x[self.outliers],
                y=self.y[self.outliers],
                mode='markers',
                marker=dict(color='red'),
                name='Outliers',
                text=self.hover_text[self.outliers],
            )

            self.figure.add_traces([scatter, outliers])

        else:
            self.figure.add_trace(scatter)

    def _basic_image(self):

        image_plot = go.Heatmap(
            x=self.x,
            y=self.y,
            z=self.image,
            colorscale='Viridis',
            zmin=0,
            zmax=np.median(self.image),
            zsmooth='best'
        )

        self.figure.add_trace(image_plot)
