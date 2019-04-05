import numpy as np
import plotly.graph_objs as go

from monitoring.monitor import Monitor
from monitoring.data_models import AcqImageModel


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

        layout = self.basic_layout

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
                    text=self.hover_text[group.index]
                )
            )

        lines = {
            fgs: [
                {
                    'type': 'line',
                    'x0': mean_x[fgs],
                    'y0': 0,
                    'x1': mean_x[fgs],
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
                    'y0': mean_y[fgs],
                    'x1': 1,
                    'y1': mean_y[fgs],
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
                active=1,
                buttons=[
                    dict(
                        label='FGS1',
                        method='update',
                        args=[{'visible': [True, False, False]}, {'title': 'FGS1', 'shapes': lines['F1']}]
                    ),
                    dict(
                        label='FGS2',
                        method='update',
                        args=[{'visible': [False, True, False]}, {'title': 'FGS2', 'shapes': lines['F2']}]
                    ),
                    dict(
                        label='FGS3',
                        method='update',
                        args=[{'visible': [False, False, True]}, {'title': 'FGS3', 'shapes': lines['F3']}]
                    )
                ]
            ),
        ]

        layout = go.Layout(updatemenus=updatemenus, hovermode='closest')

        self.figure.add_traces(traces)
        self.figure['layout'].update(layout)


if __name__ == '__main__':
    monitor = AcqImageFGSMonitor()
    monitor.monitor()
