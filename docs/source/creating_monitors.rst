Creating New Monitors
=====================
A new monitor is created by defining a data model and monitor through building off of the ``BaseDataModel`` and
``BaseMonitor`` classes.

Defining a New Data Model
-------------------------
To define a data model, construct a new class that inherits ``BaseDataModel``, and implement the ``get_data`` method:

.. code-block:: python

    MyNewModel(BaseDataModel)
        def get_data(self):
            return {
                'col1': [1, 2, 3],
                'col2': [4, 5, 6]
            }

In this simple example, ``get_data`` simply returns  a dictionary that represents column-oriented data.
However, ``get_data`` can return any data structure that is compatible with generating a pandas ``DataFrame``.
The user should be careful that whatever data structure they choose to use actually results in the correct
representation upon conversion to a ``DataFrame``, which will be accessible to the monitor through its ``data``
attribute (for more on the pandas ``DataFrame`` check out
`their documentation <https://pandas.pydata.org/pandas-docs/stable/getting_started/dsintro.html#dataframe>`_)

And that's it!

Defining a New Monitor
----------------------
Once a data model is defined, a new monitor can also be defined.
Like the data model, a new monitor is defined by constructing a class that inherits ``BaseMonitor``.
``BaseMonitor`` has some basic functionality included at the start that users can take advantage of for simple monitors.

For example, to create a basic, bare-bones monitor that produces a line plot that represents the data defined in
``MyNewModel`` the following could be done:

.. code-block:: python

    class MyMonitor(BaseMonitor):
    data_model = MyNewModel

    def track(self):
        """Measure the mean of the first column"""
        return self.data.col1.mean()  # Remember that data is a pandas DataFrame!

    def define_plot(self):
        self.plottype = 'line'
        self.x = self.data.col1
        self.y = self.data.col2

This basic monitor will produce a simple ``plotly`` line graph when run.

If a database has been defined, the monitor will attempt to store them in the corresponding database table.
However, for more complicated results that users wish to store, a custom ``stores_results`` method will need to be
implemented.

