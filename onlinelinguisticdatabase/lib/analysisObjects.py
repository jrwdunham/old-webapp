# −*− coding: UTF−8 −*−

# Copyright (C) 2010 Joel Dunham
#
# This file is part of OnlineLinguisticDatabase.
#
# OnlineLinguisticDatabase is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OnlineLinguisticDatabase is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with OnlineLinguisticDatabase.  If not, see
# <http://www.gnu.org/licenses/>.

import logging
import subprocess
import os
import codecs
import re
import pickle
import urllib

from datetime import datetime
from random import shuffle

try:
    import json
except ImportError:
    import simplejson as json

from pylons import config, session, app_globals

log = logging.getLogger(__name__)


class Phonology(object):

    def setup(self):
        self.getFilePaths()
        self.makeDirectory()
        self.writeFomaScript()
        self.writeCompileScript()

    def setID(self, id):
        self.id = id

    def getFilePaths(self):
        """Get the directory and 3 file paths for this phonology.

        """

        analysisDataDir = config['app_conf']['analysis_data']
        phonologyDirName = u'phonology_%d' % self.id
        self.phonologyDirPath = os.path.join(analysisDataDir, 'phonology',
                                             phonologyDirName)
        self.phonologyFilePath = os.path.join(self.phonologyDirPath,
                                            'phonology.foma')
        self.phonologyBinaryFilePath = os.path.join(self.phonologyDirPath,
                                            'phonology.foma.bin')
        self.phonologyCompileFilePath = os.path.join(self.phonologyDirPath,
                                            'phonologycompile.sh')

    def delete(self):
        """Delete the directories and files associated with this phonology.

        """

        self.getFilePaths()
        success = True
        try:
            os.remove(self.phonologyFilePath)
            os.remove(self.phonologyBinaryFilePath)
            os.remove(self.phonologyCompileFilePath)
            os.rmdir(self.phonologyDirPath)
        except OSError:
            success = False
            msg = 'One of the file paths is not valid or the directory is not \
                  empty'
            log.debug(msg)
        return success

    def makeDirectory(self):
        """Create the directory for this phonology: analysis/phonology_%d

        """

        try:
            os.mkdir(self.phonologyDirPath)
        except OSError:
            pass

    def writeFomaScript(self):
        log.debug('Writing phonology.foma.')
        phonologyFile = codecs.open(self.phonologyFilePath, 'w', 'utf-8')
        phonologyFile.write(self.script)
        phonologyFile.close()

    def writeCompileScript(self):
        log.debug('Writing phonologycompile.sh.')
        phonologyCompileFile = open(self.phonologyCompileFilePath, 'w')
        cmd = 'foma -e "source %s" -e "regex phonology;" -e "save stack %s" \
              -e "quit"' % (self.phonologyFilePath,
                            self.phonologyBinaryFilePath)
        phonologyCompileFile.write(cmd)
        phonologyCompileFile.close()
        os.chmod(self.phonologyCompileFilePath, 0755)

    def compile(self):
        log.debug('Generating phonology.foma.bin.')
        process = subprocess.Popen([self.phonologyCompileFilePath], shell=True,
            stdout=subprocess.PIPE)
        output = unicode(process.communicate()[0], 'utf-8')
        expectedOutput = u'Writing to file %s' % self.phonologyBinaryFilePath
        if expectedOutput in output:
            log.debug('Compilation succeeded.')
            self.compiledSuccessfully = True
        else:
            log.debug('Compilation failed.')
            log.debug(output)
            self.compiledSuccessfully = False

    def getAttributesInJSON(self):
        phonologyDict = self.getAttributesAsDict()
        return json.dumps(phonologyDict)

    def getAttributesAsDict(self):
        enterer = '%s %s' % (self.enterer.firstName,
                             self.enterer.lastName)
        if self.modifier:
            modifier = '%s %s' % (self.modifier.firstName,
                                 self.modifier.lastName)
        else:
            modifier = None
        datetimeEntered = self.datetimeEntered.strftime(
            '%H:%M on %b %d, %Y')
        datetimeModified = self.datetimeModified.strftime(
            '%H:%M on %b %d, %Y')
        if hasattr(self, 'compiledSuccessfully'):
            compiledSuccessfully = self.compiledSuccessfully
        else:
            compiledSuccessfully = None
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'script': self.script,
            'enterer': enterer,
            'modifier': modifier,
            'datetimeEntered': datetimeEntered,
            'datetimeModified': datetimeModified,
            'compiledSuccessfully': compiledSuccessfully
        }

    def phonologize(self, token):
        #log.debug('Phonologizing %s' % token)
        token = u'#%s#' % token
        cmdList = ['flookup', '-x', '-i', self.phonologyBinaryFilePath]
        process = subprocess.Popen(
            cmdList,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        process.stdin.write(token.encode('utf-8'))
        result = unicode(process.communicate()[0], 'utf-8').split('\n')
        return list(set([x[1:-1] for x in result if x]))

    def getTestsFromScript(self):
        #log.debug('Getting test expressions from script.')
        def getTestFromLine(line):
            return (line.split()[1], line.split()[2:])
        return [getTestFromLine(l) for l in
                codecs.open(self.phonologyFilePath, 'r', 'utf-8') if
                l[:5] == "#test"]

    def phonologizeInternalTests(self):
        #log.debug('Phonologizing script-internal tests.')
        tests = self.getTestsFromScript()
        return [(t[0], t[1], self.phonologize(t[0])) for t in tests]