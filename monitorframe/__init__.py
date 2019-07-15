import os
import yaml

from .monitor import BaseDataModel, BaseMonitor


with open(os.environ['MONITOR_CONFIG']) as yamlfile:
    SETTINGS = yaml.safe_load(yamlfile)
