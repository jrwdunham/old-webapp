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

"""This controller creates an XML-RPC server that serves OLD application data
-- i.e., database records, binary files -- to an OLD client.

The idea is this: use XML-RPC to sync a "mirror" (read-only) OLD application
with the "true" OLD application.  

Web pages on XML-RPC with Pylons:

- http://pylonshq.com/docs/en/1.0/controllers/#using-the-xml-rpc-controller-for-xml-rpc-requests
- http://wiki.pylonshq.com/display/pylonsdocs/Using+the+XMLRPCController

Here is some sample client code::

    from xmlrpclib import Server
    import hashlib
    
    server = Server('http://127.0.0.1:5001/rpcserver')
    
    username = 'admin'
    password = hashlib.sha224('admin').hexdigest()
    
    print server.forms(username, password)

What needs to happen:

- user on "mirror" clicks "Sync" button
- rpcclient controller initiates sync
- every table will need a datetimeModified field
- rpcclient 
"""


import logging
import xmlrpclib
import os
from pylons.controllers.util import abort, redirect_to
from pylons.controllers import XMLRPCController
from onlinelinguisticdatabase.lib.base import BaseController, render
from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url, config
from pylons.controllers.util import abort, redirect
from pylons.decorators import validate
from pylons.decorators.rest import restrict

import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

log = logging.getLogger(__name__)

class RpcserverController(XMLRPCController):

    def forms(self, username, password):
        """Docstring, dude!
        
        """
        
        user_q = meta.Session.query(model.User)
        user = user_q.filter(model.User.username==username).filter(
            model.User.password==password).first()
        if user:
            form_q = meta.Session.query(model.Form)
            forms = form_q.all()
            return [form.id for form in forms]
        else:
            return ['no smokes, Jack!']
    forms.signature = [['array', 'string', 'string']]

    def files(self, username, password):
        """Docstring, dude!"""
        user_q = meta.Session.query(model.User)
        user = user_q.filter(model.User.username==username).filter(
            model.User.password==password).first()
        if user:
            file_q = meta.Session.query(model.File)
            files = file_q.all()
            if files:
                file = files[0]
                filePath = os.path.join(
                    config['app_conf']['permanent_store'], file.name)
                handle = open(filePath)
                #print '\n\n\nSize:%s\n\n\n' % os.fstat(handle.fileno())[6]
                return xmlrpclib.Binary(handle.read())
                handle.close()
            else:
                return ['no smokes, Jack!']
        else:
            return ['no smokes, Jack!']
    files.signature = [['base64', 'string', 'string'], ['array', 'string', 'string']]
   
    def dog(self):
        return '<&>'
    dog.signature = [['string']]