import os
import yaml

def load_config(config_file):
    # load config file
    config_file = os.path.join(os.path.dirname(__file__), config_file)
    with open(config_file, 'r') as ymlfile:
        cfg = yaml.safe_load(ymlfile)
        return cfg
