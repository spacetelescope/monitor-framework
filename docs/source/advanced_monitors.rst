Advanced Monitor Options
========================
In :doc:`creating_monitors` we outlined how to create a very simple monitor that produces a simple plot.
In this section we will dive into options available for creating a more complex Monitor.

.. note::

    There are no further options for creating DataModels, and so the previous section should be referenced for
    the creation of new DataModels.

Running the monitoring steps manually
-------------------------------------
If there is a need to run the monitoring steps manually, ``BaseMonitor`` includes the following methods that can be
called independently:

- ``initialize_data``: retrieve data defined by the data model set the data attribute, create hover text.
- ``run_analysis``: execute the track method, find outliers if defined, set notifications.
- ``plot``: create the plotly figure (creates the html output)
- ``write_figure``: save the plotly figure to an html file.
- ``notify``: send notifications

.. note::

    If the monitoring steps are run individually, they must be executed in logical order.
    For example, ``initialize_data`` must be executed first, followed by ``run_analysis`` if the intent is to only
    execute the analysis portion of the monitor.


Notifications
-------------
The ``monitorframe`` frame work provides support for email notifications upon execution of a monitor.

There are two steps for activating email notifications:

1. Define ``notification_settings`` in the new monitor class required keys:

    - *active*: turn the notifications on or off

    - *username*: user that's used for sending the messages

    - *recipients*: additional users that should be notified of results

2. Define the message that the monitor should send in ``set_notification``

For example:

.. code-block:: python

    class MyMonitor(BaseMonitor):
        data_model = MyNewModel
        notification_settings = dict(
            active=True,
            username='user',
            recipients=['other@stsci.edu', 'other2@stsci.edu']  # recipients can also be a single string if there's only one
        )

        plottype = 'line'
        x = 'col1'
        y = 'col2'

        def track(self):
            """Measure the mean of the first column"""
            return self.data.col1.mean()  # Remember that data is a pandas DataFrame!

        def set_notification(self):
            return f'The mean of col1 is {self.results}!'  # The return value of track is stored in the results attribute!

.. note::

    ``set_notification`` should return a string.

Databases
---------
``monitorframe`` provides support for and an interface to two SQLite databases through the ``peewee`` ORM with
one of these databases is for storing monitor data, while the other is used for storing monitoring analysis results.
Each of these databases are created automatically when configured, and tables for those databases are also automatically
created when the ingestion methods are called (``ingest`` for a DataModel and ``store_results`` for a Monitor).

The configuration of these databases is discussed in :doc:`overview`.

DataModel Database
^^^^^^^^^^^^^^^^^^
The main difference between the DataModel database and the Monitor results database is that while the Monitor results
database is pre-defined (although broadly), the DataModel database is *not*.
The table is constructed based on the input data, which means that each DataModel can have completely different sets of
columns.

This type of implementation does have a drawback though: due to the dynamic nature of how tables are defined, it's
possible to have unintended consequences in how the data is ingested.
In particular, it's possible to have duplicate entries.

To protect against this issue, it's recommended that DataModels are defined with a ``primary_key`` attribute.
This will prevent duplicate entries from being added to the database (an example of this is included in the
:doc:`creating_monitors` section).

Once the DataModel's database and table exist, the DataModel's ``model`` attribute can be utilized.
The ``model`` attribute is a ``peewee.Model`` object that represents the DataModel's table and can be used to query the
data stored there.

Users can take advantage of the DataModel's ``model`` attribute when implementing a Monitor's ``get_data`` method.

For examples of querying and filtering, see
`peewee's Querying section <http://docs.peewee-orm.com/en/latest/peewee/querying.html#selecting-multiple-records>`_.

Monitor Results Database
^^^^^^^^^^^^^^^^^^^^^^^^
Each Monitor that is defined will automatically create a database table based on the name of the
monitor if the ``store_results`` method is called (with the default method)::

    class, MyMonitor -> results database table name, "MyMonitor"

The results table is defined with two columns:
    1. ``Datetime``
    2. ``Result``

The ``Datetime`` column corresponds to the date and time that the monitor was executed.
Each monitor that is derived from ``BaseMonitor`` will have a ``date`` attribute that is set when an instance of the
monitor is created.
``date`` is a python ``datetime`` object, and will be stored in the "isoformat"

The ``Result`` column is a JSON field.
A JSON field is used to standardize the tables for each monitor while allowing for flexibility in what exactly each
monitor stores in the table.
The only caveat to this is that whatever results that users desire to store, must be compatible with python's ``json``
encoder and decoder which performs the following translations:

.. table::

    ============= ======
        JSON      Python
    ============= ======
    object        dict
    array         list
    string        str
    number (int)  int
    number (real) float
    true          True
    false         False
    null          None
    ============= ======

This means that whatever is intended to be stored should be composed of those Python data structures.
There is some support for this with pandas.
Both ``Series`` and ``DataFrame`` objects have a ``to_json`` method for automatically translating those data structures
to JSON friendly structures.

For more information on pandas' ``to_json`` method, see
`this <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html>`_, and for more on
Python's JSON encoder and decoder, see `their documentation <https://docs.python.org/3/library/json.html>`_.

.. _custom-storage:

The data database columns are defined based on the data recovered by the ``get_new_data`` method.

Storing and accessing results
.............................
``BaseMonitor`` does provide a "default" attempt at storing the results, but for more complicated results (or just for
more custom storage), a ``format_results`` method must be implemented.

Building off of the previous ``MyMonitor`` example:

.. code-block:: python

    def format_results(self):
        # Create a custom result with json-friendly python data structures
        results = {
            'my result 1': self.data.col1.to_json  # store the whole column if you want!
            'my result mean': self.results  # MyMonitor's track method returns the mean of col1
        }

        return results

The new entry will be created on execution, and if ``format_results`` has been implemented, that resulting object will
be used.

To query the Monitor's table for a specific result, ``results_table`` and the table's column definitions
(which are used in querying) are available as attributes:

.. code-block:: python

    monitor = MyMonitor()
    query_results = monitor.results_table  # Returns all results as a peewee ModelSelect object

    # Further querying
    more_specific = query_results.where(monitor.datetime_col == '2019-04-23T14:07:03.500365')

    # Format rows as a list of dictionaries
    list(more_specific.dicts())

.. note::

    If a Monitor has been defined, but has not been executed (specifically the ``store_results`` method), the database
    table for that monitor will not exist yet.
    In this case, the ``results_table`` property will be ``None``.

For information on how to perform queries, see
`peewee's documentation <http://docs.peewee-orm.com/en/latest/peewee/querying.html#selecting-multiple-records>`_.

Customizing Plotting
--------------------
``BaseMonitor`` provides some basic plotting functionality that produces ``ploty`` interactive plots.
There are some additional options that can be set for controlling this basic plotting

Setting a specific output file name or destination
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
By default, the resulting figure of a monitor derived from ``BaseMonitor`` will be given a name that is a combination
of the monitor's class name and the date that the monitor instance was created, and will be placed in the current
working directory.

To change the path of the output file, assign ``output`` to a directory:

.. code-block:: python

    class MyMonitor(BaseMonitor)
        data_model = MyNewModel
        ...
        output = '/new/path/to/file/'  # For setting the path, but not the filename

To change the name of the file, assign ``output`` to a full path:

.. code-block:: python

    class MyMonitor(BaseMonitor)
        data_model = MyNewModel
        ...
        output = '/new/path/to/file/new_file_name.html'  # For setting the path, but not the filename

Adding a third dimension to the output
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The basic plotting functionality of ``BaseMonitor`` restricts the dimensionality to 3 dimensions at the maximum (it is
basic after all).

The third dimension is a *color* dimension supports either an array of the same shape as ``x`` and ``y``.
To specify a color dimension to the data, simply set the ``z`` attribute.
The third dimension can also be used to create an image plot.

Adding additional information to the hover labels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If additional information should be displayed on hover for each data point, that information should be included the data
retrieved by the data model.

For example, if in the simple line plot created in :doc:`creating_monitors` needed to also include a "name" for each
data point, ``get_data`` would need to be modified like so:

.. code-block:: python

    class MyNewModel(BaseDataModel):
        def get_new_data(self):
            reuturn {
                'col1': [1, 2, 3],
                'col2': [4, 5, 6],
                'names': ['first', 'second', 'third']
            }

In the definition of the monitor, the new "names" column would need to be identified as a label:

.. code-block:: python

    class MyMonitor(BaseMonitor):
        data_model = MyNewModel
        labels = ['names']  # List of column names in data that should be used in hover labels

        plottype = 'line'
        x = 'col1'
        y = 'col2'

        def track(self):
            """Measure the mean of the first column"""
            return self.data.col1.mean()  # Remember that data is a pandas DataFrame!

This will add each "name" to the corresponding point in the hover labels in the plotly figure.

More complex plotting
^^^^^^^^^^^^^^^^^^^^^
For more complex plotting, ``plot`` should be overridden with whatever is needed, but ``plotly`` is still required.

When a new instance of a monitor is created, a plotly figure is created automatically.

.. note::

    If subplots are needed, the ``subplots`` and ``subplots_layout`` attributes need to be defined in the monitor class.
    This is because the plotly figure object is different for subplots.

    To set the monitor to use a subplots figure:

    .. code-block:: python

        class MyMonitor(BaseMonitor):
            data_model = MyNewModel
            ...
            subplots = True
            subplot_layout = (2, 2)  # 2x2 grid of plots


The ``plot`` method should add whatever *traces* (``plotly``'s term) and *layouts* necessary to that monitor figure
attribute:

.. code-block:: python

    def plot(self):

        ...  # Lot's of complicated plotting stuff that results in a "plot" trace object and a new layout object

        self.figure.add_trace(plot)
        self.figure['layout'].update(layout)

If users want to integrate existing matplotlib plots without have to rewrite the entire plot, ``plotly``'s
``mpl_to_plotly`` function can be used:

.. code-block:: python

    import plotly.tools as tls

    new_plotly = tls.mpl_to_plotly(existing_mpl_figure)

This figure could then be assigned to the figure attribute on the monitor:

.. code-block:: python

    def plot(self):
        self.figure = new_plotly

Once plotting is all done, the figure can be written to an html file (with the default or specified path and/or name)
with the ``write_figure`` method:

.. code-block:: python

    monitor.write_figure()

Finding Outliers
----------------
If part of the monitor is to locate outliers, then the ``find_outliers`` method must be implemented.
This method should return a *mask* array that can be used with the ``data`` attribute of the Monitor if the user intends
to use the basic plotting functionality, but otherwise can return whatever is needed.

Outliers will be accessible via the ``outliers`` attribute of the monitor.
When using the basic plotting functionality, outliers will automatically be plotted in red, but for more advanced
plotting that requires that the ``plot`` method be overridden, the user will have to determine how to visualize any
outliers.

For example, if we add a ``find_outliers`` implementation to ``MyMonitor``:

.. code-block:: python

    def find_outliers(self):
        return self.data.col1 > 1  # Returns a pandas Series mask

After the analysis has been run, you can access the outlying data with:

.. code-block:: python

    monitor = MyMonitor()
    monitor.monitor()

    outliers = monitor.data[monitor.outliers]
