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
import hashlib

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate

from formencode.schema import Schema
from formencode.validators import UnicodeString, Email, Invalid, FancyValidator, PlainText, OneOf, StringBoolean
from formencode import htmlfill
import formencode

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from onlinelinguisticdatabase.lib.oldMarkup import linkToOLDEntitites, embedFiles, embedForms

import urllib

try:
    import json
except ImportError:
    import simplejson as json

log = logging.getLogger(__name__)

class UniqueUsername(FancyValidator):
    """Custom validator.  Ensures that the username is unique
    
    """

    messages = {
        'repeated_username': 'Sorry, that username is already taken'
    }

    def validate_python(self, value, state):
        users = meta.Session.query(model.User).all()
        if value in [user.username for user in users]:
            raise Invalid(self.message("repeated_username", state), value, state)


class NewResearcherForm(Schema):
    """NewResearcherForm is a Schema for validating the 
    data entered at the Add Researcher page.
    
    """
    
    allow_extra_fields = True
    filter_extra_fields = True
    username = formencode.All(UniqueUsername(), PlainText(not_empty=True))
    password = PlainText(not_empty=True)
    firstName = UnicodeString(not_empty=True)
    lastName = UnicodeString(not_empty=True)
    email = Email(not_empty=True)
    affiliation = UnicodeString()
    role = OneOf(app_globals.roles)
    personalPageContent = UnicodeString()


class UpdateResearcherForm(NewResearcherForm):
    """Schema class that inherits from NewResearcherForm and adds an ID and
    modifies the password validator.
    
    """

    ID = UnicodeString()
    username = PlainText()
    password = PlainText()


class SaveSettingsForm(Schema):
    """SaveSettingsForm is a Schema for validating changes to a User's settings.
    
    """
    
    allow_extra_fields = True
    filter_extra_fields = True
    #collectionViewType = OneOf(app_globals.collectionViewTypes)
    defaultMetadataFromPreviousForm = StringBoolean()
    guessMorphology = StringBoolean()
    inputOrthography = UnicodeString()
    outputOrthography = UnicodeString()
    defaultFormView = UnicodeString()
    dateFormat = UnicodeString()


def getResearcherAttributes(researcher, result, createOrSave):
    researcher.username = h.NFD(result['username'])
    researcher.firstName = h.NFD(result['firstName'])
    researcher.lastName = h.NFD(result['lastName'])
    researcher.email = result['email']
    researcher.affiliation = h.NFD(result['affiliation'])
    researcher.personalPageContent = h.NFD(result['personalPageContent'])
    researcher.role = result['role']

    # Only update the password if something was added
    if result['password']:
        researcher.password = hashlib.sha224(result['password']).hexdigest()


class ResearcherController(BaseController):

    @h.authenticate
    def view(self, id):
        """View an OLD Researcher.  Requires a Researcher ID as input.
        
        """
        
        if id is None:
            abort(404)

        researcher_q = meta.Session.query(model.User)
        c.researcher = researcher_q.get(int(id))

        if c.researcher is None:
            abort(404)

        c.personalPageContent = h.rst2html(c.researcher.personalPageContent)

        # Convert OLD Markup references to links/representations
        if c.personalPageContent:
            c.personalPageContent = linkToOLDEntitites(c.personalPageContent)
            c.personalPageContent = embedFiles(c.personalPageContent)
            c.personalPageContent = embedForms(c.personalPageContent)

        return render('/derived/people/researcher/view.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def add(self):
        """Add a new OLD Researcher.  This action renders the html form 
        for adding a new Researcher.  This form calls the create action.
        
        """
        
        return render('/derived/people/researcher/add.html')

    @h.authenticate
    @h.authorize(['administrator'])
    @restrict('POST')
    @validate(schema=NewResearcherForm(), form='add')
    def create(self):
        """Insert new Researcher data into database.
        
        """
        
        researcher = model.User()
        getResearcherAttributes(researcher, self.form_result, 'create')

        # Create a directory in files directory for this researcher
        h.createResearcherDirectory(researcher)

        # Enter the data
        meta.Session.add(researcher)
        meta.Session.commit()
        # Update the users variable in app_globals
        tags = h.getSecondaryObjects(['users'])
        app_globals.users = tags['users']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(
            controller='researcher', action='view', id=researcher.id)
        return "Moved temporarily"

    @h.authenticate
    @h.authorize(['administrator', 'contributor', 'viewer'], userIDIsArgs1=True)
    def edit(self, id):
        """Edit an OLD Researcher.  A non-administrator can only edit their own
        information; hence the userIDIsArgs1=True argument in the authorize
        validator.
        
        """
        
        if id is None:
            abort(404)
        researcher_q = meta.Session.query(model.User)
        c.researcher = researcher_q.get(int(id))
        if c.researcher is None:
            abort(404)
        html = render('/derived/people/researcher/edit.html')
        values = {
            'ID': c.researcher.id,
            'username': c.researcher.username,
            'firstName': c.researcher.firstName,
            'lastName': c.researcher.lastName,
            'email': c.researcher.email,
            'affiliation': c.researcher.affiliation,
            'personalPageContent': c.researcher.personalPageContent,
            'role': c.researcher.role
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @restrict('POST')
    @validate(schema=UpdateResearcherForm(), form='edit')
    def save(self):
        """Update OLD Researcher with newly altered data.
        
        """
        
        researcher_q = meta.Session.query(model.User)
        researcher = researcher_q.get(int(self.form_result['ID']))
        getResearcherAttributes(researcher, self.form_result, 'save')
        # Update the data
        meta.Session.commit()
        # Update the users variable in app_globals
        tags = h.getSecondaryObjects(['users'])
        app_globals.users = tags['users']
        # update the session if we have just updated the current user
        if researcher.id == session['user_id']:
            h.getAuthorizedUserIntoSession(researcher)
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(
            controller='researcher', action='view', id=researcher.id)
        return "Moved temporarily"

    @h.authenticate
    @h.authorize(['administrator'])
    def delete(self, id):
        """Delete the BLD Researcher with ID=id.
        
        """
        
        if id is None:
            abort(404)
        researcher_q = meta.Session.query(model.User)
        researcher = researcher_q.get(int(id))
        if researcher is None:
            abort(404)
        meta.Session.delete(researcher)
        meta.Session.commit()
        
        # Destroy the researcher's directory in the files directory
        h.destroyResearcherDirectory(researcher)

        # Update the users variable in app_globals
        tags = h.getSecondaryObjects(['users'])
        app_globals.users = tags['users']
        session['flash'] = "Researcher %s has been deleted" % id
        session.save()
        redirect(url(controller='people'))

    @h.authenticate
    @h.authorize(['administrator', 'contributor', 'viewer'], userIDIsArgs1=True)
    def settings(self, id):
        """View the logged in researcher's settings.
        
        """
        
        if id is None: 
            abort(404)

        researcher_q = meta.Session.query(model.User)
        c.researcher = researcher_q.get(int(id))
        if c.researcher is None:
            abort(404)

        # Get the researcher's settings from the pickle file in
        #  files/researchers/username/username.pickle
        c.researcherSettings = h.unpickleResearcherSettings(c.researcher)
        
        return render('/derived/people/researcher/settings.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor', 'viewer'], userIDIsArgs1=True)
    def editsettings(self, id):
        """Edit the logged in researcher's settings.
        
        """
        
        if id is None: 
            abort(404)

        researcher_q = meta.Session.query(model.User)
        c.researcher = researcher_q.get(int(id))
        if c.researcher is None:
            abort(404)

        # Get the researcher's settings from the pickle file in
        #  files/researchers/username/username.pickle
        c.researcherSettings = h.unpickleResearcherSettings(c.researcher)

        values = {
            'inputOrthography': c.researcherSettings.get('inputOrthography'),
            'outputOrthography': c.researcherSettings.get('outputOrthography'),
            'defaultMetadataFromPreviousForm': c.researcherSettings.get(
                'defaultMetadataFromPreviousForm'),
            'defaultFormView': c.researcherSettings.get('defaultFormView'),
            'guessMorphology': c.researcherSettings.get('guessMorphology'),
            'dateFormat': c.researcherSettings.get('dateFormat')
        }

        html = render('/derived/people/researcher/editsettings.html')

        return htmlfill.render(html, defaults=values)


    @h.authenticate
    @restrict('POST')
    @validate(schema=SaveSettingsForm(), form='editsettings')
    def savesettings(self, id):
        """Save the newly changed user-specific settings.
        
        """

        if id is None: 
            abort(404)

        researcher_q = meta.Session.query(model.User)
        c.researcher = researcher_q.get(int(id))
        if c.researcher is None:
            abort(404)

        # Save settings in the researcher's settings pickle
        researcherSettings = {
            'inputOrthography': self.form_result['inputOrthography'],
            'outputOrthography': self.form_result['outputOrthography'],
            'defaultMetadataFromPreviousForm': self.form_result[
                'defaultMetadataFromPreviousForm'],
            'defaultFormView': self.form_result['defaultFormView'],
            'guessMorphology': self.form_result['guessMorphology'],
            'dateFormat': self.form_result['dateFormat']
        }
        h.pickleResearcherSettings(researcherSettings, c.researcher)

        session['userSettings'] = researcherSettings
        # Save settings in session
        session['user_inputOrthography'] = researcherSettings[
            'inputOrthography']
        session['user_outputOrthography'] = researcherSettings[
            'outputOrthography']
        session['user_defaultMetadataFromPreviousForm'] = researcherSettings[
            'defaultMetadataFromPreviousForm']
        session['defaultFormView'] = researcherSettings['defaultFormView']
        session['guessMorphology'] = researcherSettings['guessMorphology']
        session['dateFormat'] = researcherSettings['dateFormat']

        # Put the appropriate translators in the session.
        #  That is, if the user has chosen an output orthography that is
        #  different from the storage orthography AND is different from the
        #  default output orthography, create a new translator in the session.
        #  Ditto for the input-to-storage translator.
        h.putOrthographyTranslatorsIntoSession()

        session.save()

        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='researcher', \
                                        action='settings', id=c.researcher.id)
        return "Moved temporarily"

    @h.authenticate
    @restrict('POST')
    def saveuserdisplaysetting(self):
        """Asynchronously saves the user's form add display settings, i.e.,
        whether the narrow or broad phonetic transcription fields will be
        displayed or not.  See the saveUserDisplaySetting JS function in
        functions.js.
        
        """

        value = {'true': True, 'false': False}[request.params['value']]
        setting = request.params['setting']
        researcher = meta.Session.query(model.User).get(session['user_id'])
        researcherSettings = h.unpickleResearcherSettings(researcher)
        researcherSettings[setting] = value
        h.pickleResearcherSettings(researcherSettings, researcher)
        session['userSettings'] = researcherSettings
        session.save()