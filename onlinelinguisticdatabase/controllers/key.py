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
from formencode.validators import UnicodeString, Email, Invalid, FancyValidator, PlainText, OneOf
from formencode import htmlfill
import formencode

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

import hashlib

log = logging.getLogger(__name__)

class UniqueName(FancyValidator):
    """
    Custom validator.  Ensures that the name is unique
    """
    messages = {
        'repeated_name': 'Sorry, that name is already taken'
    }
    def validate_python(self, value, state):
        keywords = meta.Session.query(model.Keyword).all()
        if value in [keyword.name for keyword in keywords]:
            raise Invalid(self.message("repeated_name", state), value, state)

class NewKeywordForm(Schema):
    """NewKeywordForm is a Schema for validating the 
    data entered at the Add Keyword page."""
    allow_extra_fields = True
    filter_extra_fields = True
    name = formencode.All(UniqueName(), UnicodeString(not_empty=True))
    description = UnicodeString()

class UpdateKeywordForm(NewKeywordForm):
    """Schema class that inherits from NewKeywordForm
    and adds an ID and removes the uniqueness reqirement on the name.
    This really sould be changed but I DON'T KNOW HOW TO MAKE FORMENCODE
    ENSURE THAT A VALUE IS UNIQUE AGAINST A SET OF VALUES IN THE DB BUT
    STILL POSSIBLY EQUAL TO THE VALUE OF THE ID THAT IS BEING EDITED..."""
    ID = UnicodeString()
    name = UnicodeString(not_empty=True)

class KeyController(BaseController):
    
    def view(self, id):
        """View an OLD Keyword.  Requires a Keyword ID as input."""
        if id is None:
            redirect(url(controller='tag', action='index'))
        keyword_q = meta.Session.query(model.Keyword)
        c.keyword = keyword_q.get(int(id))
        if c.keyword is None:
            abort(404)
        return render('/derived/tag/keyword/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Add a new OLD Keyword.  This action renders the html form 
        for adding a new Keyword."""
        return render('/derived/tag/keyword/add.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')    
    @validate(schema=NewKeywordForm(), form='add')
    def create(self):
        """Insert new Keyword data into database."""
        keyword = model.Keyword()
        keyword.name = h.NFD(self.form_result['name'])
        keyword.description = h.NFD(self.form_result['description'])
        # Enter the data
        meta.Session.add(keyword)
        meta.Session.commit()
        # Update the keywords variable in app_globals
        tags = h.getSecondaryObjects(['keywords'])
        app_globals.keywords = tags['keywords']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='key', action='view', id=keyword.id)
        return "Moved temporarily"           

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def edit(self, id):
        """Edit an OLD Keyword."""
        if id is None:
            abort(404)
        keyword_q = meta.Session.query(model.Keyword)
        c.keyword = keyword_q.get(int(id))
        if c.keyword is None:
            abort(404)
        html = render('/derived/tag/keyword/edit.html')
        values = {
            'ID': c.keyword.id,
            'name': c.keyword.name,
            'description': c.keyword.description
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    @validate(schema=UpdateKeywordForm(), form='edit')
    def save(self):
        """Update OLD Keyword with newly altered data."""
        # Check whether the user is updating a keyword to have a
        #  name that is the same as another keyword and redisplay
        #  the form with an error message if so.  This should be
        #  done by the Schema, but I couldn't figure out how.
        otherKeywordsWithSameName = meta.Session.query(model.Keyword).filter(model.Keyword.id!=self.form_result['ID']).filter(model.Keyword.name==self.form_result['name']).all()
        if otherKeywordsWithSameName:
            c.keyword = meta.Session.query(model.Keyword).get(int(self.form_result['ID']))
            html = render('/derived/tag/keyword/edit.html')
            errors = {'name': 'Sorry, that name is already taken'}
            values = {
                'ID': self.form_result['ID'],
                'name': self.form_result['name'],
                'description': self.form_result['description']
            }
            return htmlfill.render(html, defaults=values, errors=errors)
        keyword_q = meta.Session.query(model.Keyword)
        keyword = keyword_q.get(int(self.form_result['ID']))        
        keyword.name = h.NFD(self.form_result['name'])
        keyword.description = h.NFD(self.form_result['description'])
        # Update the data
        meta.Session.commit()
        # Update the keywords variable in app_globals
        tags = h.getSecondaryObjects(['keywords'])
        app_globals.keywords = tags['keywords']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='key', action='view', id=keyword.id)
        return "Moved temporarily"    

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD Keyword with ID=id."""
        if id is None:
            abort(404)
        keyword_q = meta.Session.query(model.Keyword)
        keyword = keyword_q.get(int(id))
        if keyword is None:
            abort(404)
        meta.Session.delete(keyword)
        meta.Session.commit()
        # Update the keywords variable in app_globals
        tags = h.getSecondaryObjects(['keywords'])
        app_globals.keywords = tags['keywords']
        session['flash'] = "Keyword %s has been deleted" % id
        session.save()
        redirect(url(controller='tag', action='index'))
