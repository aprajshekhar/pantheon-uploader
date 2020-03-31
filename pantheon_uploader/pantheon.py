#!/usr/bin/python3
import argparse
import base64
import getpass
import logging
import os

import sys
from pathlib import PurePath

import requests
import yaml
from requests import Response
from pprint import pprint

from pantheon_uploader import logger
from pantheon_uploader.constants import HEADERS
from pantheon_uploader.helpers import ConfigHelper
from pantheon_uploader.processor import Processor
from pantheon_uploader.utils import LogUtils, FileUtils

DEFAULT_SERVER = 'http://localhost:8080'
DEFAULT_USER = 'author'
DEFAULT_PASSWORD = base64.b64decode(b'YXV0aG9y').decode()


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description='''\
Red Hat bulk upload module for Pantheon 2. This tool will scan a directory recursively and upload relevant files.

Both this uploader and Pantheon 2 are ALPHA software and features may update or change over time.

''')
parser.add_argument('push', nargs='+', help='Type of operation, default push')
parser.add_argument('--server', '-s', help='The Pantheon server to upload modules to, default ' + DEFAULT_SERVER)
parser.add_argument('--repository', '-r', help='The name of the Pantheon repository')
parser.add_argument('--attrFile', '-f', help='Path to the attribute File', dest='attrFile')
parser.add_argument('--user', '-u', help='Username for authentication, default \'' + DEFAULT_USER + '\'',
                    default=DEFAULT_USER)
parser.add_argument('--password', '-p',
                    help='Password for authentication, default \'' + DEFAULT_PASSWORD + '\'. If \'-\' is supplied, the script will prompt for the password.',
                    default=DEFAULT_PASSWORD)
parser.add_argument('--directory', '-d',
                    help='Directory to upload, default is current working directory. (' + os.getcwd() + ')',
                    default=os.getcwd())
parser.add_argument('--verbose', '-v', help='Print information that may be helpful for debugging', action='store_const',
                    const=True)
parser.add_argument('--dry', '-D',
                    help='Dry run; print information about what would be uploaded, but don\'t actually upload',
                    action='store_const', const=True)
parser.add_argument('--sandbox', '-b',
                    help='Push to the user\'s personal sandbox. This parameter overrides --repository',
                    action='store_const', const=True)
parser.add_argument('--sample', '-S',
                    help='Print a sample pantheon2.yml file to stdout (which you may want to redirect to a file).',
                    action='version', version='''\
# Config file for Pantheon v2 uploader
## server: Pantheon server URL
## repository: a unique name, which is visible in the user facing URL

## Note: Due to yaml syntax, any filepaths that start with a wildcard must be surrounded in quotes like so:
# modules:
#  - '*.adoc'

server: http://localhost:8080
repositories:
  - name: pantheonSampleRepo
    attributes: path/to/attribute.adoc

    modules:
      - master.adoc
      - modules/*.adoc

    resources:
      - shared/legal.adoc
      - shared/foreword.adoc
      - resources/*
''')
args = parser.parse_args()

logStr = 'DEBUG' if args.verbose is not None else 'WARNING'
numeric_level = getattr(logging, logStr, None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % args.log)

logger.setLevel(numeric_level)
logger.addHandler(logging.StreamHandler())

pw = args.password
if pw == '-':
    pw = getpass.getpass()

config_helper = ConfigHelper(args.directory)
config = config_helper.configure()


def resolveOption(parserVal, configKey, default):
    if parserVal is not None:
        return parserVal
    elif config is not None and configKey in config:
        return config[configKey]
    else:
        return default


def exists(path):
    """Makes a head request to the given path and returns a status_code"""
    try:
        resp = requests.head(path)
        logger.debug('HEAD request to remote server. Response status_code: %s', resp.status_code)
        return resp.status_code < 400
    except Exception:
        return False


def remove_trailing_slash(path):
    """Removes the trailing slash from path if exists and returns a string"""
    if path.endswith('/'):
        path = path[:-1]
    return path


def process_workspace(path):
    """
    Adds pant:attributeFile to the repository node.
    Parameter:
    path: string
    """
    content_root = 'sandbox' if args.sandbox else 'repositories'
    url = server + '/content/' + content_root + '/' + repository

    # Specify attributeFile property
    logger.debug('url: %s', url)
    data = {}
    data['jcr:primaryType'] = 'pant:workspace'
    if attributeFile:
        data['pant:attributeFile'] = attributeFile
    if not args.dry:
        r: Response = requests.post(url, headers=HEADERS, data=data, auth=(args.user, pw))
        LogUtils.print_response('workspace', path, r.status_code, r.reason)
    logger.debug('')


def readYamlGlob(config, keyword):
    globs = config[keyword] if config is not None and keyword in config else ()
    logger.debug('keyword: $s', keyword)
    logger.debug('config[keyword] $s', config[keyword])
    if globs is not None:
        for i, val in enumerate(globs):
            globs[i] = val.replace('*', '[^/]+')
            logger.debug('key:val => $s : $s', i, val)

    return globs


server = resolveOption(args.server, 'server', DEFAULT_SERVER)
# Check if server url path reachable
server = remove_trailing_slash(server)
if exists(server + '/pantheon'):
    logger.debug('server: %s is reachable', server)
else:
    sys.exit('server ' + server + ' is not reachable')

LogUtils.info('Using server: ' + server)

if len(config.keys()) > 0 and 'repositories' in config:
    for repo_list in config['repositories']:
        repository = resolveOption(args.repository, '', repo_list['name'])
        # Enforce a repository being set in the pantheon.yml
        if repository == "" and mode == 'repository':
            sys.exit('repository is not set')

        mode = 'sandbox' if args.sandbox else 'repository'
        # override repository if sandbox is chosen (sandbox name is the user name)
        if args.sandbox:
            repository = args.user

        if 'attributes' in repo_list:
            attributeFile = resolveOption(args.attrFile, '', repo_list['attributes'])
        else:
            attributeFile = resolveOption(args.attrFile, '', '')

        if args.attrFile:
            if not os.path.isfile(args.directory + '/' + args.attrFile):
                sys.exit('attributes: ' + args.directory + '/' + args.attrFile + ' does not exist.')

        elif attributeFile and not os.path.isfile(attributeFile.strip()):
            sys.exit('attributes: ' + attributeFile + ' does not exist.')

        LogUtils.info('Using ' + mode + ': ' + repository)
        LogUtils.info('Using attributes: ' + attributeFile)
        print('--------------')

        process_workspace(repository)

        moduleGlobs = readYamlGlob(repo_list, 'modules')
        resourceGlobs = readYamlGlob(repo_list, 'resources')

        if attributeFile:
            if resourceGlobs == None:
                resourceGlobs = [attributeFile]
            else:
                resourceGlobs = resourceGlobs + [attributeFile]
        non_resource_files = []
        logger.debug('moduleGlobs: %s', moduleGlobs)
        logger.debug('resourceGlobs: %s', resourceGlobs)
        logger.debug('args.directory: %s', args.directory)

        # List all files in the directory
        allFiles = []
        FileUtils.listdir_recursive(args.directory, allFiles)

        # FileUtils.processRegexMatches(allFiles, resourceGlobs, 'resources')
        # FileUtils.processRegexMatches(allFiles, moduleGlobs, 'modules')
        processor = Processor(dry=args.dry, sandbox=args.sandbox,
                              repository=repository, directory=args.directory, server=server, user=args.user, pw=pw)
        processor.processRegexMatches(allFiles, resourceGlobs, 'resources')
        processor.processRegexMatches(allFiles, resourceGlobs, 'modules')
        leftoverFiles = len(allFiles)
        if leftoverFiles > 0:
            LogUtils.warn(f'{leftoverFiles} additional files detected but not uploaded. Only files specified in '
                          + config_helper.CONFIG_FILE
                          + ' are handled for upload.')

print('Finished!')
