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

from webhelpers.markdown import markdown

log = logging.getLogger(__name__)

class TagController(BaseController):

    def index(self):
        keyword_q = meta.Session.query(model.Keyword).order_by(
            model.Keyword.name)
        c.keywords = keyword_q.all()
        syncat_q = meta.Session.query(model.SyntacticCategory).order_by(
            model.SyntacticCategory.name)
        c.syncats = syncat_q.all()
        elicitationMethod_q = meta.Session.query(
            model.ElicitationMethod).order_by(model.ElicitationMethod.name)
        c.elicitationMethods = elicitationMethod_q.all()
        return render('/derived/tag/index.html')
