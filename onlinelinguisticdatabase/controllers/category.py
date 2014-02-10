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
        categories = meta.Session.query(model.SyntacticCategory).all()
        if value in [category.name for category in categories]:
            raise Invalid(self.message("repeated_name", state), value, state)

class NewCategoryForm(Schema):
    """NewCategoryForm is a Schema for validating the 
    data entered at the Add Category page."""
    allow_extra_fields = True
    filter_extra_fields = True
    name = formencode.All(UniqueName(), PlainText(not_empty=True))
    description = UnicodeString()

class UpdateCategoryForm(NewCategoryForm):
    """Schema class that inherits from NewCategoryForm
    and adds an ID and removes the uniqueness reqirement on the name.
    This really sould be changed but I DON'T KNOW HOW TO MAKE FORMENCODE
    ENSURE THAT A VALUE IS UNIQUE AGAINST A SET OF VALUES IN THE DB BUT
    STILL POSSIBLY EQUAL TO THE VALUE OF THE ID THAT IS BEING EDITED..."""
    ID = UnicodeString()
    name = PlainText(not_empty=True)

class CategoryController(BaseController):
    
    def view(self, id):
        """View an OLD Syntactic Category.  Requires a Category ID as input."""
        if id is None:
            redirect(url(controller='tag', action='index'))
        category_q = meta.Session.query(model.SyntacticCategory)
        c.category = category_q.get(int(id))
        if c.category is None:
            abort(404)
        return render('/derived/tag/category/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Add a new OLD Syntactic Category.  This action renders the html form 
        for adding a new Category."""
        return render('/derived/tag/category/add.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')    
    @validate(schema=NewCategoryForm(), form='add')
    def create(self):
        """Insert new Category data into database.

        """

        category = model.SyntacticCategory()
        category.name = h.NFD(self.form_result['name'])
        category.description = h.NFD(self.form_result['description'])
        # Enter the data
        meta.Session.add(category)
        meta.Session.commit()
        # Update the syncats variable in app_globals
        tags = h.getSecondaryObjects(['syncats'])
        app_globals.syncats = tags['syncats']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='category', action='view', id=category.id)
        return "Moved temporarily"           

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def edit(self, id):
        """Edit an OLD Category."""
        if id is None:
            abort(404)
        category_q = meta.Session.query(model.SyntacticCategory)
        c.category = category_q.get(int(id))
        if c.category is None:
            abort(404)
        html = render('/derived/tag/category/edit.html')
        values = {
            'ID': c.category.id,
            'name': c.category.name,
            'description': c.category.description
        }
        return htmlfill.render(html, values)
        #return htmlfill.render(html, defaults=values, errors=errors)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')    
    @validate(schema=UpdateCategoryForm(), form='edit')
    def save(self):
        """Update OLD Category with newly altered data."""
        # Check whether the user is updating a category to have a
        #  name that is the same as another category and redisplay
        #  the form with an error message if so.  This should be
        #  done by the Schema, but I couldn't figure out how.
        otherCategoriesWithSameName = meta.Session.query(model.SyntacticCategory).filter(model.SyntacticCategory.id!=self.form_result['ID']).filter(model.SyntacticCategory.name==self.form_result['name']).all()
        if otherCategoriesWithSameName:
            c.category = meta.Session.query(model.SyntacticCategory).get(int(self.form_result['ID']))
            html = render('/derived/tag/category/edit.html')
            errors = {'name': 'Sorry, that name is already taken'}
            values = {
                'ID': self.form_result['ID'],
                'name': self.form_result['name'],
                'description': self.form_result['description']
            }
            return htmlfill.render(html, defaults=values, errors=errors)
        category_q = meta.Session.query(model.SyntacticCategory)
        category = category_q.get(int(self.form_result['ID']))        
        category.name = h.NFD(self.form_result['name'])
        category.description = h.NFD(self.form_result['description'])
        # Update the data
        meta.Session.commit()
        # Update the syncats variable in app_globals
        tags = h.getSecondaryObjects(['syncats'])
        app_globals.syncats = tags['syncats']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='category', action='view', id=category.id)
        return "Moved temporarily"

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD Category with ID=id."""
        if id is None:
            abort(404)
        category_q = meta.Session.query(model.SyntacticCategory)
        category = category_q.get(int(id))
        if category is None:
            abort(404)
        meta.Session.delete(category)
        meta.Session.commit()
        # Update the syncats variable in app_globals
        tags = h.getSecondaryObjects(['syncats'])
        app_globals.syncats = tags['syncats']
        session['flash'] = "Syntactic Category %s has been deleted" % id
        session.save()
        redirect(url(controller='tag', action='index'))
