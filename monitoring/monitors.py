import numpy as np
import dask
import plotly.graph_objs as go

from astropy.io import fits

from monitoring.monitor import Monitor, DataModel, find_all_files


class AcqImageModel(DataModel):

    def get_data(self):

        @dask.delayed
        def get_acqimagekeys(fitsfile):
            with fits.open(fitsfile) as acq:
                if acq[0].header['EXPTYPE'] == 'ACQ/IMAGE':
                    return {
                        'slewx': acq[0].header['ACQSLEWX'],
                        'slewy': acq[0].header['ACQSLEWY'],
                        'expstart': acq[1].header['EXPSTART'],
                        'rootname': acq[0].header['ROOTNAME'],
                        'program_id': acq[0].header['PROPOSID']
                    }

        rawacqs = [item for item in find_all_files() if 'rawacq' in item]

        delayed_data = [get_acqimagekeys(acqfile) for acqfile in rawacqs]
        results = [item for item in dask.compute(*delayed_data, scheduler='multiprocessing') if item is not None]

        return results


class AcqImageMonitor(Monitor):
    name = 'AcqImage Monitor'
    data_model = AcqImageModel
    plottype = 'scatter'
    labels = ['rootname', 'program_id']
    output = '/Users/jwhite/Desktop/test.html'

    notification_settings = {
        'active': True,
        'username': 'jwhite',
        'recipients': 'jwhite@stsci.edu'
    }

    def track(self):
        return np.sqrt(self.data.slewx ** 2 + self.data.slewy ** 2)

    def find_outliers(self):
        return self.results >= 2

    def notification_string(self):
        return (
            f'{np.count_nonzero(self.outliers)} AcqImages were found to have a total slew of greater than 2 arcseconds'
        )

    def define_plot(self):
        self.x = self.data.slewx
        self.y = self.data.slewy
        self.z = self.data.expstart
        self.plottype = 'scatter'


class AcqImageSlewMonitor(Monitor):
    name = 'AcImage Slew Monitor'
    data_model = AcqImageModel
    plottype = 'scatter'
    subplots = True
    subplot_layout = (2, 1)
    output = '/Users/jwhite/Desktop/test2.html'
    labels = ['rootname', 'program_id']

    def track(self):
        xline = np.poly1d(np.polyfit(self.data.expstart, self.data.slewx, 1))
        yline = np.poly1d(np.polyfit(self.data.expstart, self.data.slewy, 1))
        return xline(self.data.expstart), yline(self.data.expstart), xline, yline

    def plot(self):
        xline, yline, xfit, yfit = self.results

        x_scatter = go.Scatter(
            x=self.data.expstart,
            y=self.data.slewx,
            name='Slew X',
            mode='markers',
            text=self.hover_text

        )

        y_scatter = go.Scatter(
            x=self.data.expstart,
            y=self.data.slewy,
            name='Slew Y',
            mode='markers',
            text=self.hover_text
        )

        xline_fit = go.Scatter(
            x=self.data.expstart,
            y=xline,
            mode='lines',
            name=f'Fit:\nslope: {xfit[1]:.5f}\nintercept: {xfit[0]:.3f}'
        )

        yline_fit = go.Scatter(
            x=self.data.expstart,
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
