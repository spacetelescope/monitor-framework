import os

from .monitor import get_keywords_from_files, DataModel, find_all_files

ALL_COS_FILES = find_all_files()


class AcqImageModel(DataModel):

    def get_data(self):
        keywords, extensions = ('ACQSLEWX', 'ACQSLEWY', 'EXPSTART', 'ROOTNAME', 'PROPOSID'), (0, 0, 1, 0, 0)
        spt_keywords, spt_extensions = ('DGESTAR',), (0,)

        rawacqs = [item for item in ALL_COS_FILES if 'rawacq' in item]
        roots = [os.path.basename(item)[:9] for item in rawacqs]
        spts = [item for item in ALL_COS_FILES if os.path.basename(item)[:9] in roots and '_spt.' in item]

        roots.sort(key=os.path.basename), spts.sort(key=os.path.basename)

        acq_results = get_keywords_from_files(rawacqs, keywords, extensions, exptype='ACQ/IMAGE')
        spt_results = get_keywords_from_files(spts, spt_keywords, spt_extensions, exptype='ACQ/IMAGE')

        for acq_dict, spt_dict in zip(acq_results, spt_results):
            acq_dict.update(spt_dict)

        del spt_results

        for item in acq_results:
            item.update({'dom_fgs': item['DGESTAR'][-2:]})

        return acq_results
