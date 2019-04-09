import numpy as np
import plotly.graph_objs as go

from datetime import datetime
from astropy.time import Time
from itertools import repeat


from monitoring.monitor import Monitor
from monitoring.data_models import AcqImageModel, AcqImageV2V3Model, AcqPeakdModel


class AcqImageMonitor(Monitor):
    name = 'AcqImage Monitor'
    data_model = AcqImageModel
    plottype = 'scatter'
    labels = ['ROOTNAME', 'PROPOSID']
    output = '/Users/jwhite/Desktop/test.html'

    notification_settings = {
        'active': True,
        'username': 'jwhite',
        'recipients': 'jwhite@stsci.edu'
    }

    def track(self):
        return np.sqrt(self.data.ACQSLEWX ** 2 + self.data.ACQSLEWY ** 2)

    def find_outliers(self):
        return self.results >= 2

    def notification_string(self):
        return (
            f'{np.count_nonzero(self.outliers)} AcqImages were found to have a total slew of greater than 2 arcseconds'
        )

    def define_plot(self):
        self.x = -self.data.ACQSLEWX
        self.y = -self.data.ACQSLEWY
        self.z = self.data.EXPSTART
        self.plottype = 'scatter'


class AcqImageSlewMonitor(Monitor):
    name = 'AcImage Slew Monitor'
    data_model = AcqImageModel
    subplots = True
    subplot_layout = (2, 1)
    output = '/Users/jwhite/Desktop/test2.html'
    labels = ['ROOTNAME', 'PROPOSID']

    def track(self):
        xline = np.poly1d(np.polyfit(self.data.EXPSTART, self.data.ACQSLEWX, 1))
        yline = np.poly1d(np.polyfit(self.data.EXPSTART, self.data.ACQSLEWY, 1))
        return xline(self.data.EXPSTART), yline(self.data.EXPSTART), xline, yline

    def plot(self):
        xline, yline, xfit, yfit = self.results

        x_scatter = go.Scatter(
            x=self.data.EXPSTART,
            y=self.data.ACQSLEWX,
            name='Slew X',
            mode='markers',
            text=self.hover_text

        )

        y_scatter = go.Scatter(
            x=self.data.EXPSTART,
            y=self.data.ACQSLEWY,
            name='Slew Y',
            mode='markers',
            text=self.hover_text
        )

        xline_fit = go.Scatter(
            x=self.data.EXPSTART,
            y=xline,
            mode='lines',
            name=f'Fit:\nslope: {xfit[1]:.5f}\nintercept: {xfit[0]:.3f}'
        )

        yline_fit = go.Scatter(
            x=self.data.EXPSTART,
            y=yline,
            mode='lines',
            name=f'Fit:\nslop: {yfit[1]:.5f}\nintercept: {yfit[0]:.3f}'
        )

        layout = go.Layout(
            title=self.name,
            xaxis1=dict(title=self.data.EXPSTART.name),
            xaxis2=dict(title=self.data.EXPSTART.name),
            yaxis1=dict(title=self.data.ACQSLEWX.name),
            yaxis2=dict(title=self.data.ACQSLEWY.name)
        )

        self.figure.add_traces(
            [x_scatter, y_scatter, xline_fit, yline_fit],
            rows=[1, 2, 1, 2],
            cols=[1, 1, 1, 1]
        )

        self.figure['layout'].update(layout)


class AcqImageFGSMonitor(Monitor):
    name = 'AcqImage FGS Monitor'
    data_model = AcqImageModel
    labels = ['ROOTNAME', 'PROPOSID']
    output = '/Users/jwhite/Desktop/test3.html'

    def track(self):
        groups = self.data.sort_values('dom_fgs').reset_index(drop=True).groupby('dom_fgs')
        return groups, -groups.ACQSLEWX.mean(), -groups.ACQSLEWY.mean()

    def plot(self):
        groups, mean_x, mean_y = self.results

        average_text = {
            fgs: f'<br>Mean offset in X: {mean_x[fgs]:.3f}<br>Mean offset in Y: {mean_y[fgs]:.3f}'
            for fgs in self.data.dom_fgs.unique()
        }

        traces = []
        for name, group in groups:
            traces.append(
                go.Scatter(
                    x=-group.ACQSLEWX,
                    y=-group.ACQSLEWY,
                    mode='markers',
                    marker=dict(
                        color=group.EXPSTART,
                        colorscale='Viridis',
                        colorbar=dict(len=0.75),
                        showscale=True,
                    ),
                    name=name,
                    text=self.hover_text[group.index],
                    visible=False
                )
            )

        lines = {
            fgs: [
                {
                    'type': 'line',
                    'x0': -mean_x[fgs],
                    'y0': 0,
                    'x1': -mean_x[fgs],
                    'y1': 1,
                    'yref': 'paper',
                    'line': {
                        'color': 'red',
                        'width': 3,
                    }
                },

                {
                    'type': 'line',
                    'x0': 0,
                    'y0': -mean_y[fgs],
                    'x1': 1,
                    'y1': -mean_y[fgs],
                    'xref': 'paper',
                    'line': {
                        'color': 'red',
                        'width': 3,
                    },
                }
            ]
            for fgs in self.data.dom_fgs.unique()
        }

        updatemenus = [
            dict(
                active=10,
                buttons=[
                    dict(
                        label='FGS1',
                        method='update',
                        args=[
                            {'visible': [True, False, False]},
                            {'title': 'FGS1' + average_text['F1'], 'shapes': lines['F1']}
                        ]
                    ),
                    dict(
                        label='FGS2',
                        method='update',
                        args=[
                            {'visible': [False, True, False]},
                            {'title': 'FGS2' + average_text['F2'], 'shapes': lines['F2']}
                        ]
                    ),
                    dict(
                        label='FGS3',
                        method='update',
                        args=[
                            {'visible': [False, False, True]},
                            {'title': 'FGS3' + average_text['F3'], 'shapes': lines['F3']}
                        ]
                    )
                ]
            ),
        ]

        layout = go.Layout(updatemenus=updatemenus, hovermode='closest')

        self.figure.add_traces(traces)
        self.figure['layout'].update(layout)


# TODO: Figure out how to add the vertical lines to both subplots
class AcqImageV2V3Monitor(Monitor):
    name = 'V2V3 Offset Monitor'
    data_model = AcqImageV2V3Model
    labels = ['ROOTNAME', 'PROPOSID']
    subplots = True
    subplot_layout = (2, 1)
    output = '/Users/jwhite/Desktop/v2v3_test.html'

    break_points = {
        'F1': [
            ('start', 2011.172),
            (2011.172, 2013.205),  # FGS realignment
            (2013.205, 2014.055),  # FGS realignment
            (2014.055, 'end')  # SIAF update
        ],

        'F2': [
            ('start', 2011.172),
            (2011.206, 2013.205),  # FGS2 turned back on + FGS realignment
            (2013.205, 2014.055),  # FGS realignment
            (2014.055, 2015.327),  # SIAF update
            (2016.123, 'end')
        ],

        'F3': []  # No current break points for F3 yet
    }

    fgs_events = {
        'FGS realignment 1': 2011.172,
        'FGS2 turned on': 2011.206,
        'FGS realignment 2': 2013.205,
        'SIAF update': 2014.055,
        'FGS2 turned off': 2015.327,
        'FGS2 turned back on': 2016.123,
        'GAIA guide stars': 2017.272
    }

    @staticmethod
    def convert_day_of_year(date, mjd=False):
        t = datetime.strptime(str(date), '%Y.%j')

        if mjd:
            return Time(t, format='datetime').mjd

        return t

    @staticmethod
    def line(x, y):
        fit = np.poly1d(np.polyfit(x, y, 1))

        return fit, fit(x)

    def track(self):
        groups = self.data.groupby('dom_fgs')

        last_updated_results = dict()
        for name, group in groups:
            if name == 'F3':
                continue

            t_start = self.convert_day_of_year(self.break_points[name][-1][0], mjd=True)

            df = self.data[self.data.EXPSTART >= t_start]

            v2_line_fit = self.line(df.EXPSTART, df.V2SLEW)
            v3_line_fit = self.line(df.EXPSTART, df.V3SLEW)

            last_updated_results[name] = (v2_line_fit, v3_line_fit)

        return groups, last_updated_results

    def plot(self):
        fgs_groups, _ = self.results

        traces = {'F1': [], 'F2': []}
        rows = []
        cols = []
        for name, group in fgs_groups:

            if name == 'F3':
                continue

            for points in self.break_points[name]:

                t_start, t_end = [
                    self.convert_day_of_year(point, mjd=True) if not isinstance(point, str) else None
                    for point in points
                ]

                if t_start is None:
                    df = group[group.EXPSTART <= t_end]

                elif t_end is None:
                    df = group[group.EXPSTART >= t_start]

                else:
                    df = group.iloc[np.where((group.EXPSTART >= t_start) & (group.EXPSTART <= t_end))]

                if df.empty:
                    continue

                for i, slew in enumerate(['V2SLEW', 'V3SLEW']):
                    rows.append(i + 1)
                    rows.append(i + 1)
                    cols.append(1)
                    cols.append(1)

                    line_fit, fit = self.line(df.EXPSTART, -df[slew])

                    scatter = go.Scatter(
                        x=df.EXPSTART,
                        y=-df[slew],
                        name=slew,
                        mode='markers',
                        text=df.hover_text,
                        visible=False
                    )

                    line = go.Scatter(
                        x=df.EXPSTART,
                        y=fit,
                        name=f'Slope: {line_fit[1]:.5f}; Zero Point: {fit[0]:.3f}',
                        visible=False
                    )

                    traces[name].append(scatter)
                    traces[name].append(line)

        self.figure.add_traces([item for sublist in traces.values() for item in sublist], rows=rows, cols=cols)

        lines = [
            {
                'type': 'line',
                'x0': self.convert_day_of_year(value, mjd=True),
                'y0': -2,
                'x1': self.convert_day_of_year(value, mjd=True),
                'y1': 2,
                'yref': 'paper',
                'line': {
                    'width': 3,
                    'name': key
                }
            } for key, value in self.fgs_events.items()
        ]

        f1_visibility = list(repeat(True, len(traces['F1']))) + list(repeat(False, len(traces['F2'])))
        f2_visibility = list(repeat(False, len(traces['F1']))) + list(repeat(True, len(traces['F2'])))

        updatemenus = [
            dict(
                active=50,
                buttons=[
                    dict(
                        label='FGS1',
                        method='update',
                        args=[
                            {'visible': f1_visibility},
                            {'title': 'FGS1 V2V3 Slew vs Time', 'shapes': lines + lines}
                        ]
                    ),
                    dict(
                        label='FGS2',
                        method='update',
                        args=[
                            {'visible': f2_visibility},
                            {'title': 'FGS2 V2V3 Slew vs Time', 'shapes': lines + lines}
                        ]
                    ),
                ]
            ),
        ]

        layout = go.Layout(updatemenus=updatemenus, hovermode='closest')
        self.figure['layout'].update(layout)


class AcqPeakdMonitor(Monitor):
    name = 'AcqPeakd Monitor'
    data_model = AcqPeakdModel
    labels = ['ROOTNAME', 'PROPOSID']
    output = '/Users/jwhite/Desktop/acq_peakd.html'

    def track(self):
        groups = self.data.groupby('dom_fgs')
        scatter = groups.ACQSLEWX.mean()

        return groups, scatter

    def plot(self):
        fgs_groups, std_results = self.results

        traces = []
        for name, group in fgs_groups:
            scatter = go.Scatter(
                x=group.EXPSTART,
                y=-group.ACQSLEWX,
                mode='markers',
                text=group.hover_text,
                visible=False,
                marker=dict(
                    color=group.LIFE_ADJ,
                    colorscale='Viridis',
                    colorbar=dict(
                        len=0.75,
                        tickmode='array',
                        nticks=len(group.LIFE_ADJ.unique()),
                        tickvals=group.LIFE_ADJ.unique(),
                        ticktext=[f'LP{l}' for l in group.LIFE_ADJ.unique()]
                    ),
                    showscale=True,
                ),
                name=name,
            )

            traces.append(scatter)

        updatemenus = [
            dict(
                active=10,
                buttons=[
                    dict(
                        label='FGS1',
                        method='update',
                        args=[
                            {'visible': [True, False, False]},
                            {'title': 'FGS1 AcqPeakd Slew vs Time'}
                        ]
                    ),
                    dict(
                        label='FGS2',
                        method='update',
                        args=[
                            {'visible': [False, True, False]},
                            {'title': 'FGS2 AcqPeakd Slew vs Time'}
                        ]
                    ),
                    dict(
                        label='FGS3',
                        method='update',
                        args=[
                            {'visible': [False, False, True]},
                            {'title': 'FGS3 AcqPeakd Slew vs Time'}
                        ]
                    )
                ]
            )
        ]

        layout = go.Layout(updatemenus=updatemenus, hovermode='closest')
        self.figure.add_traces(traces)
        self.figure['layout'].update(layout)


if __name__ == '__main__':
    monitor = AcqPeakdMonitor()
    monitor.monitor()
