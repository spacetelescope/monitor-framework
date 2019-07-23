import os
import yaml


with open(os.environ['MONITOR_CONFIG']) as yamlfile:
    SETTINGS = yaml.safe_load(yamlfile)
