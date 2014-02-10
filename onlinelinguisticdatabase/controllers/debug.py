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
import datetime
import os
import re
from docutils import core

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators import validate
from pylons.decorators.rest import restrict

import webhelpers.paginate as paginate

from pylons import config
from formencode.schema import Schema
from formencode.validators import Invalid, FancyValidator
from formencode.validators import Int, DateConverter, UnicodeString, OneOf, \
    Regex
from formencode import variabledecode
from formencode import htmlfill, All
from formencode.foreach import ForEach
from formencode.api import NoDefault

from sqlalchemy.sql import or_

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from sqlalchemy import desc

log = logging.getLogger(__name__)


class DebugController(BaseController):

    @h.authenticate
    @h.authorize(['administrator'])
    def index(self):
        c.stuff = config['app_conf']
        return render('/derived/debug/index.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def cfg(self):
        c.config = config
        return render('/derived/debug/cfg.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def root(self):
        c.root = app_globals.pylons_config.paths
        return render('/derived/debug/root.html')