import os

import yaml

from pantheon_uploader import logger
from pantheon_uploader.constants import CONFIG_FILE


class ConfigHelper:

    def __init__(self, directory, config_file):
        self.directory = directory
        self.config_file = config_file | CONFIG_FILE

    def configure(self):

        config = None
        if not os.path.exists(self.directory):
            raise ValueError('Directory not found {}'.format(self.directory))
        try:
            config = yaml.safe_load(open(self.directory + '/' + self.config_file))

        except FileNotFoundError:
            logger.warning(
                'Could not find a valid config file(' + self.config_file + ') in this directory; all files will be treated as resource uploads.')
        logger.debug('config: %s', config)
        return config
