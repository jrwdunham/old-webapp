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

import codecs

import logging

from pylons import request, response, session, tmpl_context as c
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

log = logging.getLogger(__name__)

class UpdateHelpPageForm(Schema):
    """UpdateHelpPageForm is a Schema for validating the 
    data entered at the Edit Help Page page."""
    allow_extra_fields = True
    filter_extra_fields = True
    name = UnicodeString()
    heading = UnicodeString()
    content = UnicodeString()
    ID = Int()
    
def createUserGuideHTMLFile():
    """Function opens the reStructuredText file docs/user_guide.txt and uses
    docutils.core.publish_parts to generate an html file from it.  The html file
    is written to templates/derived/help
    
    """
    
    try:
        userGuideFile = codecs.open('./docs/user_guide.txt', encoding='utf-8')
        userGuideString= userGuideFile.read()
        userGuideHTML = h.rst2html(userGuideString)
    except IOError:
        userGuideHTML = ''
    
    try:
        userGuideAbsPath = os.path.join(
            config['pylons.paths']['root'],
            'templates',
            'derived',
            'help',
            'user_guide_body.html')
        outputFile = open(userGuideAbsPath, 'w')
        outputFile.write(userGuideHTML)
    except IOError:
        pass
    
class HelpController(BaseController):

    def index(self):
        """The index action redirects to olduserguide action."""
        response.status_int = 302
        response.headers['location'] = url(controller='help',
                                                 action='olduserguide')
        return "Moved temporarily"

    def olduserguide(self):
        """The olduserguide action displays the general-purpose OLD User Guide
        as generated from the user_guide.txt ReST file in the docs directory.
        
        """

        return render('/derived/help/oldUserGuide.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def ougr(self):
        """The ougr (OLD User Guide Refresh) action is a utility function that
        redirects to the olduserguide action but forces a regeneration of the
        <root>/templates/derived/help/user_guide_body.html
        file from the ./docs/user_guide.txt ReST file.  This action will only
        work in a development environment, i.e., where the cwd is the
        superdirectory of the onlinelinguisticdatabase directory.
        
        """
        createUserGuideHTMLFile()
        response.status_int = 302
        response.headers['location'] = url(controller='help',
                                                 action='olduserguide')
        return "Moved temporarily"

    def applicationhelp(self):
        """Display the OLD Application help page.  This page is generated from
        the entry with name='help' of the page table of the model.  This page
        can be edited by administrators.
        
        """
        
        # Get the helppage from the model
        helppage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'help')
        helppage = helppage_q.first()

        c.heading = helppage.heading

        # Get the help page content and translate it to HTML
        content = helppage.content
        content = h.literal(h.rst2html(content))

        c.content = content
        
        return render('/derived/help/help.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def edit(self):
        """The edit action displays the HTML form for editing the OLD
        Application's help page.
        
        """
        # Get the help page from the model
        helppage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'help')
        helppage = helppage_q.first()
        if helppage is None:
            abort(404)
            
        html = render('/derived/help/edit.html')
        values = {
            'ID': helppage.id,
            'name': helppage.name,
            'heading': helppage.heading,
            'content': helppage.content
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @h.authorize(['administrator'])
    @restrict('POST')
    @validate(schema=UpdateHelpPageForm(), form='edit')
    def save(self):
        """Update OLD Help Page with newly altered data.
        
        """

        # Get the help page from the model
        helppage_q = meta.Session.query(model.Page).filter(
            model.Page.name==u'help')
        helppage = helppage_q.first()
        if helppage is None:
            abort(404)
            
        helppage.name = h.NFD(self.form_result['name'])
        helppage.heading = h.NFD(self.form_result['heading'])
        helppage.content = h.NFD(self.form_result['content'])
        
        # Update the data
        meta.Session.commit()

        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='help', action='applicationhelp')
        return "Moved temporarily"