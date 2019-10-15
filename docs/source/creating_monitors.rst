Creating New Monitors
=====================
A new monitor is created by defining a DataModel and Monitor through building off of the ``BaseDataModel`` and
``BaseMonitor`` classes.

Defining a New Data Model
-------------------------
To define a DataModel, construct a new class that inherits ``BaseDataModel``, and implement the ``get_new_data`` method:

.. code-block:: python

    MyNewModel(BaseDataModel)
        primary_key = 'col1'  # if the database is in use, it may be helpful to define a primary key

        def get_new_data(self):
            return {
                'col1': [1, 2, 3],
                'col2': [4, 5, 6]
            }

In this simple example, ``get_new_data`` simply returns  a dictionary that represents column-oriented data.
However, ``get_new_data`` can return any data structure that is compatible with generating a pandas ``DataFrame``.

The user should be careful that whatever data structure they choose to use actually results in the correct
representation upon conversion to a ``DataFrame``.
For more on the pandas ``DataFrame`` check out
`their documentation <https://pandas.pydata.org/pandas-docs/stable/getting_started/dsintro.html#dataframe>`_.

And that's it!

If database support is being utilized, data can be ingested into the database with the ``ingest`` method.

On the first call of ``ingest``, the database defined in the configuration file will be created along with a table that
corresponds to ``MyNewModel`` (and in fact will have the same name as that class).

Once data is ingested into the database, the DataModel defines an interface to that data with the ``model`` attribute.
``model`` is a ``peewee.Model`` object that is dynamically defined by introspecting the ``MyNewModel``'s database table.
This object can be used to query the table.

Defining a New Monitor
----------------------
Once a DataModel is defined, a new Monitor can also be defined.
Like the DataModel, a new monitor is defined by constructing a class that inherits ``BaseMonitor``.

``BaseMonitor`` has some basic functionality included at the start that users can take advantage of for simple monitors,
however, at minimum, the ``get_data`` and ``track`` methods must be implemented and the monitor must have a
DataModel assigned to it.
If the results database is not defined in the configuration file, the ``store_results`` must also be implemented.

``get_data`` should be where the monitor accesses the data from the data model and performs any filtering required for
analysis.
The results of get data are stored in the ``data`` attribute.

``track`` defines what the monitor is quantitatively "monitoring," and can return anything that the user wants.
The results of this method are stored in the ``results`` attribute which can be utilized elsewhere in the monitor (such
areas like ``plot``, ``set_notifications``, or ``store_results``).

For example, to create a basic, bare-bones monitor that produces a line plot that represents the data defined in
``MyNewModel`` the following could be done:

.. code-block:: python

    # Note: In this case, it's implied that the results database is configured
    class MyMonitor(BaseMonitor):
        data_model = MyNewModel

        plottype = 'line'
        x = 'col1'
        y = 'col2'

        def get_data(self):
            return self.model.new_data

        def track(self):
            """Measure the mean of the first column"""
            return self.data.col1.mean()  # Remember that data is a pandas DataFrame!

This basic monitor will produce a simple ``plotly`` line graph when the ``monitor`` method is called.

In this casse, the monitor will store the results in the corresponding database table.
For for more complex results that users wish to store, a ``format_results`` method will need to be implemented (see
:ref:`Storing and accessing results <custom-storage>`).

To execute the monitor, create an instance of ``MyMonitor`` and execute the ``monitor`` method:

.. code-block:: python

    monitor = MyMonitor()
    monitor.monitor()
