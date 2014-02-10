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
import datetime
import os
import re
import codecs
from docutils import core

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators import validate
from pylons.decorators.rest import restrict
from pylons import config

from formencode.schema import Schema
from formencode.validators import Invalid, FancyValidator
from formencode.validators import Int, DateConverter, UnicodeString, OneOf, \
    Regex
from formencode import variabledecode
from formencode import htmlfill, All
from formencode.foreach import ForEach
from formencode.api import NoDefault

from sqlalchemy.sql import or_

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h
from onlinelinguisticdatabase.lib.exporter import exporters

log = logging.getLogger(__name__)

class ExportController(BaseController):

    def index(self):
        
        redirect(url(controller='home', action='index'))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def options(self, id):
        """Display the export options available given the input.  Here the id
        variable is the input.  The id variable must be one of the following:
        
        1. 'memory'
        2. 'lastsearch'
        3. 'formx' (where 'x' is a digit representing a Form ID)
        4. 'collectionformsx' (where 'x' represents a Collection ID)
        5. 'collectioncontentx' (where 'x' represents a Collection ID)
        
        Export options come from the Exporter objects defined in the
        lib/exporter module.
        
        """
        
        c.goodExporters = [(exporters.index(x), id, x) for x in exporters \
            if x.input_types(id)]
        return render('/derived/export/options.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def create(self, input, option):
        """Create the export file in file/researcher.username"""
        
        # Get the appropriate exporter instance via the option variable
        exporterIndex = int(option[6:])
        exporter = exporters[exporterIndex]
        
        # Create the export string
        exportString = exporter.export(input)
        
        # Create the export file (simultaneously overwriting this user's
        #  previous export file)
        c.filename = '%s.%s' % (session['user_username'], exporter.extension)
        filePath = os.path.join(
            config['app_conf']['permanent_store'],
            'researchers',
            session['user_username'],
            c.filename
        )
        file = codecs.open(filePath, encoding='utf-8', mode='w')
        file.write(exportString)

        c.fileRetrieveName = os.path.join(
            'researchers', session['user_username'], c.filename)
        return render('/derived/export/create.html')
