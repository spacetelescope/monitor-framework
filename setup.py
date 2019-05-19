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

setup(name='monitorframe',  # Required
      version='0.0.3',  # Required
      description='Framework for building instrument monitors.',  # Required
      author='James White; Space Telescope Science Institute',
      author_email='jwhite@stsci.edu',
      # url=,

      # This is an optional longer description of your project that represents
      # the body of text which users will see when they visit PyPI.
      #
      # Often, this is the same as your README, so you can just read it in from
      # that file directly (as we have already done above)
      #
      # This field corresponds to the "Description" metadata field:
      # https://packaging.python.org/specifications/core-metadata/#description-optional
      # long_description=long_description,   Optional

      classifiers=['Intended Audience :: STScI',
                   'Topic :: Monitoring',

                   # Python versions supported.
                   'Programming Language :: Python :: 3'],

      install_requires=['pandas', 'plotly', 'peewee', 'numpy'],

      **setup_parameters
      )
