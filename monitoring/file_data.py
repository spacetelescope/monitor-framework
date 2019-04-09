import os
import dask
import re

from glob import glob
from astropy.io import fits


def keywords_from_acqs_spts(acq_keywords, acq_extensions, spt_keywords, spt_extensions, exptype=None):
    all_cos_files = find_all_files()

    rawacqs = [item for item in all_cos_files if 'rawacq' in item]

    spts = []
    for acq in rawacqs:
        path, name = os.path.split(acq)
        spt_name = '_'.join([name.split('_')[0], 'spt.fits.gz'])
        spts.append(os.path.join(path, spt_name))

    rawacqs.sort(key=os.path.basename), spts.sort(key=os.path.basename)

    acq_results = get_keywords_from_files(rawacqs, acq_keywords, acq_extensions, exptype=exptype)
    spt_results = get_keywords_from_files(spts, spt_keywords, spt_extensions, exptype=exptype)

    for acq_dict, spt_dict in zip(acq_results, spt_results):
        acq_dict.update(spt_dict)

    del spt_results

    return acq_results


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
