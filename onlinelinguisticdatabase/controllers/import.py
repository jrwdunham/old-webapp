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
import datetime
import os
import sys
import shutil
import codecs
from mimetypes import guess_type
import re
import zipfile

from lxml import etree

from paste.fileapp import FileApp

from pylons import config
from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, forward, redirect
from pylons.decorators import validate
from pylons.decorators.rest import restrict

from formencode.schema import Schema
from formencode import variabledecode
from formencode import htmlfill

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

log = logging.getLogger(__name__)


class NewUploadForm(Schema):
    """A Schema for validating that the only thing being uploaded is a file with
    an .xml extension.  Logic in the import.process() method will validate the
    OLD XML file uploaded against the Relax NG file 'oldxmlschmea.rng'
    
    (Future implementations may permit a compressed folder containing an OLD XML
    file plus a directory containing digital media (audio, video, images, etc.))
    
    """
    
    pass

    allow_extra_fields = True
    filter_extra_fields = True

def importOLDXML(OLDXMLFile_doc):
    """This function takes an lxml.etree.parse object, extracts the relevant
    data in the right order and inserts them into the OLD application's db.
    
    This is complicated by the relational dependencies of the OLD...
    
    Procedure:

    1. collect all independent entities (these are either children of
       the 'oldentities' root element or children of 'form', 'fo', 'file' or
       'collection' elements):

        independentEntities = {
            'elicitationMethod': {},
            'keyword': {},
            'page': {},
            'source': {},
            'speaker': {},
            'syntacticCategory': {}
            'user': {}
        }
        
       possibilities:
       
       - defined in oldentities root element
         - needs id and name
       - novel: defined (possibly redundantly) in form, fo, file, or collection
         elements
       - reference to entity existing in OLD Application's db

    2. For each to-be-entered independent entity, see if it already exists
       (with a reasonable criteria for 'already exists') in the database.  If it
       does, get it from the db; if
       duplicates exist,
       
    2. get the id of each new

    2. collect all primarily dependent entities:

        - file
        - form
        - fo
        - collection


        applicationSettings         DON'T IMPORT (?)
        collection                  10
            dependencies: speaker, source, user (elicitor, enterer)
        collectionBackup            11
            dependencies: collection, speaker, source, user (elicitor, enterer,
                backuper)
        collectionFile              12
            dependencies: collection, file
        collectionForm              12
            dependencies: collection, form
        elicitationMethod           1
        file                        10
            dependencies: speaker, user (elicitor, enterer)
        form                        10
            dependencies: gloss, user (elicitor, enterer, verifier), speaker,
                elicitation method, syntactic category, source, keyword, file,
                collection, memorizer
        fo                          10
            dependencies: gloss, user (elicitor, enterer, verifier), speaker,
                elicitation method, syntactic category, source, keyword, file,
                collection, memorizer
        formBackup                  11
            dependencies: gloss, user (elicitor, enterer, verifier, backuper),
                speaker, elicitation method, syntactic category, source,
                keyword, file, collection, memorizer
        formFile                    12
            dependencies: form, file
        formKeyword                 12
            dependencies: form, keyword
        gloss                       11?
            dependencies: form
        keyword                     1
        language                    DON'T IMPORT (?)
        page                        1
        source                      1
        speaker                     1
        syntacticCategory           1
        user                        1
        userForm                    11
            dependencies: form, user
    
    Complications:
    
    - references to OLD Entities within certain text fields.  Such
      references will need to be replaced using regex replace since the IDs of
      the entities will be changed on import...
    
    - forms can have speaker initials instead of speaker ...
    
    - many-to-many associations (e.g., keywords, form-file associations): should
      these only be available as formKeyword/formFile entities or should OLD XML
      allow, e.g., form elements to have multiple keyword/file children?...  The
      latter seems to needlessly complicate things...

    - max length on certain fields and how to deal with spillover...
    
    - duplication of entries

    - orthography conversion

    1. import
    
    """

    OLDEntitiesSchema = {
        'applicationSettings': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'collection': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'collectionBackup': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'collectionFile': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'collectionForm': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'elicitationMethod': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'file': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'form': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'fo': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'formBackup': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'formFile': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'formKeyword': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'gloss': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'keyword': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'language': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'page': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'source': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'speaker': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'syntacticCategory': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'user': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ),
        'userForm': (
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        )
    }

    # These OLD entities are 'independent' insofar as they never contain
    #  references to other entities
    independentOLDEntityNames = [
        'elicitationMethod',
        'keyword',
        'page',
        'source',
        'speaker',
        'syntacticCategory',
        'user'
    ]

    root = {}
    
    # Get all the children of the oldentities element
    for name in OLDEntitiesSchema:
        root[name] = OLDXMLFile_doc.findall(name)

    # Get OLD core entities, i.e., Form, File and Collection
    OLDCoreEntities = root['file'] + root['form'] + root['fo'] + \
        root['collection']
    
    # Get all the independent OLD entities
    for name in independentOLDEntityNames:
        root[name] += [x.find(name) for x in OLDCoreEntities if x.find(name)]
    
    return root

class ImportController(BaseController):

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def index(self):
        redirect(url(controller='import', action='upload'))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def upload(self):
        """This method renders the page for uploading an OLD XML file.
        
        """
        
        return render('/derived/import/upload.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def process(self):
        """Process the OLD XML file to be imported.
        
        Processing involves:
        
        - saving the file
        - validating against oldxmlschema.rng
        - ...
        
        """

        schema = NewUploadForm()
        values = dict(request.params)

        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            html = render('/derived/import/upload.html')
            errors=variabledecode.variable_encode(
                e.unpack_errors() or {},
                add_repetitions=False
            )
            return htmlfill.render(html, defaults=values, errors=errors)
        else:
            # Make sure that the file type is allowed for upload
            #  and return the form if this is not the case
            if request.POST['fileData'] == '':
                html = render('/derived/import/upload.html')
                errors={'fileData': 'please enter a file to upload'}
                return htmlfill.render(html, defaults=values, errors=errors)

            fileData = request.POST['fileData']
            fileType = guess_type(fileData.filename)[0]

            if fileType != u'application/xml':
                html = render('/derived/import/upload.html')
                errors={'fileData': 'only XML files (with extension .xml) \
                    are permitted'}
                return htmlfill.render(html, defaults=values, errors=errors)

            # All is good: save the file to temporary_store
            #  (see development.ini)
            fileName = fileData.filename.replace(os.sep, '_').replace(
                "'", "").replace('"', '').replace(' ', '_')
            filePathName = os.path.join(
                config['app_conf']['temporary_store'],
                fileName
            )

            # Create the temporary file, copy the file data to it and close
            temporary_file = open(
                filePathName,
                'wb'
            )
            shutil.copyfileobj(fileData.file, temporary_file)
            fileData.file.close()
            temporary_file.close()

            # Validate the OLD XML file against the Relax NG schema
            #  oldxmlschema.rng

            RelaxNGFileName = u'onlinelinguisticdatabase/public/oldxmlschema.rng'
            RelaxNGFile = codecs.open(
                RelaxNGFileName, mode='r', encoding='utf-8')
            RelaxNG_doc = etree.parse(RelaxNGFile)
            RelaxNG = etree.RelaxNG(RelaxNG_doc)

            OLDXMLFile = codecs.open(filePathName, mode='r', encoding='utf-8')
            OLDXMLFile_doc = etree.parse(OLDXMLFile)

            try:
                result = RelaxNG.assert_(OLDXMLFile_doc)
            except AssertionError, e:
                html = render('/derived/import/upload.html')
                errorMessage = 'Sorry, the file you have uploaded is not a \
                    valid OLD XML document.  Error message: %s.' % e
                errors={'fileData': errorMessage}
                return htmlfill.render(html, defaults=values, errors=errors)

            else:
                result = "Yay, this is good oldxml!!!  Now we must parse it"
                OLDEntities = importOLDXML(OLDXMLFile_doc)
                for k in OLDEntities:
                    result += '<p>%s</p>' % k
                    result += '<ol><li>'
                    result += '</li><li>'.join([x.tag for x in OLDEntities[k]])
                    result += '</li></ol>'
            return result