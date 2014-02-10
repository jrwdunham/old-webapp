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

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate

from formencode.schema import Schema
from formencode.validators import UnicodeString, Int, Regex
from formencode import htmlfill
import formencode

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from sqlalchemy.sql import desc

import hashlib

log = logging.getLogger(__name__)

class NewSourceForm(Schema):
    """NewSourceForm is a Schema for validating the 
    data entered at the Add Source page."""
    allow_extra_fields = True
    filter_extra_fields = True
    authorFirstName = UnicodeString(not_empty=True)
    authorLastName = UnicodeString(not_empty=True)
    title = UnicodeString(not_empty=True)
    year = Regex('[0-9]{4}', not_empty=True)
    fullReference = UnicodeString()
    file_id = Regex('[0-9]+')

class UpdateSourceForm(NewSourceForm):
    """Schema class that inherits from NewSourceForm
    and adds an ID and modifies the password validator."""
    ID = UnicodeString()

class SourceController(BaseController):
    
    def index(self):
        """View all Sources."""
        c.sources = meta.Session.query(model.Source).order_by(
            model.Source.authorLastName).order_by(
            model.Source.authorFirstName).order_by(desc(model.Source.year)).all()
        return render('/derived/source/index.html')

    def view(self, id):
        """View an OLD Source.  Requires a Source ID as input."""
        if id is None:
            abort(404)
        source_q = meta.Session.query(model.Source)
        c.source = source_q.get(int(id))
        if c.source is None:
            abort(404)
        return render('/derived/source/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Add a new OLD Source.  This action renders the html form 
        for adding a new Source."""
        return render('/derived/source/add.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    @validate(schema=NewSourceForm(), form='add')
    def create(self):
        """Insert new Source data into database."""
        source = model.Source()
        source.authorFirstName = h.NFD(self.form_result['authorFirstName'])
        source.authorLastName = h.NFD(self.form_result['authorLastName'])
        source.title = h.NFD(self.form_result['title'])
        source.year = self.form_result['year']
        source.fullReference = h.NFD(self.form_result['fullReference'])
        fileID = self.form_result['file_id']
        if fileID:
            file = meta.Session.query(model.File).get(int(fileID))
            if file:
                source.file = file
            else:
                html = render('/derived/source/add.html')
                values = self.form_result
                errors = {'file_id': 'There is no file with ID %s' % fileID}
                return htmlfill.render(html, defaults=values, errors=errors)
        # Enter the data
        meta.Session.add(source)
        meta.Session.commit()
        # Update the users variable in app_globals
        tags = h.getSecondaryObjects(['sources'])
        app_globals.sources = tags['sources']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='source', action='view', id=source.id)
        return "Moved temporarily"           

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def edit(self, id):
        """Edit an OLD Source."""
        if id is None:
            abort(404)
        source_q = meta.Session.query(model.Source)
        c.source = source_q.get(int(id))
        if c.source is None:
            abort(404)
        html = render('/derived/source/edit.html')
        values = {
            'ID': c.source.id,
            'authorFirstName': c.source.authorFirstName,
            'authorLastName': c.source.authorLastName,
            'title': c.source.title,
            'year': c.source.year,
            'fullReference': c.source.fullReference,
            'file_id': c.source.file_id
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    @validate(schema=UpdateSourceForm(), form='edit')
    def save(self):
        """Update OLD Source with newly altered data."""
        source_q = meta.Session.query(model.Source)
        source = source_q.get(int(self.form_result['ID']))
        c.source = source        
        source.authorFirstName = h.NFD(self.form_result['authorFirstName'])
        source.authorLastName = h.NFD(self.form_result['authorLastName'])
        source.title = h.NFD(self.form_result['title'])
        source.year = self.form_result['year']
        source.fullReference = h.NFD(self.form_result['fullReference'])
        fileID = self.form_result['file_id']
        if fileID:
            file = meta.Session.query(model.File).get(int(fileID))
            if file:
                source.file = file
            else:
                html = render('/derived/source/edit.html')
                values = self.form_result
                errors = {'file_id': 'There is no file with ID %s' % fileID}
                return htmlfill.render(html, defaults=values, errors=errors)
        else:
            source.file = None
        # Update the data
        meta.Session.commit()
        # Update the users variable in app_globals
        tags = h.getSecondaryObjects(['sources'])
        app_globals.sources = tags['sources']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='source', action='view', id=source.id)
        return "Moved temporarily"    

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD Source with ID=id."""
        if id is None:
            abort(404)
        source_q = meta.Session.query(model.Source)
        source = source_q.get(int(id))
        if source is None:
            abort(404)
        meta.Session.delete(source)
        meta.Session.commit()
        # Update the users variable in app_globals
        tags = h.getSecondaryObjects(['sources'])
        app_globals.sources = tags['sources']
        session['flash'] = "Source %s has been deleted" % id
        session.save()
        redirect(url(controller='source'))
