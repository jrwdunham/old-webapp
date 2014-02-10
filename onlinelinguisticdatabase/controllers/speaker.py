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
from formencode.validators import UnicodeString
from formencode import htmlfill

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from onlinelinguisticdatabase.lib.oldMarkup import linkToOLDEntitites, embedFiles, embedForms

log = logging.getLogger(__name__)

class NewSpeakerForm(Schema):
    """NewSpeakerForm is a Schema for validating the 
    data entered at the Add Speaker page."""
    allow_extra_fields = True
    filter_extra_fields = True
    firstName = UnicodeString(not_empty=True)
    lastName = UnicodeString(not_empty=True)
    dialect = UnicodeString()
    speakerPageContent = UnicodeString()

class UpdateSpeakerForm(NewSpeakerForm):
    """Schema class that inherits from NewSpeakerForm
    and adds an ID key."""
    ID = UnicodeString()

class SpeakerController(BaseController):

    def view(self, id):
        """View an OLD Speaker.  Requires a Speaker ID as input."""
        
        if id is None:
            abort(404)
        speaker_q = meta.Session.query(model.Speaker)
        c.speaker = speaker_q.get(int(id))
        if c.speaker is None:
            abort(404)
        c.speakerPageContent = h.rst2html(c.speaker.speakerPageContent)
        
        # Convert OLD Markup references to links/representations
        c.speakerPageContent = linkToOLDEntitites(c.speakerPageContent)
        c.speakerPageContent = embedFiles(c.speakerPageContent)
        c.speakerPageContent = embedForms(c.speakerPageContent)
        
        return render('/derived/people/speaker/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Add a new OLD Speaker.  This action renders the html form 
        for adding a new speaker."""
        return render('/derived/people/speaker/add.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    @validate(schema=NewSpeakerForm(), form='add')
    def create(self):
        """Insert new Speaker data into database."""
        speaker = model.Speaker()
        speaker.firstName = h.NFD(self.form_result['firstName'])
        speaker.lastName = h.NFD(self.form_result['lastName'])
        speaker.dialect = h.NFD(self.form_result['dialect'])
        speaker.speakerPageContent = h.NFD(self.form_result['speakerPageContent'])
        # Enter the data
        meta.Session.add(speaker)
        meta.Session.commit()
        # Update the speaker variable in app_globals
        tags = h.getSecondaryObjects(['speakers'])
        app_globals.speakers = tags['speakers']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='speaker', action='view', id=speaker.id)
        return "Moved temporarily"           

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def edit(self, id):
        """Edit an OLD Speaker."""
        if id is None:
            abort(404)
        speaker_q = meta.Session.query(model.Speaker)
        c.speaker = speaker_q.get(int(id))
        if c.speaker is None:
            abort(404)
        html = render('/derived/people/speaker/edit.html')
        values = {
            'ID': c.speaker.id,
            'firstName': c.speaker.firstName,
            'lastName': c.speaker.lastName,
            'dialect': c.speaker.dialect,
            'speakerPageContent': c.speaker.speakerPageContent,
        }
        return htmlfill.render(html, values)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')    
    @validate(schema=UpdateSpeakerForm(), form='edit')
    def save(self):
        """Update OLD Speaker with newly altered data."""
        speaker_q = meta.Session.query(model.Speaker)
        speaker = speaker_q.get(int(self.form_result['ID']))        
        speaker.firstName = h.NFD(self.form_result['firstName'])
        speaker.lastName = h.NFD(self.form_result['lastName'])
        speaker.dialect = h.NFD(self.form_result['dialect'])
        speaker.speakerPageContent = h.NFD(self.form_result['speakerPageContent'])
        # Update the data
        meta.Session.commit()
        # Update the speaker variable in app_globals
        tags = h.getSecondaryObjects(['speakers'])
        app_globals.speakers = tags['speakers']
        # Issue an HTTP redirect
        response.status_int = 302
        response.headers['location'] = url(controller='speaker', action='view', id=speaker.id)
        return "Moved temporarily"    

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])    
    def delete(self, id):
        """Delete the BLD Speaker with ID=id."""
        if id is None:
            abort(404)
        speaker_q = meta.Session.query(model.Speaker)
        speaker = speaker_q.get(int(id))
        if speaker is None:
            abort(404)
        meta.Session.delete(speaker)
        meta.Session.commit()
        # Update the speaker variable in app_globals
        tags = h.getSecondaryObjects(['speakers'])
        app_globals.speakers = tags['speakers']
        session['flash'] = "Speaker %s has been deleted" % id
        session.save()
        redirect(url(controller='people'))

