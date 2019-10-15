Overview
=========
The ``monitorframe`` framework consists of two components:

1. data model
2. monitor


DataModel
----------
The ``DataModel`` defines the source of the data for the monitor, how that data is collected, and defines an interface to
the database backend for the set of data defined by the DataModel.
Data that is collected via the data model will be converted to a pandas ``DataFrame``, and methods are included for
ingesting the new data that's collected into an SQlite3 database.

Monitor
-------
The monitor defines the analysis done on the data retrieved by the data model as well as output (typically a plot) and
how the monitor results are stored in the results database.

Database Support
----------------
Database support is provided via ``peewee``, but this is entirely optional and other storage options can be used (or
not).

Currently the only database type that is supported by default is SQLite3.

To use database support, provide a database filename in those sections of the configuration file:

.. code-block:: yaml

    # Monitor data database
    data:
     db_settings:
       database: 'my_database.db'
       pragmas:
         journal_mode: 'wal'
         foreign_keys: 1
         ignore_check_constraints: 0
         synchronous: 0

Additionally, SQLite3 pragma statements can be defined to further customize the database.

For more information on the configuration of the database and pragama statements, check out
`peewee's documentation <http://docs.peewee-orm.com/en/latest/peewee/sqlite_ext.html#getting-started>`_.

If a database is configured, each DataModel that is defined will automatically create the database (if it doesn't
exist), as well as a corresponding table in that database (again, if it doesn't exist) when the ``ingest`` method is
called.

For the monitoring results database, creation of the database and corresponding table is done automatically as with the
DataModel database when the ``store_results`` method is called.
