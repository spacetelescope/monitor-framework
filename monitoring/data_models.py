import numpy as np

from monitoring.monitor import DataModel
from monitoring.file_data import keywords_from_acqs_spts


class AcqImageModel(DataModel):

    def get_data(self):
        keywords, extensions = ('ACQSLEWX', 'ACQSLEWY', 'EXPSTART', 'ROOTNAME', 'PROPOSID', ), (0, 0, 1, 0, 0)
        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = keywords_from_acqs_spts(keywords, extensions, spt_keywords, spt_extensions, 'ACQ/IMAGE')

        for item in data_results:
            item.update({'dom_fgs': item['DGESTAR'][-2:]})

        return data_results


class AcqPeakdModel(DataModel):

    def get_data(self):
        acq_keywords, acq_extensions = ('ACQSLEWX', 'EXPSTART', 'LIFE_ADJ', 'ROOTNAME', 'PROPOSID'), (0, 1, 0, 0, 0)
        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = keywords_from_acqs_spts(acq_keywords, acq_extensions, spt_keywords, spt_extensions, 'ACQ/PEAKD')

        for item in data_results:
            item.update({'dom_fgs': item['DGESTAR'][-2:]})

        return data_results


class AcqPeakxdModel(DataModel):

    def get_data(self):
        acq_keywords, acq_extensions = ('ACQSLEWY', 'EXPSTART', 'LIFE_ADJ', 'ROOTNAME', 'PROPOSID'), (0, 1, 0, 0, 0)
        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = keywords_from_acqs_spts(acq_keywords, acq_extensions, spt_keywords, spt_extensions, 'ACQ/PEAKXD')

        for item in data_results:
            item.update({'dom_fgs': item['DGESTAR'][-2:]})

        return data_results


class AcqImageV2V3Model(DataModel):

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
            'ACQSLEWX',
            'ACQSLEWY',
            'EXPSTART',
            'ROOTNAME',
            'PROPOSID',
            'OBSTYPE',
            'NEVENTS',
            'SHUTTER',
            'LAMPEVNT',
            'ACQSTAT',
            'EXTENDED',
            'LINENUM'
        )
        acq_extensions = (0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0, 0)

        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        data_results = keywords_from_acqs_spts(acq_keywords, acq_extensions, spt_keywords, spt_extensions)

        for item in data_results:
            v2_values, v3_values = detector_to_v2v3(item['ACQSLEWX'], item['ACQSLEWY'])
            item.update({'V2SLEW': v2_values, 'V3SLEW': v3_values})

            item.update({'dom_fgs': item['DGESTAR'][-2:]})

        return data_results

    def filter_data(self):

        index = np.where(
            (self.data.OBSTYPE == 'IMAGING') &
            (self.data.NEVENTS >= 2000) &
            (np.sqrt(self.data.V2SLEW ** 2 + self.data.V3SLEW ** 2) < 2) &
            (self.data.SHUTTER == 'Open') &
            (self.data.LAMPEVNT >= 500) &
            (self.data.ACQSTAT == 'Success') &
            (self.data.EXTENDED == 'NO')
        )

        partially_filtered = self.data.iloc[index]
        filtered_df = partially_filtered[partially_filtered.LINENUM.str.endswith('1')]

        return filtered_df
