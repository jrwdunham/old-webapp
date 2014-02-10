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

"""This module contains general-purpose functions used in the OLD

"""

import os
import shutil
import re
import helpers as h
import codecs
import htmlentitydefs
import string
import pickle
import unicodedata as ud

from datetime import datetime, date, time

try:
    import json
except ImportError:
    import simplejson as json

from docutils import core

from pylons import session, app_globals
from pylons import config

from sqlalchemy import desc

import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta


def removeWhiteSpace(string):
    """Remove leading and trailing whitespace, newlines and tabs; reduce
    multiple spaces to single ones.
    
    """
    
    string = string.strip()
    string = string.replace('\n', ' ')
    string = string.replace('\t', ' ')
    patt = re.compile(' {2,}')
    string = patt.sub(' ', string)
    return string


def removeAllWhiteSpace(string):
    """Remove all spaces, newlines and tabs."""
    string = string.replace(u'\n', u'')
    string = string.replace(u'\t', u'')
    string = string.replace(u' ', u'')
    return string


def getUserID():
    """Returns logged in user's ID if a user is logged in; otherwise, None."""
    if 'user_id' in session:
        return session['user_id']
    else:
        return None


def pretty_filesize(bytes):
    """Converts filesize in bytes to a string representation
    in KB, MB or GB, as appropriate."""
    if bytes >= 1073741824:
        return str(round(bytes / 1024 / 1024 / 1024.0, 2)) + ' GB'
    elif bytes >= 1048576:
        return str(round(bytes / 1024 / 1024.0, 1)) + ' MB'
    elif bytes >= 1024:
        return str(round(bytes / 1024.0, 1)) + ' KB'
    elif bytes < 1024:
        return str(bytes) + ' bytes'


def filesize_to_bytes(value, unit):
    """Converts filesize in KB, MB or GB to an integer representing bytes."""
    value = float(value)
    if unit == 'GB':
        result = value * 1024 * 1024 * 1024
    elif unit == 'MB':
        result = value * 1024 * 1024
    elif unit == 'KB':
        result = value * 1024
    else:
        result = value
    return int(result)


def putOrthographyTranslatorsIntoSession():
    """Three variables need defining:
    
    1. storageToOutputTranslator
    2. inputToStorageTranslator
    3. storageToInputTranslator
    
    Whether these variables point to OrthographyTranslator instances or to None,
    depends on the user's user-specific settings.
    
    If (1) the user has chosen an input orthography and (2) that orthography
    differs from the system's storage orthography and (3) that orthography
    differs from the system's default input orthography and (4) that orthography
    is a key in app_globals.OLOrthographies, then set inputToStorageTranslator
    and storageToInputTranslator to the appropriate OrthographyTranslator
    instances.  Do similarly for the storage-output connection.
    
    """

    if session['user_inputOrthography'] and \
        (app_globals.storageOrthography != \
        session['user_inputOrthography']) and (
        session['user_inputOrthography'] != \
        app_globals.defaultInputOrthography) and (
        session['user_inputOrthography'] in app_globals.OLOrthographies):
        # Update the inputToStorageTranslator
        session['user_inputToStorageTranslator'] = h.OrthographyTranslator(
            app_globals.OLOrthographies[session['user_inputOrthography']][1],
            app_globals.storageOrthography[1]
        )
        # Update the storageToInputTranslator
        session['user_storageToInputTranslator'] = h.OrthographyTranslator(
            app_globals.storageOrthography[1],
            app_globals.OLOrthographies[session['user_inputOrthography']][1]
        )
    else:
        session['user_inputToStorageTranslator'] = None
        session['user_storageToInputTranslator'] = None

    if session['user_outputOrthography'] and \
        (app_globals.storageOrthography != \
        session['user_outputOrthography']) and (
        session['user_outputOrthography'] != \
        app_globals.defaultOutputOrthography) and (
        session['user_outputOrthography'] in app_globals.OLOrthographies):
        session['user_storageToOutputTranslator'] = h.OrthographyTranslator(
            app_globals.storageOrthography[1],
            app_globals.OLOrthographies[session['user_outputOrthography']][1]
        )
    else:
        session['user_storageToOutputTranslator'] = None

    session.save()


def getAuthorizedUserIntoSession(user):
    """Put user-specific info into the session.
    
    """

    session['userSettings'] = unpickleResearcherSettings(user)
    session['user'] = user
    session['user_id'] = user.id
    session['user_username'] = user.username
    session['user_role'] = user.role
    session['user_firstName'] = user.firstName
    session['user_lastName'] = user.lastName
    session['user_collectionViewType'] = user.collectionViewType
    session['user_inputOrthography'] = user.inputOrthography
    session['user_outputOrthography'] = user.outputOrthography
    session.save()
    putOrthographyTranslatorsIntoSession()


def updateSessionAndGlobals(user):
    """Updates both the current user's info in the session and the variable
    app_globals attributes.
    
    """
    
    # Update session with given user
    getAuthorizedUserIntoSession(user)
    
    # Update the secondary object lists in app_globals
    updateSecondaryObjectsInAppGlobals(app_globals)


def updateSecondaryObjectsInAppGlobals(app_globals):
    """Updates the app_globals secondary object list attributes, e.g., speakers,
    users, etc.

    """

    # Update the tags options (i.e., possible speakers, elicitors, sources, etc.)
    secondaryObjects = getSecondaryObjects()
    app_globals.speakers = secondaryObjects['speakers']
    app_globals.users = secondaryObjects['users']
    app_globals.nonAdministrators = secondaryObjects['nonAdministrators']
    app_globals.unrestrictedUsers= secondaryObjects['unrestrictedUsers']
    app_globals.sources = secondaryObjects['sources']
    app_globals.syncats = secondaryObjects['syncats']
    app_globals.keywords = secondaryObjects['keywords']
    app_globals.elicitationMethods = secondaryObjects['elicitationMethods']


def getSecondaryObjects(objectsList=None):
    """Returns a dict whose values are lists for each of speakers, users,
    sources, syntactic categories, elicitation methods, keywords.

    The optional objectsList parameter is a list specifying which objects should
    be retrieved.  If objectsList is None, all are retrieved.

    """

    # Speakers
    speakers = []
    if not objectsList or 'speakers' in objectsList:
        speakers = meta.Session.query(model.Speaker).order_by(
            model.Speaker.lastName).all()

    # Users
    users = []
    nonAdministrators = []
    if not objectsList or 'users' in objectsList:
        users = meta.Session.query(model.User).order_by(
            model.User.lastName).all()
        nonAdministrators = [user for user in users if
                             user.role == u'contributor']

    # Unrestricted Users
    unrestrictedUsers = []
    if not objectsList or 'unrestrictedUsers' in objectsList:
        appSet = meta.Session.query(
            model.ApplicationSettings).order_by(  
            desc(model.ApplicationSettings.id)).first()

        try:
            unrestrictedUserIDs = tuple([int(uu) for uu in json.loads(
                appSet.unrestrictedUsers)])
        except TypeError: # Error caused by json choking on None
            unrestrictedUserIDs = []
        unrestrictedUsers = meta.Session.query(model.User).filter(
            model.User.id.in_(unrestrictedUserIDs)).all()

    # Sources
    sources = []
    if not objectsList or 'sources' in objectsList:
        sources = meta.Session.query(model.Source).order_by(
            model.Source.authorLastName).order_by(
            model.Source.authorFirstName).order_by(
            desc(model.Source.year)).all()

    # Syntactic Categories
    syncats = []
    if not objectsList or 'syncats' in objectsList:
        syncats = meta.Session.query(model.SyntacticCategory).order_by(
            model.SyntacticCategory.name).all()

    # Keywords
    keywords = []
    if not objectsList or 'keywords' in objectsList:
        keywords = meta.Session.query(model.Keyword).order_by(
            model.Keyword.name).all()

    # Elicitation Methods
    elicitationMethods = []
    if not objectsList or 'elicitationMethods' in objectsList:
        elicitationMethods = meta.Session.query(
            model.ElicitationMethod).order_by(
            model.ElicitationMethod.name).all()

    return {
        'speakers': speakers,
        'users': users,
        'nonAdministrators': nonAdministrators,
        'unrestrictedUsers': unrestrictedUsers,
        'sources': sources,
        'syncats': syncats,
        'keywords': keywords,
        'elicitationMethods': elicitationMethods
    }


def applicationSettingsToAppGlobals(app_globals, applicationSettings=None):
    """This function puts the application settings data into app_globals.
    
    If an applicationSettings object is not received, we try to retrieve one
    from the model.
    
    """
    
    # If we have not been passed an applicationSettings object, create one
    #  using data from the model.  Note: new application settings are simply
    #  added to the application_settings table; thus we get the current settings
    #  by selecting that with the highest ID
    if not applicationSettings:
        applicationSettings = getApplicationSettings()

    # If we have an application settings object, update app_globals using it
    if applicationSettings:
        app_globals.objectLanguageName = applicationSettings.objectLanguageName
        app_globals.objectLanguageId = applicationSettings.objectLanguageId
        app_globals.metaLanguageName = applicationSettings.metaLanguageName
        app_globals.headerImageName = applicationSettings.headerImageName
        app_globals.colorsCSS = applicationSettings.colorsCSS.encode('ascii')
        app_globals.morphemeBreakIsObjectLanguageString = \
                        applicationSettings.morphemeBreakIsObjectLanguageString
        app_globals.orthographicValidation = \
                                    applicationSettings.orthographicValidation
        app_globals.narrPhonInventory = applicationSettings.narrPhonInventory
        app_globals.narrPhonValidation = applicationSettings.narrPhonValidation
        app_globals.broadPhonInventory = applicationSettings.broadPhonInventory
        app_globals.broadPhonValidation = \
                                        applicationSettings.broadPhonValidation
        app_globals.morphPhonInventory = applicationSettings.morphPhonInventory
        app_globals.morphPhonValidation = \
                                        applicationSettings.morphPhonValidation

        if applicationSettings.morphDelimiters:
            app_globals.morphDelimiters = removeAllWhiteSpace(
                                applicationSettings.morphDelimiters).split(u',')
        else:
            app_globals.morphDelimiters = ['-', '=']

        if applicationSettings.punctuation:
            app_globals.punctuation = list(removeAllWhiteSpace(
                                            applicationSettings.punctuation))
        else:
            app_globals.punctuation = list(
                                u""".,;:!?'"\u2018\u2019\u201C\u201D[]{}()-""")

        if applicationSettings.grammaticalities:
            app_globals.grammaticalities = [u''] + removeAllWhiteSpace(
                            applicationSettings.grammaticalities).split(u',')
        else:
            app_globals.grammaticalities = [u'', u'*', u'?', u'#']

        # Create the app_globals.OLOrthographies dictionary with the following
        #  structure: {identifier: (name, OrthographyObject), etc.}
        #  e.g., {'Orthography 1': ('NAPA', <Orthography object>)}
        app_globals.OLOrthographies = {}
        for i in range(1, 6):
            identifier = 'Orthography %s' % str(i)
            name = getattr(applicationSettings,
                        'objectLanguageOrthography%sName' % str(i))
            orthography = getattr(applicationSettings,
                        'objectLanguageOrthography%s' % str(i))
            lowercase = getattr(applicationSettings,
                        'OLO%sLowercase' % str(i))
            initialGlottalStops = getattr(applicationSettings,
                        'OLO%sInitialGlottalStops' % str(i))
            app_globals.OLOrthographies[identifier] = (
                name,
                h.Orthography(
                    orthography,
                    lowercase=lowercase,
                    initialGlottalStops=initialGlottalStops
                )
            )

        # Storage, Input and Output Orthographies point to the appropriate
        #  (name, <Orthography object>) tuples in app_globals.OLOrthographies
        app_globals.storageOrthography = app_globals.OLOrthographies[
            applicationSettings.storageOrthography]
        app_globals.defaultInputOrthography = app_globals.OLOrthographies[
            applicationSettings.defaultInputOrthography]
        app_globals.defaultOutputOrthography = app_globals.OLOrthographies[
            applicationSettings.defaultOutputOrthography]

        # Get the orthography of the metalanguage as an Orthography object
        app_globals.metaLanguageOrthography = \
            h.Orthography(applicationSettings.metaLanguageOrthography)
        
        # inputToStorageTranslator
        #  If the defaultInputOrthography differs from the storageOrthography,
        #  set app_globals.inputToStorageTranslator to the appropriate
        #  OrthographyTranslator instance; otherwise, set it to None
        if applicationSettings.storageOrthography != \
                                applicationSettings.defaultInputOrthography:
            app_globals.inputToStorageTranslator = h.OrthographyTranslator(
                app_globals.defaultInputOrthography[1],
                app_globals.storageOrthography[1]
            )
        else:
            app_globals.inputToStorageTranslator = None

        # storageToInputTranslator
        #  If the defaultInputOrthography differs from the storageOrthography,
        #  set app_globals.storageToInputTranslator to the appropriate
        #  OrthographyTranslator instance; otherwise, set it to None
        #  Note: this translator is required for updating data.
        if applicationSettings.storageOrthography != \
                                applicationSettings.defaultInputOrthography:
            app_globals.storageToInputTranslator = h.OrthographyTranslator(
                app_globals.storageOrthography[1],
                app_globals.defaultInputOrthography[1]
            )
        else:
            app_globals.storageToInputTranslator = None
            
        # storageToOutputTranslator
        #  If the defaultOutputOrthography differs from the storageOrthography,
        #  set app_globals.storageToInputTranslator to the appropriate
        #  OrthographyTranslator instance; otherwise, set it to None
        if applicationSettings.storageOrthography != \
                                applicationSettings.defaultOutputOrthography:
            app_globals.storageToOutputTranslator = h.OrthographyTranslator(
                app_globals.storageOrthography[1],
                app_globals.defaultOutputOrthography[1]
            )
        else:
            app_globals.storageToOutputTranslator = None

        unrestrictedUserIDs = json.loads(applicationSettings.unrestrictedUsers)
        unrestrictedUsers = meta.Session.query(model.User).filter(
            model.User.id.in_(unrestrictedUserIDs)).all()
        app_globals.unrestrictedUsers = unrestrictedUsers

        # Update Inventory objects (useful for validation)
        updateInventoryObjectsInAppGlobals(app_globals, applicationSettings)

    # We have no application settings object, so update app_globals with some
    #  default application settings data.
    else:
        defaultOrthography = ','.join(list(string.ascii_lowercase))
        app_globals.objectLanguageName = u'Anonymous'
        app_globals.metaLanguageName = u'Unknown'
        app_globals.headerImageName = u''
        app_globals.colorsCSS= 'green.css'
        app_globals.metaLanguageOrthography = h.Orthography(defaultOrthography)
        app_globals.OLOrthographies = {
            u'Orthography 1': (
                u'Unnamed',
                h.Orthography(
                    defaultOrthography, lowercase=1, initialGlottalStops=1
                )
            )
        }
        app_globals.storageOrthography = app_globals.OLOrthographies[
            u'Orthography 1']
        app_globals.defaultInputOrthography = app_globals.OLOrthographies[
            u'Orthography 1']
        app_globals.defaultOutputOrthography = app_globals.OLOrthographies[
            u'Orthography 1']
        app_globals.morphemeBreakIsObjectLanguageString = u'yes'
        app_globals.inputToStorageTranslator = None
        app_globals.storageToOutputTranslator = None

        app_globals.orthographicValidation = u'None'
        app_globals.narrPhonInventory = u''
        app_globals.narrPhonValidation = u'None'
        app_globals.broadPhonInventory = u''
        app_globals.broadPhonValidation = u'None'
        app_globals.morphPhonInventory = u''
        app_globals.morphDelimiters = [u'-', u'=']
        app_globals.morphPhonValidation = u'None'
        app_globals.punctuation = list(u""".,;:!?'"\u2018\u2019\u201C\u201D[]{}()-""")
        app_globals.grammaticalities = [u'', u'*', u'#', u'?']


def getApplicationSettings():
    """Return an ApplicationSettings instance.

    """

    return meta.Session.query(model.ApplicationSettings).order_by(
                    desc(model.ApplicationSettings.id)).first()

def updateInventoryObjectsInAppGlobals(app_globals, applicationSettings=None):
    """Updates the narrPhonInvObj, broadPhonInvObj, orthtranscrInvObj,
    morphBreakInvObj, punctInvObj and morphDelimInvObj properties of
    app_globals.  Called by the applicationSettingsToAppGlobals and X
    functions.

    """

    if not applicationSettings:
        applicationSettings = getApplicationSettings()

    fWNarrPhonTranscrs, fWBroadPhonTranscrs, fWOrthTranscrs, \
        fWMorphTranscrs = getForeignWordTranscriptions()
    storOrthAsList = getStorageOrthographyAsList(applicationSettings)
    app_globals.punctInvObj = Inventory(app_globals.punctuation)
    app_globals.morphDelimInvObj = Inventory(app_globals.morphDelimiters)
    app_globals.narrPhonInvObj = Inventory(fWNarrPhonTranscrs + [u' '] + 
        h.removeAllWhiteSpace(app_globals.narrPhonInventory).split(','))
    app_globals.broadPhonInvObj = Inventory(fWBroadPhonTranscrs + [u' '] + 
        h.removeAllWhiteSpace(app_globals.broadPhonInventory).split(','))
    app_globals.orthTranscrInvObj = Inventory(fWOrthTranscrs + 
        app_globals.punctuation + [u' '] + storOrthAsList)
    if app_globals.morphemeBreakIsObjectLanguageString == u'yes':
        app_globals.morphBreakInvObj = Inventory(fWMorphTranscrs +
            app_globals.morphDelimiters + [u' '] + storOrthAsList)
    else:
        app_globals.morphBreakInvObj = Inventory(fWMorphTranscrs + 
            app_globals.morphDelimiters + [u' '] +
            h.removeAllWhiteSpace(app_globals.morphPhonInventory).split(','))


################################################################################
# INPUT TO STORAGE TRANSLATE FAMILY OF FUNCTIONS
################################################################################


def getInputToStorageTranslator():
    """Looks for an input-to-storage translator first in the session and then
    in the globals.  If no translator is found, return the identity function.
    
    """
    if session['user_inputToStorageTranslator']:
        return lambda x: h.literal(session[
            'user_inputToStorageTranslator'].translate(x))
    elif app_globals.inputToStorageTranslator:
        return lambda x: h.literal(
            app_globals.inputToStorageTranslator.translate(x))
    else:
        return lambda x: x


def inputToStorageTranslate(string, isMBField=False):
    """This function translates input strings of the object language into the 
    appropriate storage orthography.  An input-to-storage translator is first
    looked for in the user-specific session dict, then in the system-wide
    app_globals; if no translator is found, the string is simply returned.
    
    The isMBField indicates whether the input string is from the morpheme break
    field.  If it is, and if this application does not treat morpheme break
    data as object language strings, then return the string.
    
    """
    if isMBField and app_globals.morphemeBreakIsObjectLanguageString == u'no':
        return string
    else:
        return getInputToStorageTranslator()(string)


def inputToStorageTranslateOLOnly(string):
    """This function behaves just like inputToStorageTranslate except that it
    applies only to strings in <orth></orth> tags.
    
    """
    patt = re.compile('<orth>(.*?)</orth>')
    translator = getInputToStorageTranslator()
    return patt.sub(lambda x: translator(x.group()), string)


################################################################################


################################################################################
# STORAGE TO INPUT TRANSLATE FAMILY OF FUNCTIONS
################################################################################


def getStorageToInputTranslator():
    """Looks for a storage-to-input translator first in the session and then
    in the globals.  If no translator is found, return the identity function.
    
    """
    if session['user_storageToInputTranslator']:
        return lambda x: h.literal(session[
            'user_storageToInputTranslator'].translate(x))
    elif app_globals.storageToInputTranslator:
        return lambda x: h.literal(
            app_globals.storageToInputTranslator.translate(x))
    else:
        return lambda x: x


def storageToInputTranslate(string, isMBField=False):
    """This function translates storage strings of the object language into the 
    appropriate input orthography.  A storage-to-input translator is first
    looked for in the user-specific session dict, then in the system-wide
    app_globals; if no translator is found, the string is simply returned.
    
    The isMBField indicates whether the input string is from the morpheme break
    field.  If it is, and if this application does not treat morpheme break
    data as object language strings, then return the string.
    
    """
    if isMBField and app_globals.morphemeBreakIsObjectLanguageString == u'no':
        return string
    else:
        return getStorageToInputTranslator()(string)


def storageToInputTranslateOLOnly(string):
    """This function behaves just like storageToInputTranslate except that it
    applies only to strings in <orth></orth> tags.
    
    """
    # '?' in regex gets us a non-greedy match, good for parsing xml
    patt = re.compile('<orth>(.*?)</orth>')
    translator = getStorageToInputTranslator()
    return patt.sub(lambda x: translator(x.group()), string)


################################################################################



################################################################################
# STORAGE TO OUTPUT TRANSLATE FAMILY OF FUNCTIONS
################################################################################


def getStorageToOutputTranslator():
    """Looks for a storage-to-input translator first in the session and then
    in the globals.  If no translator is found, return the identity function.
    
    """
    if 'user_storageToOutputTranslator' in session and \
    session['user_storageToOutputTranslator']:
        return lambda x: h.literal(session[
            'user_storageToOutputTranslator'].translate(x))
    elif app_globals.storageToOutputTranslator:
        return lambda x: h.literal(
            app_globals.storageToOutputTranslator.translate(x))
    else:
        return lambda x: h.literal(x)


def storageToOutputTranslate(string, isMBField=False):
    """This function translates storage strings of the object language into the 
    appropriate output orthography.  A storage-to-output translator is first
    looked for in the user-specific session dict, then in the system-wide
    app_globals; if no translator is found, the string is simply returned.
    
    The isMBField indicates whether the input string is from the morpheme break
    field.  If it is, and if this application does not treat morpheme break
    data as object language strings, then return the string.
    
    """
    if isMBField and app_globals.morphemeBreakIsObjectLanguageString == u'no':
        return string
    else:
        return getStorageToOutputTranslator()(string)


def storageToOutputTranslateOLOnly(string):
    """This function behaves just like storageToOutput except that it applies
    only to strings in <orth></orth> tags.
    
    """
    patt = re.compile('<orth>(.*?)</orth>')
    translator = getStorageToOutputTranslator()
    return patt.sub(lambda x: translator(x.group()), string)


################################################################################



def getObjectLanguageDetails():
    """I don't know what this function was supposed to be for..."""
    pass


def escapeUnderscores(string):
    return string.replace('_', '\_')


# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    """This function was copied from somewhere (...).  It is used in the
    getmatchinglanguages function of the SettingsController.
    """
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)


def tablify(listOfItems, maxCols, tableClass=None, tableId=None):
    """Returns an HTML table where each item from listOfItems occupies a single
    cell and where there are no more than maxCols columns.

    """

    numEmptyCells = maxCols - (len(listOfItems) % maxCols)
    if tableClass:
        tClass = " class='%s'" % tableClass
    else:
        tClass = ''
    if tableId:
        tId = " id='%s'" % tableId
    else:
        tId = ''
    result = '\n\n<table%s%s>' % (tClass, tId)
    for index in range(len(listOfItems)):
        noZeroIndex = index + 1
        item = listOfItems[index]
        if type(item) in (type(u''), type('')):
            itemRepr = item
        else:
            style = u''
            style2 = u'style="position: relative;"'
            itemRepr = u'<div class="graph">%s</div>\
                       <div class="graphInfo" %s><div %s>%s</div></div>' % (
                            item[0], style, style2, '; '.join(item[1:]))
        if noZeroIndex % maxCols is 1:
            result += '\n\t<tr>\n\t\t<td>%s</td>' % itemRepr
        elif noZeroIndex % maxCols is 0:
            result += '\n\t\t<td>%s</td>\n\t</tr>' % itemRepr
        else:
            result += '\n\t\t<td>%s</td>' % itemRepr
    if numEmptyCells != maxCols:
        result += '%s\n\t</tr>' % ('\n\t\t<td></td>' * numEmptyCells)
    result += '\n</table>\n\n'
    return result


def clip(string, maxLen):
    """Return the first maxLen characters of the input string."""
    if len(string) < maxLen:
        return string
    else:
        return string[:maxLen] + '...'


def rst2html(string):
    """Use docutils.core to return a string of restructuredtext as HTML.
    """
    result = core.publish_parts(string, writer_name='html')
    
    # It is necessary to append result['stylesheet'] to the head of the
    #  resulting HTML.  Do this by having rst2html return
    #  (result['html_body'], result['stylesheet']) and use Mako inheritance
    #  to put result['stylesheet'] in the HTML <head>
    
    return result['html_body']


xelatex_preamble = u"""\\usepackage{fontspec} 
% Font selection for XeLaTeX; see fontspec.pdf for documentation

\\defaultfontfeatures{Mapping=tex-text} 
% to support TeX conventions like ``---''

\\usepackage{xunicode} 
% Unicode support for LaTeX character names (accents, European chars, etc)

\\usepackage{xltxtra}
% Extra customizations for XeLaTeX

\\setmainfont{Charis SIL}
% set the main body font -- if you don't have Charis SIL, then install it or
% install and use Doulos SIL, or Aboriginal Sans, etc.
"""

covington_package = u"""
\\usepackage{covington}
% the covington package formats IGT
"""

expex_package = u"""
\\usepackage{expex}
% the expex package also formats IGT
"""

def rst2latex(string, **kwargs):
    """Use docutils.core to return a string of restructuredtext as a full LaTeX
    document.  Actually, this uses string replacement hacks to make a functional
    (so far?) XeLaTeX document.  These hacks consist of removing the
    '\usepackage[utf8]{inputenc}' declaration and adding some XeLaTeX commands
    to the preamble.

    """

    preamble = u'\n'.join([
        xelatex_preamble,
        {'covington': covington_package, 'expex': expex_package}.\
            get(kwargs.get('igt_package', 'expex'), expex_package)
    ])
    result = core.publish_parts(string, writer_name='latex')['whole']
    result = result.replace('\\usepackage[utf8]{inputenc}', '')
    result = result.replace('%%% Body', preamble + '\n\n%%% Body')
    return result


def getOrdString(string):
    """Take a string and return a space-delimited string of unicode code points
    (in standard U+XXXX notation) corresponding to each character in the string.
    
    """
    result = ''
    for char in string:
        result += 'U+%0.4X ' % ord(char)
    return result



def getKeyboardTable(fieldId, appSettings=None):
    """Create the keyboardTable to be displayed under the input field with id =
    fieldId.  The graphs of keyboard are those of the input orthography.

    """

    if not appSettings:
        appSettings = getApplicationSettings()

    if fieldId == 'transcription':
        graphemeList = getOrthographyAsList(appSettings, 'user input')
    elif fieldId == 'morphemeBreak':
        if app_globals.morphemeBreakIsObjectLanguageString == u'yes':
            graphemeList = getOrthographyAsList(appSettings, 'user input')
        else:
            graphemeList = app_globals.morphBreakInvObj.getInputList()
    elif fieldId == 'phoneticTranscription':
        graphemeList = app_globals.broadPhonInvObj.getInputList()
    elif fieldId == 'narrowPhoneticTranscription':
        graphemeList = app_globals.narrPhonInvObj.getInputList()
    else:
        graphemeList = []

    keys = ['<a class="key" title="Click this key to insert \'%s\' into the %s field" \
            onclick="graphToInput(\'%s\', \'%s\');">%s</a>' \
            % (x.replace("'", "\\'"), fieldId, x.replace("'", "\\'"), fieldId, \
            x) for x in graphemeList]
    return h.literal(h.tablify(keys, 10, 'keyboardTable'))


def getInventoryListForKeyboard(fieldId, appSettings=None):
    """Return a list of graphemes to be used for the keyboard table on the form
    add/update page.

    """

    if not appSettings:
        appSettings = getApplicationSettings()

    def removeForeignWords(lst):
        return lst[lst.index(u' ') + 1:]

    if fieldId == 'transcription':
        graphemeList = getOrthographyAsList(appSettings, 'user input')
    elif fieldId == 'morphemeBreak':
        if app_globals.morphemeBreakIsObjectLanguageString == u'yes':
            graphemeList = getOrthographyAsList(appSettings, 'user input')
        else:
            graphemeList = removeForeignWords(
                app_globals.morphBreakInvObj.getInputList())
    elif fieldId == 'phoneticTranscription':
        graphemeList = removeForeignWords(
            app_globals.broadPhonInvObj.getInputList())
    elif fieldId == 'narrowPhoneticTranscription':
        graphemeList = removeForeignWords(
            app_globals.narrPhonInvObj.getInputList())
    else:
        graphemeList = []

    return graphemeList



def createResearcherDirectory(researcher):
    """Creates a directory named researcher.username in files/researchers/.
    
    """

    directoryPath = os.path.join(
        config['app_conf']['permanent_store'], 'researchers',
        researcher.username
    )

    try:
        os.mkdir(directoryPath)
        createResearcherSettingsPickleFile(researcher, directoryPath)
    except OSError:
        pass


def destroyResearcherDirectory(researcher):
    """Destroys the directory named researcher.username in files/researchers/.
    
    """

    directoryPath = os.path.join(
        config['app_conf']['permanent_store'], 'researchers', researcher.username)
    shutil.rmtree(directoryPath, ignore_errors=True)


def createResearcherSettingsPickleFile(researcher, directoryPath):
    """Creates a Python pickle for storing a researcherSettings dictionary.
    
    Default contents is an empty dictionary.
    
    """
    
    researcherSettings = {}
    temp = '%s.pickle' % researcher.username
    filename = os.path.join(directoryPath, temp)
    file = open(filename, 'wb')
    pickle.dump(researcherSettings, file)

def unpickleResearcherSettings(researcher):
    """Unpickles the researcher's settings and returns the researcherSettings
    dictionary.
    
    """

    directoryPath = os.path.join(
        config['app_conf']['permanent_store'],
        'researchers',
        researcher.username
    )
    temp = '%s.pickle' % researcher.username
    filename = os.path.join(directoryPath, temp)

    try:
        file = open(filename, 'rb')
    except IOError:
        createResearcherSettingsPickleFile(researcher, directoryPath)
        file = open(filename, 'rb')

    return pickle.load(file)

def pickleResearcherSettings(researcherSettings, researcher):
    """Pickles the researcher's settings.
    
    """

    directoryPath = os.path.join(
        config['app_conf']['permanent_store'], 'researchers',
        researcher.username
    )
    temp = '%s.pickle' % researcher.username
    filename = os.path.join(directoryPath, temp)
    file = open(filename, 'wb')

    pickle.dump(researcherSettings, file)


def latexSmallCaps(string):
    """Return a string converted to lowercase within a LaTeX smallcaps
    expression (\textsc{}).
    
    """
    
    if string.isupper():
        return '\\textsc{%s}' % string.lower()
    else:
        return string


def capsToLatexSmallCaps(string):
    """Function used to convert uppercase morpheme glosses to LaTeX smallcaps.
    
    """
    temp = re.split('(%s| )' % '|'.join(app_globals.morphDelimiters), string)
    return ''.join([latexSmallCaps(x) for x in temp])


def getListOfLanguages():
    """ Function returns the ISO 639-3 Code Set
    (http://www.sil.org/iso639-3/download.asp) as a list.
    
    Expects a UTF-8 file named 'iso-639-3.tab' in lib/languages. 
    
    """
    file = codecs.open(
        os.path.join(
            config['pylons.paths']['root'], 'lib', 'languages', 'iso-639-3.tab'
        ),
        'r', 'utf-8'
    )
    temp = [x.split('\t') for x in file]
    return temp

def commatizeNumberString(numberString):
    if len(numberString) > 3:
        numberString = '%s,%s' % (numberString[:-3], numberString[-3:])
    if len(numberString) > 7:
        numberString = '%s,%s' % (numberString[:-7], numberString[-7:])
    return numberString



def parse_timestamp(s):
    """Returns (datetime, tz offset in minutes) or (None, None).
    
    Code origin:

        http://efreedom.com/Question/1-2211362/Parse-Xsd-DateTime-Format
    
    """

    m = re.match(""" ^
        (?P<year>-?[0-9]{4}) - (?P<month>[0-9]{2}) - (?P<day>[0-9]{2})
        T (?P<hour>[0-9]{2}) : (?P<minute>[0-9]{2}) : (?P<second>[0-9]{2})
        (?P<microsecond>\.[0-9]{1,6})?
        (?P<tz>
            Z | (?P<tz_hr>[-+][0-9]{2}) : (?P<tz_min>[0-9]{2})
        )?
        $ """, s, re.X)
    
    if m is not None:
        values = m.groupdict()

        if values["tz"] in ("Z", None):
            tz = 0
        else:
            tz = int(values["tz_hr"]) * 60 + int(values["tz_min"])

        if values["microsecond"] is None:
            values["microsecond"] = 0
        else:
            values["microsecond"] = values["microsecond"][1:]
            values["microsecond"] += "0" * (6 - len(values["microsecond"]))

        values = dict((k, int(v)) for k, v in values.iteritems() \
            if not k.startswith("tz"))

        try:
            return datetime(**values), tz
        except ValueError:
            pass

    return None, None


def pretty_date(datetimeInput=False):
    """Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc.

    Taken from:

      http://stackoverflow.com/questions/1551382/python-user-friendly-time-format

    CHANGES TO NOTE:
    
    1. now is now UTC, i.e., datetime.utcnow() since my datetimes are in UT.
    2. "1 month ago" is now returned instead of, for example, "1 months ago".
    3. datetime.date objects are now accepted inputs.

    """

    now = datetime.utcnow()
    if type(datetimeInput) is int:
        diff = now - datetime.fromtimestamp(datetimeInput)
    elif isinstance(datetimeInput, datetime):
        diff = now - datetimeInput
    elif isinstance(datetimeInput, date):
        diff = now - datetime.combine(datetimeInput, time(0))
    elif not datetimeInput:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            if (second_diff / 3600) == 1:
                return "1 hour ago"
            else:
                return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        if (day_diff / 7) == 1:
            return "1 week ago"
        else:
            return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        if (day_diff / 30) == 1:
            return "1 month ago"
        else:
            return str(day_diff/30) + " months ago"
    if (day_diff / 365) == 1:
        return "1 year ago"
    return str(day_diff/365) + " years ago"


def userIsAuthorizedToAccessForm(user, form):
    """Return true if the user is authorized to access the form.  Forms tagged
    with the 'restricted' keyword are only accessible to administrators, their
    enterers and unrestricted users.

    """

    return not (form.keywords and \
        'restricted' in [k.name for k in form.keywords] and \
        user.id not in [uu.id for uu in app_globals.unrestrictedUsers] and \
        user.id != form.enterer_id and \
        user.role != u'administrator')


def appendMsgToFlash(msg):
    if 'flash' in session:
        session['flash'] += msg
    else:
        session['flash'] = msg




def getUnicodeNames(string):
    """Returns a string of comma-delimited unicode character names corresponding
    to the characters in the input string.

    """

    return ', '.join([ud.name(c, u'<no name>') for c in string])

def getUnicodeCodePoints(string):
    """Returns a string of comma-delimited unicode code points corresponding
    to the characters in the input string.

    """

    return ', '.join(['U+%04X' % ord(c) for c in string])


def NFD(unistr):
    """Return a unistr using canonical decompositional normalization (NFD).

    """
    try:
        return ud.normalize('NFD', unistr)
    except TypeError:
        return unistr

def NFDDict(dict_):
    """NFD normalize all unicode values in dict_.
    
    """

    for k in dict_:
        try:
            dict_[k] = h.NFD(dict_[k])
        except TypeError:
            pass
    return dict_

class Inventory:
    """An inventory is a set of graphemes/polygraphs/characters.  Initialization
    requires a list.

    Display methods. getHTMLTable returns an HTML table for displaying the
    inventory which provides unicode metadata such as character name, character
    code, etc.

    This class should be the base class from which the Orthography class
    inherits but I don't have time to implement that right now.
    
    """

    def __init__(self, inputList):
        self.inputList = inputList
        self._getUnicodeMetadata(inputList)
        self._setRegexValidator(inputList)
        self._compileRegexValidator(self.regexValidator)

    def _getUnicodeMetadata(self, inputList):
        self.inventoryWithUnicodeMetadata = [self._getNameCodeDistNorm(g)
                                             for g in inputList]

    def _getNameCodeDistNorm(self, graph):
        return (graph, getUnicodeNames(graph), getUnicodeCodePoints(graph))

    def _getDistinctNFCNormalization(self, graph):
        graphNFC = ud.normalize('NFC', graph)
        if graphNFC != graph:
            return graphNFC
        else:
            return u''

    def _setRegexValidator(self, inputList):
        disjPatt = u'|'.join([escREMetaChars(g) for g in inputList])
        self.regexValidator = u'^(%s)*$' % disjPatt

    def _compileRegexValidator(self, regexValidator):
        self.compiledRegexValidator = re.compile(regexValidator)

    def getInputList(self):
        return self.inputList

    def getRegexValidator(self, substr=False):
        """Returns a regex that matches only strings composed of zero or more
        of the graphemes in the inventory (plus the space character).

        """

        return self.regexValidator

    def getNonMatchingSubstrings(self, string):
        """Return a list of substrings of string that are not constructable
        using the inventory.

        """

        regex = u'|'.join([escREMetaChars(g) for g in self.inputList])
        regex = u'(%s)+' % regex
        patt = re.compile(regex)
        list_ = patt.split(string)
        nonMatchingSubstrings = [escREMetaChars(x) for x in list_[::2] if x]
        return nonMatchingSubstrings

    def getHTMLTable(self, className='', tabLen=5):
        return tablify(self.inventoryWithUnicodeMetadata, tabLen, className)

    def stringIsValid(self, string):
        """Return False if string cannot be generated by concatenating the
        elements of the orthography, else return True.

        """

        if self.compiledRegexValidator.match(string):
            return True
        return False


def getCommaDelimitedStringAsInventory(string):
    return h.Inventory(h.removeAllWhiteSpace(string).split(','))


def escREMetaChars(string):
    """Escapes regex metacharacters so that we can formulate a regular to feed
    to SQL based on an arbitrary, user-specified inventory of
    graphemes/polygraphs.

    """

    def esc(c):
        if c in u'\\^$*+?{,}.|][()^-':
            return re.escape(c)
        return c
    return ''.join([esc(c) for c in string])


def getForeignWordKeywordIds():
    """Return a list of ids corresponding to the keywords with 'foreign word'
    as their name.

    """

    foreignWordKeywords = meta.Session.query(model.Keyword).filter(
        model.Keyword.name == u'foreign word').all()
    return [fwk.id for fwk in foreignWordKeywords]


def getForeignWords():
    """Return the forms that are tagged with a 'foreign word' keyword.  This is
    useful for input validation as foreign words may contain otherwise illicit
    characters/graphemes.

    ***Note*** This should obviously be done with a SQL join!  However, SQLite
    on my system is taking *forever* to perform a join query, hence this
    roundabout.

    """

    foreignWordKeywordIds = getForeignWordKeywordIds()
    formKeywords = meta.Session.query(model.FormKeyword).filter(
        model.FormKeyword.keyword_id.in_(foreignWordKeywordIds)).all()
    formIds = [fkw.form_id for fkw in formKeywords]
    return meta.Session.query(model.Form).filter(
        model.Form.id.in_(formIds)).all()

def getForeignWordTranscriptions():
    """Returns a 4-tuple (fWNarrPhonTranscrs, fWBroadPhonTranscrs,
    fWOrthTranscrs, fWMorphTranscrs) where each element is a list of
    transcriptions (narrow phonetic, broad phonetic, orthographic, morphemic)
    of foreign words.

    """

    foreignWords = getForeignWords()
    fWNarrPhonTranscrs = []
    fWBroadPhonTranscrs = []
    fWOrthTranscrs = []
    fWMorphTranscrs = []
    for fw in foreignWords:
        if fw.narrowPhoneticTranscription:
            fWNarrPhonTranscrs.append(fw.narrowPhoneticTranscription)
        if fw.phoneticTranscription:
            fWBroadPhonTranscrs.append(fw.phoneticTranscription)
        if fw.morphemeBreak:
            fWMorphTranscrs.append(fw.morphemeBreak)
        fWOrthTranscrs.append(fw.transcription)
    return (fWNarrPhonTranscrs, fWBroadPhonTranscrs, fWOrthTranscrs, fWMorphTranscrs)


def formIsForeignWord(form):
    fwkwIds = getForeignWordKeywordIds()
    kwIds = [kw.id for kw in form.keywords]
    if [id for id in fwkwIds if id in kwIds]:
        return True
    return False

def updateInventoryObjsIfFormIsForeignWord(form):
    if formIsForeignWord(form):
        updateInventoryObjectsInAppGlobals(app_globals)


def getInputOrthographyAsString():
    """Returns a string representing the input orthography.  Looks first for a
    user-specific value in the session, then a global value in app_globals.  If
    nothing is found, returns empty string.

    """

    if 'user_inputOrthography' in session and session['user_inputOrthography']:
        return app_globals.OLOrthographies[
            session['user_inputOrthography']][1].orthographyAsString
    elif hasattr(app_globals, 'defaultInputOrthography') and \
        app_globals.defaultInputOrthography[1]:
        return app_globals.defaultInputOrthography[1].orthographyAsString
    else:
        return ''


def getOrthographyAsList(appSettings=None, whichOrthography='storage'):
    """Return the specified orthography as a list of graphemes/polygraphs.

    """

    if not appSettings:
        appSettings = getApplicationSettings()

    if whichOrthography == u'default input':
        orthId = appSettings.defaultInputOrthography[-1]
    elif whichOrthography == u'user input':
        orthId = session.get('user_inputOrthography', None)
        if not orthId:
            orthId = appSettings.defaultInputOrthography
        orthId = orthId[-1]
    elif whichOrthography == u'default output':
        orthId = appSettings.defaultOutputOrthography[-1]
    elif whichOrthography == u'user input':
        orthId = session.get('user_outputOrthography', None)
        if not orthId:
            orthId = appSettings.defaultInputOrthography
        orthId = orthId[-1]
    else:
        orthId = appSettings.storageOrthography[-1]

    orthography = getattr(appSettings,
                    'objectLanguageOrthography%s' % orthId, u'').replace(
                    u'[', u'').replace(u']', u'').split(u',')
    lowercase = {None: True, u'1': True, u'0': False}[
                    getattr(appSettings, 'OLO%sLowercase' % orthId, None)]

    # Add uppercase correspondants
    if not lowercase:
        temp = orthography[:]
        orthography = []
        for g in temp:
            orthography.append(g)
            if g.capitalize() != g:
                orthography.append(g.capitalize())

    return orthography


def getStorageOrthographyAsList(appSettings):
    """Return the storage orthography as a list of graphemes/polygraphs.

    """

    return getOrthographyAsList(appSettings, 'storage')


def getFormCount():
    """Get formCount from app_globals.  If undefined, define and return it.

    """

    formCount = getattr(app_globals, 'formCount', None)
    if not formCount:
        formCount = meta.Session.query(model.Form).count()
        app_globals.formCount = formCount
    return formCount
