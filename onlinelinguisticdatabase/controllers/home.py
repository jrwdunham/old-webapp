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

try:
    import json
except ImportError:
    import simplejson as json

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from formencode.schema import Schema
from formencode import htmlfill
from formencode.validators import Int, OneOf, UnicodeString

from onlinelinguisticdatabase.lib.oldMarkup import linkToOLDEntitites, embedFiles, embedForms

log = logging.getLogger(__name__)

class UpdateHomePageForm(Schema):
    """NewPageForm is a Schema for validating the 
    data entered at the Edit Home Page page."""
    allow_extra_fields = True
    filter_extra_fields = True
    name = UnicodeString()
    heading = UnicodeString()
    content = UnicodeString()
    ID = Int()

class HomeController(BaseController):

    def index(self):
        """Display the OLD Application home page.  This page is generated from
        the entry with name='home' of the table page_table of the model.  This
        page can be edited by administrators.
        
        """
        
        # Get the number of Forms in the db
        c.formCount = str(h.getFormCount())
        
        # Get the homepage from the model
        homepage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'home')
        homepage = homepage_q.first()

        try:
            c.heading = homepage.heading
            c.content = homepage.content
        except AttributeError:
            c.heading = u'There is no heading'
            c.content = u'There is no content for this page'

        # Convert reStructuredText to HTML
        c.content = h.rst2html(c.content)
        
        # Convert OLD Markup references to links/representations
        c.content = linkToOLDEntitites(c.content)
        c.content = embedFiles(c.content)
        c.content = embedForms(c.content)
        
        return render('/derived/home/index.html')

    def index_ajax(self):
        """Display the OLD Application home page.  This page is generated from
        the entry with name='home' of the table page_table of the model.  This
        page can be edited by administrators.

        """

        response.headers['Content-Type'] = 'application/json'
        result = {}

        # Get the number of Forms in the db
        result['formCount'] = str(h.getFormCount())

        # Get the homepage from the model
        homepage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'home')
        homepage = homepage_q.first()

        try:
            result['headerText'] = homepage.heading
            result['bodyContent'] = homepage.content
        except AttributeError:
            result['heading'] = u'There is no heading'
            result['content'] = u'There is no content for this page'

        # Perform a series of transformations on the page body content:
        #  1. convert reStructuredText to HTML, 2. link to OLD entities,
        #  3. embed Files and 4. Forms (LAST 3 SHOULD BE DONE CLIENT-SIDE)
        # Convert OLD Markup references to links/representations
        result['bodyContent'] = embedForms(
                                embedFiles(
                                linkToOLDEntitites(
                                h.rst2html(result['bodyContent']))))

        return json.dumps(result)

    #@h.authenticate_ajax
    @restrict('POST')
    def get_secondary_objects_ajax(self):
        """Return the secondary OLD objects, i.e., source, user,
        syntacticCategory, elicitationMethod, speaker, grammaticality, as JSON
        objects.

        Accepts optional parameters in the POST header indicating the age of the
        data stored client-side, i.e., """
        pass


    def add_ajax(self):
        #time.sleep(5)
        schema = NewFormAjaxForm()
        values = variabledecode.variable_decode(request.params)

    @h.authenticate
    @h.authorize(['administrator'])
    def edit(self):
        """The edit action displays the HTML form for editing the OLD
        Application's home page.
        """
        # Get the homepage from the model
        homepage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'home')
        homepage = homepage_q.first()
        if homepage is None:
            abort(404)
            
        html = render('/derived/home/edit.html')
        values = {
            'ID': homepage.id,
            'name': homepage.name,
            'heading': homepage.heading,
            'content': homepage.content
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @h.authorize(['administrator'])
    @restrict('POST')
    @validate(schema=UpdateHomePageForm(), form='edit')
    def save(self):
        """Update OLD Home Page with newly altered data.
        
        """

        # Get the homepage from the model
        homepage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'home')
        homepage = homepage_q.first()
        if homepage is None:
            abort(404)
            
        homepage.name = h.NFD(self.form_result['name'])
        homepage.heading = h.NFD(self.form_result['heading'])
        homepage.content = h.NFD(self.form_result['content'])
        
        # Update the data
        meta.Session.commit()

        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='home', action='index')
        return "Moved temporarily"