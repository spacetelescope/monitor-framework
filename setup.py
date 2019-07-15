#!/usr/bin/env python
from setuptools import setup

setup_parameters = dict(
    packages=['monitorframe', ],
    package_dir={
        'monitorframe': 'monitorframe',
        'monitorframe.monitor': 'monitorframe/monitor',
        'monitorframe.database': 'monitorframe/database'
    }
)

setup(
    name='monitorframe',  # Required
    version='0.0.4',  # Required
    description='Framework for building instrument monitors.',  # Required
    author='James White; Space Telescope Science Institute',
    author_email='jwhite@stsci.edu',
    classifiers=[
        'Intended Audience :: STScI',
        'Topic :: Monitoring',

        # Python versions supported.
        'Programming Language :: Python :: 3'
    ],
    
    python_requires='~=3.6',
    install_requires=['pandas', 'plotly', 'peewee', 'numpy', 'pyyaml'],
    **setup_parameters
)
