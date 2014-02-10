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
import smtplib
import string
from random import choice

try:
    import json
except ImportError:
    import simplejson as json

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate

from formencode.schema import Schema
from formencode.validators import UnicodeString, Invalid
from formencode import htmlfill, variabledecode

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

log = logging.getLogger(__name__)

class LoginForm(Schema):
    """LoginForm simply validates that both username
    and passwrod have been entered.""" 
    allow_extra_fields = True
    filter_extra_fields = True
    username = UnicodeString(not_empty=True)
    password = UnicodeString(not_empty=True)


def generatePassword(length=12, chars=string.letters + string.digits):
    """Generate password function taken from
    http://code.activestate.com/recipes/59873-random-password-generation/

    """

    return ''.join([choice(chars) for i in range(length)])


class LoginController(BaseController):

    def login(self):
        """Renders the login.html page for authentication.  login.html calls the
        authenticate action.
        
        """
        
        return render('/derived/login/login.html')

    @restrict('POST')
    @validate(schema=LoginForm(), form='login')
    def authenticate(self):
        """Checks whether username and password match any records in the User
        table.
        
        """ 
        
        username = self.form_result['username']
        password = unicode(
            hashlib.sha224(self.form_result['password']).hexdigest())
        user_q = meta.Session.query(model.User)
        user = user_q.filter(model.User.username==username).filter(
            model.User.password==password).first()

        if user:
            # Successful login
            # Update session and app_globals data (function located in lib/functions.py)
            h.updateSessionAndGlobals(user)
            redirect(url(controller='home', action='index'))
        else:
            session['flash'] = 'Authentication failed.'
            return render('/derived/login/login.html')

    @restrict('POST')
    def authenticate_ajax(self):
        """Checks whether username and password match any records in the User
        table.  Returns a stringified JSON object.

        """ 

        response.headers['Content-Type'] = 'application/json'
        schema = LoginForm()
        values = variabledecode.variable_decode(request.params)
        try:
            result = schema.to_python(values)
        except Invalid, e:
            result = {'valid': False, 'errors': e.unpack_errors()}
            return json.dumps(result)
        else:
            username = values['username']
            password = unicode(
                hashlib.sha224(values['password']).hexdigest())

            user = meta.Session.query(model.User).filter(
                model.User.username==username).filter(
                model.User.password==password).first()

            if user:
                # Successful login
                # Update session and app_globals data (function located in
                #  lib/functions.py)
                h.updateSessionAndGlobals(user)
                result = {'valid': True, 'authenticated': True}
                return json.dumps(result)
            else:
                result = {'valid': True, 'authenticated': False}
                return json.dumps(result)


    def check_authentication_ajax(self):
        """Checks if the user is logged in, i.e., checks if 'user_username' is
        in the session.

        """

        response.headers['Content-Type'] = 'application/json'
        return json.dumps('user_username' in session)


    def logout(self):
        """Log the user out by destroying the session['user_username']
        variable.  Redirect to home page.
        
        """
        
        if 'user_username' in session:
            del session['user_username']
            del session['user_id']
            del session['user_role']
            del session['user_firstName']
            del session['user_lastName']
            session['flash'] = 'You have been logged out.'
            session.save()
        redirect(url(controller='home', action='index'))

    def logout_ajax(self):
        """Logout the user by destroying the relevant keys of the session
        object.  If 

        """

        if 'user_username' in session:
            del session['user_username']
            del session['user_id']
            del session['user_role']
            del session['user_firstName']
            del session['user_lastName']
            session.save()

        response.headers['Content-Type'] = 'application/json'
        result = {'authenticated': False}
        return json.dumps(result)

    def email_reset_password_ajax(self):
        """Try resetting the user's password and emailing them the new one.

        """

        response.headers['Content-Type'] = 'application/json'

        user = meta.Session.query(model.User).filter(
            model.User.username==username).first()

        if user:
            # Reset the user's password
            newPassword = generatePassword()
            user.password = newPassword
            meta.Session.commit()

            # Sender email: e.g., bla@old.org, else old@old.org
            lang = app_globals.objectLanguageId
            lang = lang if lang else 'old'
            sender = '%s@old.org' % lang

            # Receiver email
            receivers = [user.email]

            # Message
            appName = lang.upper() + ' OLD' if lang != 'old' else 'OLD'
            appURL = log.debug(url('/', qualified=True))
            message = 'From: %s <%s>\n' % (appName, sender)
            message += 'To: %s %s <%s>\n' % (user.firstName, user.lastName,
                                             user.email)
            message += 'Subject: %s Password Reset\n\n\n' % appName
            message += 'Your password at %s has been reset to %s.\n\n' % (
                newPassword, appURL)
            message += 'Please change it once you have logged in.\n\n'
            message += '(Do not reply to this email.)'

            # Send the message
            try:
               smtpObj = smtplib.SMTP('localhost')
               smtpObj.sendmail(sender, receivers, message)
               return json.dumps({'validUsername': True, passwordReset: True})
            except:
               return json.dumps({'validUsername': True, passwordReset: False})

        else:
            return json.dumps({'validUsername': False, passwordReset: False})