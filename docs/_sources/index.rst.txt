.. Monitor Framework documentation master file, created by
   sphinx-quickstart on Thu Apr 25 10:41:06 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Monitoring Framework
====================
Light-weight framework designed to make writing new instrument monitors quick and easy.

To install, clone the repository and use ``pip``::

   cd monitor-framework (or wherever the repo was cloned to)
   pip install .

Or execute ``setup.py`` directly::

   cd monitoring
   python setup.py

`monitorframe` requires that a ``yaml`` configuration file is created and set to an environment variable,
``MONITOR_CONFIG``.
This configuration file is used to define the monitoring data database and the monitoring results database, and should
have the following format:

.. code-block:: yaml

   # Monitor data database
   data:
     db_settings:
       database: ''
       pragmas:
         journal_mode: 'wal'
         foreign_keys: 1
         ignore_check_constraints: 0
         synchronous: 0

   # Monitor status and results database
   results:
     db_settings:
       database: ''
       pragmas:
         journal_mode: 'wal'
         foreign_keys: 1
         ignore_check_constraints: 0
         synchronous: 0

.. toctree::
   :maxdepth: 2
   :hidden:

   overview
   creating_monitors
   advanced_monitors