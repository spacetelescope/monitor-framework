Overview
=========
The ``monitorframe`` framework consists of two components:

1. data model
2. monitor


Data Model
----------
The data model defines the source of the data for the monitor.
Data that is collected via the data model will be converted to a pandas ``DataFrame``.

Monitor
-------
The monitor defines the analysis done on the data retrieved by the data model as well as output (typically a plot) and
how the monitor results are stored in the results database.

Database Support
----------------
Database support is provided via ``peewee``, but this is entirely optional and other storage options can be used (or
not).
Currently the only database type that is supported is SQLite.

To use database support, the ``SETTINGS`` variable should be updated in ``database_config.py``.
``SETTINGS`` is a dictionary that defines the arguments used for creating a SQLite database as explained in
`peewee's documentation <http://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html#getting-started>`_ in a dictionary.

A very simple example of a configuration:

.. code-block:: python

    SETTINGS = dict(database='mydb.db')

If a database is configured, each monitor that is defined will have a corresponding table defined in the database
automatically.
Monitoring results (defined by the user per monitor) will be stored in the corresponding table.