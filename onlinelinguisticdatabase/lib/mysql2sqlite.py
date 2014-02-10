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

import re

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons.controllers.util import abort, redirect

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h


def y():
    form_q = meta.Session.query(model.Form)
    return len(form_q.all())

"""
def x()
    # Get the SQLAlchemy Session
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Get a dict of the pages of the UBCWPL Web Site 
    ubcwpl = UBCWPLWebSite(session)
    ubcwpl.pages = ubcwpl.getAllUBCWPLWebSitePages()

    # Create the ubcwplHTML/YYYY-MM-DD_ubcwpl_web_site directory,
    #  overwriting an identically-named, preexisting directory.
    today = datetime.date.today()
    dirName = '%s_ubcwpl_web_site' % today
    dirName = os.path.join('ubcwplHTML', dirName)
    if os.path.isdir(dirName):
        shutil.rmtree(dirName)
    os.mkdir(dirName)
    
    # Write the .txt files for each page
    for key in ubcwpl.pages:
        filename = '%s.txt' % key.replace('/', '_')
        filename = os.path.join(dirName, filename)
        f = codecs.open(filename, encoding='utf-8', mode='w')
        f.write(ubcwpl.pages[key])
        f.close()

    # Reassure the user
    print '\nUBCWPL Web Site successfully written.\n\n'
    print 'See ubcwplHTML/%s directory\n\n' % dirName
"""