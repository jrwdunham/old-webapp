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
        elicitationMethods = meta.Session.query(model.ElicitationMethod).all()
        if value in [elicitationMethod.name for elicitationMethod in elicitationMethods]:
            raise Invalid(self.message("repeated_name", state), value, state)

class NewElicitationMethodForm(Schema):
    """NewElicitationMethodForm is a Schema for validating the 
    data entered at the Add ElicitationMethod page."""
    allow_extra_fields = True
    filter_extra_fields = True
    name = formencode.All(UniqueName(), UnicodeString(not_empty=True))
    description = UnicodeString()

class UpdateElicitationMethodForm(NewElicitationMethodForm):
    """Schema class that inherits from NewElicitationMethodForm
    and adds an ID and removes the uniqueness reqirement on the name.
    This really sould be changed but I DON'T KNOW HOW TO MAKE FORMENCODE
    ENSURE THAT A VALUE IS UNIQUE AGAINST A SET OF VALUES IN THE DB BUT
    STILL POSSIBLY EQUAL TO THE VALUE OF THE ID THAT IS BEING EDITED..."""
    ID = UnicodeString()
    name = UnicodeString(not_empty=True)

class MethodController(BaseController):
    
    def view(self, id):
        """View an OLD Elicitation Method.  Requires a ElicitationMethod ID as
        input.
        """
        if id is None:
            redirect(url(controller='tag', action='index'))
        elicitationMethod_q = meta.Session.query(model.ElicitationMethod)
        c.elicitationMethod = elicitationMethod_q.get(int(id))
        if c.elicitationMethod is None:
            abort(404)
        return render('/derived/tag/method/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Add a new OLD ElicitationMethod.  This action renders the html form 
        for adding a new ElicitationMethod."""
        return render('/derived/tag/method/add.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')    
    @validate(schema=NewElicitationMethodForm(), form='add')
    def create(self):
        """Insert new ElicitationMethod data into database."""
        elicitationMethod = model.ElicitationMethod()
        elicitationMethod.name = h.NFD(self.form_result['name'])
        elicitationMethod.description = h.NFD(self.form_result['description'])
        # Enter the data
        meta.Session.add(elicitationMethod)
        meta.Session.commit()
        # Update the syncats variable in app_globals
        tags = h.getSecondaryObjects(['elicitationMethods'])
        app_globals.elicitationMethods = tags['elicitationMethods']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='method', action='view', id=elicitationMethod.id)
        return "Moved temporarily"           

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def edit(self, id):
        """Edit an OLD ElicitationMethod."""
        if id is None:
            abort(404)
        elicitationMethod_q = meta.Session.query(model.ElicitationMethod)
        c.elicitationMethod = elicitationMethod_q.get(int(id))
        if c.elicitationMethod is None:
            abort(404)
        html = render('/derived/tag/method/edit.html')
        values = {
            'ID': c.elicitationMethod.id,
            'name': c.elicitationMethod.name,
            'description': c.elicitationMethod.description
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')    
    @validate(schema=UpdateElicitationMethodForm(), form='edit')
    def save(self):
        """Update OLD ElicitationMethod with newly altered data."""
        # Check whether the user is updating a method to have a
        #  name that is the same as another method and redisplay
        #  the form with an error message if so.  This should be
        #  done by the Schema, but I couldn't figure out how.
        otherMethodsWithSameName = meta.Session.query(model.ElicitationMethod).filter(model.ElicitationMethod.id!=self.form_result['ID']).filter(model.ElicitationMethod.name==self.form_result['name']).all()
        if otherMethodsWithSameName:
            c.elicitationMethod = meta.Session.query(model.ElicitationMethod).get(int(self.form_result['ID']))
            html = render('/derived/tag/method/edit.html')
            errors = {'name': 'Sorry, that name is already taken'}
            values = {
                'ID': self.form_result['ID'],
                'name': self.form_result['name'],
                'description': self.form_result['description']
            }
            return htmlfill.render(html, defaults=values, errors=errors)
        elicitationMethod_q = meta.Session.query(model.ElicitationMethod)
        elicitationMethod = elicitationMethod_q.get(int(self.form_result['ID']))        
        elicitationMethod.name = h.NFD(self.form_result['name'])
        elicitationMethod.description = h.NFD(self.form_result['description'])
        # Update the data
        meta.Session.commit()
        # Update the syncats variable in app_globals
        tags = h.getSecondaryObjects(['elicitationMethods'])
        app_globals.elicitationMethods = tags['elicitationMethods']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='method', action='view', id=elicitationMethod.id)
        return "Moved temporarily"    

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD ElicitationMethod with ID=id."""
        if id is None:
            abort(404)
        elicitationMethod_q = meta.Session.query(model.ElicitationMethod)
        elicitationMethod = elicitationMethod_q.get(int(id))
        if elicitationMethod is None:
            abort(404)
        meta.Session.delete(elicitationMethod)
        meta.Session.commit()
        # Update the syncats variable in app_globals
        tags = h.getSecondaryObjects(['elicitationMethods'])
        app_globals.elicitationMethods = tags['elicitationMethods']
        session['flash'] = "Elicitation Method %s has been deleted" % id
        session.save()
        redirect(url(controller='tag', action='index'))
