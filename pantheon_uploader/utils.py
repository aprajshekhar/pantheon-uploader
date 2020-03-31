import os
from pathlib import PurePath

from pantheon_uploader import logger


class LogUtils:
    @staticmethod
    def info(message, colored=True):
        """
        Print an info message on the console. Warning messages are cyan
        """
        if colored:
            print('\033[96m{}\033[00m'.format(message))
        else:
            print(message)

    @staticmethod
    def warn(message, colored=True):
        """
        Print a warning message on the console. Warning messages are yellow
        """
        if colored:
            print('\033[93m{}\033[00m'.format(message))
        else:
            print(message)

    @staticmethod
    def error(message, colored=True):
        """
        Print an error message on the console. Warning messages are red
        """
        if colored:
            print('\033[91m{}\033[00m'.format(message))
        else:
            print(message)

    @staticmethod
    def print_response(filetype, path, response_code, reason):
        """
        Prints an http response in the appropriate terminal color
        """
        if 200 <= response_code < 300:
            LogUtils.info(filetype + ': ' + str(path), False)
            LogUtils.info(str(response_code) + ' ' + reason, True)
        elif response_code >= 500:
            LogUtils.error(filetype + ': ' + str(path), True)
            LogUtils.error(str(response_code) + ' ' + reason, True)
        else:
            print(response_code, reason)


class FileUtils:
    @staticmethod
    def listdir_recursive(directory, allFiles):
        for name in os.listdir(directory):
            if name == 'pantheon2.yml' or name[0] == '.':
                continue
            path = PurePath(str(directory) + '/' + name)
            if os.path.isdir(path) and not os.path.islink(path):
                FileUtils.listdir_recursive(path, allFiles)
            else:
                allFiles.append(path)


