import numpy as np

from monitoring.monitor import BaseDataModel
from monitoring.file_data import FileFinder

SOURCE = '/grp/hst/cos2/cosmo'


def dgestar_to_fgs(results):
    for item in results:
        item.update({'dom_fgs': item['DGESTAR'][-2:]})


def get_acq_data(acq_keys, acq_extensions, spt_keys, spt_extensions, exptype):
    finder = FileFinder(SOURCE, '*rawacq*', acq_keys, acq_extensions, spt_keys, spt_extensions, exptype)
    data_results = finder.data_from_files()

    if 'DGESTAR' in spt_keys:
        dgestar_to_fgs(data_results)

    return data_results


class AcqPeakdModel(BaseDataModel):

    def get_data(self):
        acq_keywords, acq_extensions = ('ACQSLEWX', 'EXPSTART', 'LIFE_ADJ', 'ROOTNAME', 'PROPOSID'), (0, 1, 0, 0, 0)
        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = get_acq_data(acq_keywords, acq_extensions, spt_keywords, spt_extensions, 'ACQ/PEAKD')

        return data_results


class AcqPeakxdModel(BaseDataModel):

    def get_data(self):
        acq_keywords, acq_extensions = ('ACQSLEWY', 'EXPSTART', 'LIFE_ADJ', 'ROOTNAME', 'PROPOSID'), (0, 1, 0, 0, 0)
        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = get_acq_data(acq_keywords, acq_extensions, spt_keywords, spt_extensions, 'ACQ/PEAKXD')

        return data_results


class AcqImageModel(BaseDataModel):

    def get_data(self):

        def detector_to_v2v3(slewx, slewy):
            """Detector coordinates to V2/V3 coordinates."""
            rotation_angle = np.radians(45.0)  # rotation angle in degrees converted to radians
            x_conversion = slewx * np.cos(rotation_angle)
            y_conversion = slewy * np.sin(rotation_angle)

            v2 = x_conversion + y_conversion
            v3 = x_conversion - y_conversion

            return v2, v3

        acq_keywords = (
            'ACQSLEWX', 'ACQSLEWY', 'EXPSTART', 'ROOTNAME', 'PROPOSID', 'OBSTYPE', 'NEVENTS', 'SHUTTER', 'LAMPEVNT',
            'ACQSTAT', 'EXTENDED', 'LINENUM'
        )
        acq_extensions = (0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0)

        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = get_acq_data(acq_keywords, acq_extensions, spt_keywords, spt_extensions, 'ACQ/IMAGE')

        for item in data_results:
            v2_values, v3_values = detector_to_v2v3(item['ACQSLEWX'], item['ACQSLEWY'])
            item.update({'V2SLEW': v2_values, 'V3SLEW': v3_values})

        return data_results
