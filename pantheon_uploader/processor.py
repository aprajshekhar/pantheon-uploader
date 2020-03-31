import os
import re
from pathlib import PurePath

import requests

from pantheon_uploader import logger
from pantheon_uploader.constants import HEADERS
from pantheon_uploader.utils import LogUtils


class Processor:

    def __init__(self,  dry, sandbox, repository, directory, server, user, pw):
        #self.path = path
        self.dry = dry
        self.sandbox = sandbox
        self.repository = repository
        self.directory = directory
        self.server = server
        self.user = user
        self.pw = pw

    def processRegexMatches(self, files, globs, filetype):
        matches = []
        logger.debug(' === ' + filetype)
        for f in files:
            if os.path.islink(f):
                logger.debug(f)
                logger.debug(' -- is symlink')
                matches.append(f)
                self.__process_file__(f)
            else:
                subpath = str(f)[len(self.directory) + 1:]
                logger.debug(' Evaluating ' + subpath)
                for regex in globs or []:
                    if re.match(regex, subpath):
                        logger.debug(' -- match ' + filetype + ' ' + regex)
                        matches.append(f)
                        self.__process_file__(f, filetype)
                        break  # necessary because the same file could potentially match more than 1 wildcard
        for f in matches:
            files.remove(f)

    def __process_file__(self, path, filetype):
        """
        Processes the matched files and upload to pantheon through sling api call

        Paramters:
        path (string): A file path
        filetype (string): A type of file(assemblies [someday], modules or resources)

        Returns:
        list: It returns a list with value of the API call status_code and reason
        """
        isModule = True if filetype == 'modules' else False
        isResource = True if filetype == 'resources' else False
        content_root = 'sandbox' if self.sandbox else 'repositories'
        url = self.server + '/content/' + content_root + '/' + self.repository

        path = PurePath(path)
        base_name = path.stem

        ppath = path
        hiddenFolder = False
        while not ppath == PurePath(self.directory):
            logger.debug('ppath: %s', str(ppath.stem))
            if ppath.stem[0] == '.':
                hiddenFolder = True
                break
            ppath = ppath.parent
        if hiddenFolder:
            logger.debug('Skipping %s because it is hidden.', str(path))
            logger.debug('')
            return

        # parent directory
        parent_dir_str = str(path.parent.relative_to(self.directory))
        if parent_dir_str == '.':
            parent_dir_str = ''
        logger.debug('parent_dir_str: %s', parent_dir_str)
        # file becomes a/file/name (no extension)

        if parent_dir_str:
            url += '/' + parent_dir_str

        logger.debug('base name: %s', base_name)

        # Asciidoc content (treat as a module)
        if isModule:
            self.__process__module(base_name, path, url)
        elif isResource:
            if os.path.islink(path):
                self.__process_resources__(path, url)
            else:
                self.__process_generic__(path, url)
        logger.debug('')

    def __process_generic__(self, path, url):
        # determine the file content type, for some common ones
        file_type = None
        if path.suffix in ['.adoc', '.asciidoc']:
            file_type = 'text/x-asciidoc'
        # Upload as a regular file(nt:file)
        logger.debug('url: %s', url)
        files = {path.name: (path.name, open(path, 'rb'), file_type)}
        if not self.dry:
            r = requests.post(url, headers=HEADERS, files=files, auth=(self.user, self.pw))
            LogUtils.print_response('resource', path, r.status_code, r.reason)

    def __process_resources__(self, path, url):
        target = str(os.readlink(path))
        url += '/' + path.name
        logger.debug('url: %s', url)
        if target[0] == '/':
            LogUtils.error('Absolute symlink paths are unsupported: ' + str(path) + ' -> ' + target)
        elif not self.dry:
            symlinkData = {}
            symlinkData['jcr:primaryType'] = 'pant:symlink'
            symlinkData['pant:target'] = target
            r = requests.post(url, headers=HEADERS, data=symlinkData, auth=(self.user, self.pw))
            LogUtils.print_response('symlink', path, r.status_code, r.reason)

    def __process__module(self, base_name, path, url):
        url += '/' + path.name
        logger.debug('url: %s', url)
        jcr_primary_type = 'pant:module'
        data = self.__generate_data__(jcr_primary_type, base_name, path.name, asccidoc_type='nt:file')
        # This is needed to add a new module version, otherwise it won't be handled
        data[':operation'] = 'pant:newModuleVersion'
        files = {'asciidoc': ('asciidoc', open(path, 'rb'), 'text/x-asciidoc')}
        # Minor question: which is correct, text/asciidoc or text/x-asciidoc?
        # It is text/x-asciidoc. Here's why:
        # https://tools.ietf.org/html/rfc2045#section-6.3
        # Paraphrased: "If it's not an IANA standard, use the 'x-' prefix."
        # Here's the list of standards; text/asciidoc isn't in it.
        # https://www.iana.org/assignments/media-types/media-types.xhtml#text
        if not self.dry:
            r = requests.post(url, headers=HEADERS, data=data, files=files, auth=(self.user, self.pw))
            LogUtils.print_response('module', path, r.status_code, r.reason)

    def __generate_data__(self, jcr_primary_type, base_name, path_name, asccidoc_type):
        """
        Generate the data object for the API call.
        """
        data = {}
        if jcr_primary_type:
            data['jcr:primaryType'] = jcr_primary_type
        if base_name:
            data['jcr:title'] = base_name
            data['jcr:description'] = base_name
        if path_name:
            data['pant:originalName'] = path_name
        if asccidoc_type:
            data['asciidoc@TypeHint'] = asccidoc_type

        return data