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

from pylons import request, response, session, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from sqlalchemy.sql import desc

log = logging.getLogger(__name__)

class MemoryController(BaseController):

    @h.authenticate
    def index(self):
        """Render the 'memory/index.html' page which displays
        the Forms that the user has stored in memory."""
        # Get all Forms that user has memorized ordered by Form ID 
        #  by using the 'memorizers' backreference
        user = meta.Session.query(model.User).filter(
            model.User.id==session['user_id']).first()
        c.rememberedForms = meta.Session.query(model.Form).order_by(desc(
            model.Form.id)).filter(model.Form.memorizers.contains(user)).all() 
        return render('/derived/memory/index.html')

    @h.authenticate
    def forget(self, id=None):
        """Remove 0 or more Forms from the User's Memory.

        If id is None, remove all Forms from Memory;
        otherwise, remove Form with provided id."""
        if id is None:
            user = meta.Session.query(model.User).filter(
                model.User.id==session['user_id']).first()
            user.rememberedForms = []
            meta.Session.commit()
            msg = u'All Forms in Memory have been removed.'
        else:
            form_q = meta.Session.query(model.Form)
            form = form_q.get(int(id))
            if form is None:
                msg = u'There is no Form with ID %s' % id
            else:
                user = meta.Session.query(model.User).filter(
                    model.User.id==session['user_id']).first()
                if form in user.rememberedForms:
                    user.rememberedForms.remove(form)
                    meta.Session.commit()
                    msg = u'Form %s has been removed from your memory' % id
                else:
                    msg = u'Form %s was never in your memory to begin with!' % id
        session['flash'] = msg
        session.save()
        redirect(url(controller='memory', action='index', id=None))


