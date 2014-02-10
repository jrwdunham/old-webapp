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
import re
import string
import os

try:
    from itertools import product
except ImportError:
    product = lambda x, y: ((a, b) for a in x for b in y)
import unicodedata as ud

try:
    import json
except ImportError:
    import simplejson as json

from pylons import request, response, session, app_globals, config,\
    tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict
from pylons.decorators import validate

from formencode.schema import Schema
from formencode.validators import Int, UnicodeString, Email, Invalid,\
    FancyValidator, PlainText, OneOf, StringBoolean
from formencode import htmlfill, variabledecode
import formencode
from formencode.foreach import ForEach

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from sqlalchemy import desc, or_, not_

log = logging.getLogger(__name__)



class UnrestrictedUser(Schema):
    """UnrestrictedUser validator ensures that unrestricted users are integers
    representing user IDs.
    
    """

    unrestrictedUser = Int()

class AlterSettingsForm(Schema):
    """AlterSettingsForm is a Schema for validating the data entered at the
    system settings page.

    """

    allow_extra_fields = True
    filter_extra_fields = True
    pre_validators = [variabledecode.NestedVariables()]

    OLName = UnicodeString()
    OLId = UnicodeString()

    MLName = UnicodeString()
    MLId = UnicodeString()
    MLOrthography = UnicodeString()

    headerImageName = UnicodeString()
    colorsCSS = UnicodeString()

    orthographyOptions = [u'Orthography %s' % unicode(i) for i \
                          in range(1,6)]
    storageOrthography = OneOf(orthographyOptions)
    defaultInputOrthography = UnicodeString()
    defaultOutputOrthography = UnicodeString()

    objectLanguageOrthography1Name = UnicodeString()
    objectLanguageOrthography1 = UnicodeString()
    OLO1Lowercase = StringBoolean(if_missing=False)
    OLO1InitialGlottalStops = StringBoolean(if_missing=False)

    objectLanguageOrthography2Name = UnicodeString()
    objectLanguageOrthography2 = UnicodeString()
    OLO2Lowercase = StringBoolean(if_missing=False)
    OLO2InitialGlottalStops = StringBoolean(if_missing=False)

    objectLanguageOrthography3Name = UnicodeString()
    objectLanguageOrthography3 = UnicodeString()
    OLO3Lowercase = StringBoolean(if_missing=False)
    OLO3InitialGlottalStops = StringBoolean(if_missing=False)
    
    objectLanguageOrthography4Name = UnicodeString()
    objectLanguageOrthography4 = UnicodeString()
    OLO4Lowercase = StringBoolean(if_missing=False)
    OLO4InitialGlottalStops = StringBoolean(if_missing=False)

    objectLanguageOrthography5Name = UnicodeString()
    objectLanguageOrthography5 = UnicodeString()
    OLO5Lowercase = StringBoolean(if_missing=False)
    OLO5InitialGlottalStops = StringBoolean(if_missing=False)

    morphemeBreakIsObjectLanguageString = UnicodeString()

    unrestrictedUsers = ForEach(UnrestrictedUser())

    orthographicValidation = OneOf([u'None', u'Warning', u'Error'])
    narrPhonInventory = UnicodeString()
    narrPhonValidation = OneOf([u'None', u'Warning', u'Error'])
    broadPhonInventory = UnicodeString()
    broadPhonValidation = OneOf([u'None', u'Warning', u'Error'])
    morphPhonInventory = UnicodeString()
    morphDelimiters = UnicodeString()
    morphPhonValidation = OneOf([u'None', u'Warning', u'Error'])
    punctuation = UnicodeString()
    grammaticalities = UnicodeString()


def renderEditSettings(values=None, errors=None):
    """Function is called by the edit action to create the Edit Application
    Settings HTML form.
    
    """

    html = render('/derived/settings/edit.html')
    return htmlfill.render(html, defaults=values, errors=errors)


def getOutputOrthographyTranslators(olo, oos):
    """If getOLOrthographyTranslators func works, destroy this one!
    
    """

    olo = h.Orthography(olos)
    return [h.OrthographyTranslator(olo, h.Orthography(oo)) for oo in oos]


def getOLOrthographyTranslators(olos):
    translators = []
    for pair in product(olos, olos):
        translator = h.OrthographyTranslator(pair[0], pair[1])
        translators.append(translator)
    return translators



def getOrthographiesAsInventories(appSettings, punctuation=False, space=False,
                                  delimiters=None):
    """Return the orthographies in application_settings as Inventory objects in
    a dict of the form {id: (name, Inventory)}

    """

    orthographiesAsInventories = {}
    for i in range(1, 6):
        identifier = 'Orthography %s' % str(i)
        name = getattr(appSettings, 'objectLanguageOrthography%sName' % str(i),
                                                                        None)
        orthography = getattr(appSettings,
                              'objectLanguageOrthography%s' % str(i), u'')
        if orthography:
            orthography = orthography.replace(u'[', u'').replace(
                            u']', u'').split(u',')
        lowercase = {None: True, u'1': True, u'0': False}[
                    getattr(appSettings, 'OLO%sLowercase' % str(i), None)]
        initialGlottalStops = getattr(appSettings,
                                    'OLO%sInitialGlottalStops' % str(i), None)

        # Add uppercase correspondants
        # Note: python2.5 capitalizes glottal stop U+0294 to capital glottal
        #  stop U+0241 put python2.6 does not!  
        if not lowercase:
            temp = orthography[:]
            orthography = []
            for g in temp:
                orthography.append(g)
                if g.capitalize() != g:
                    orthography.append(g.capitalize())

        if punctuation:
            punctuation = appSettings.punctuation
            orthography += list(punctuation)

        if space:
            orthography.append(u' ')

        if delimiters:
            orthography += delimiters

        if name and orthography:
            orthographiesAsInventories[identifier] = (name,
                                                h.Inventory(orthography))

    return orthographiesAsInventories


def getInventoriesAsPropertiesOfC(appSettings):
    """Get Inventory objects for the metalanguage orthography, the narrow and
    broad phonetic transcription inventories, the morphophonemic segmentation
    inventory, the morpheme delimiters, the punctuation set and the
    grammaticalities.  Assign these Inventory objects to c properties.

    """

    # Get metalanguage orthography as an Inventory object
    c.metaLanguageOrthography = h.getCommaDelimitedStringAsInventory(
                            appSettings.metaLanguageOrthography)

    # Get inventories as Inventory object properties of c
    c.narrPhonInventory = h.getCommaDelimitedStringAsInventory(
                                appSettings.narrPhonInventory)
    c.broadPhonInventory = h.getCommaDelimitedStringAsInventory(
                                appSettings.broadPhonInventory)
    c.morphPhonInventory = h.getCommaDelimitedStringAsInventory(
                                appSettings.morphPhonInventory)
    c.morphDelimiters = h.getCommaDelimitedStringAsInventory(
                                appSettings.morphDelimiters)
    c.punctuation = h.Inventory(list(h.removeAllWhiteSpace(
                        appSettings.punctuation)))
    c.grammaticalities = h.getCommaDelimitedStringAsInventory(
                        appSettings.grammaticalities)

class SettingsController(BaseController):
    """Controller for viewing and altering the system-wide settings of the
    application.
    
    """
    
    @h.authenticate
    def index(self):
        """View the application settings.
        
        """

        # Query the model for the application settings
        c.applicationSettings = meta.Session.query(
            model.ApplicationSettings).order_by(
                desc(model.ApplicationSettings.id
                )
            ).first()

        # Get obj lang orthographies as Inventoriy objects
        c.orthographiesAsInventories = getOrthographiesAsInventories(
                                                        c.applicationSettings)

        # Get metalanguage orthography, and other graph sets as Inventory objects
        getInventoriesAsPropertiesOfC(c.applicationSettings)

        # Get info about the database/RDBMS being used
        SQLAlchemyURL = config['sqlalchemy.url']
        c.rdbms = SQLAlchemyURL.split(':')[0]
        c.databaseName = SQLAlchemyURL.split('/')[-1]
        
        c.unrestrictedUsers = app_globals.unrestrictedUsers

        return render('/derived/settings/index.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def edit(self):
        """Edit the system settings.

        """

        appSet = c.applicationSettings = meta.Session.query(
            model.ApplicationSettings).order_by(
            desc(model.ApplicationSettings.id)).first()

        c.colorsCSSOptions = os.listdir(os.path.join(
            config['pylons.paths']['root'], 'public', 'css', 'colors'
        ))

        if c.applicationSettings:
            values = {
                'OLName': appSet.objectLanguageName,
                'OLId': appSet.objectLanguageId,

                'MLName': appSet.metaLanguageName,
                'MLId': appSet.metaLanguageId,
                'MLOrthography': appSet.metaLanguageOrthography,

                'headerImageName': appSet.headerImageName,
                'colorsCSS': appSet.colorsCSS,
                
                'storageOrthography': appSet.storageOrthography,
                'defaultInputOrthography': appSet.defaultInputOrthography,
                'defaultOutputOrthography': appSet.defaultOutputOrthography,
                
                'objectLanguageOrthography1': appSet.objectLanguageOrthography1,
                'objectLanguageOrthography1Name': \
                    appSet.objectLanguageOrthography1Name,
                'OLO1Lowercase': appSet.OLO1Lowercase,
                'OLO1InitialGlottalStops': appSet.OLO1InitialGlottalStops,
                
                'objectLanguageOrthography2': appSet.objectLanguageOrthography2,
                'objectLanguageOrthography2Name': \
                    appSet.objectLanguageOrthography2Name,
                'OLO2Lowercase': appSet.OLO2Lowercase,
                'OLO2InitialGlottalStops': appSet.OLO2InitialGlottalStops,
                
                'objectLanguageOrthography3': appSet.objectLanguageOrthography3,
                'objectLanguageOrthography3Name': \
                    appSet.objectLanguageOrthography3Name,
                'OLO3Lowercase': appSet.OLO3Lowercase,
                'OLO3InitialGlottalStops': appSet.OLO3InitialGlottalStops,
                
                'objectLanguageOrthography4': appSet.objectLanguageOrthography4,
                'objectLanguageOrthography4Name': \
                    appSet.objectLanguageOrthography4Name,
                'OLO4Lowercase': appSet.OLO4Lowercase,
                'OLO4InitialGlottalStops': appSet.OLO4InitialGlottalStops,

                'objectLanguageOrthography5': appSet.objectLanguageOrthography5,
                'objectLanguageOrthography5Name': \
                    appSet.objectLanguageOrthography5Name,
                'OLO5Lowercase': appSet.OLO5Lowercase,
                'OLO5InitialGlottalStops': appSet.OLO5InitialGlottalStops,
                
                'morphemeBreakIsObjectLanguageString': \
                    appSet.morphemeBreakIsObjectLanguageString,

                'orthographicValidation' : appSet.orthographicValidation,
                'narrPhonInventory' : appSet.narrPhonInventory,
                'narrPhonValidation' : appSet.narrPhonValidation,
                'broadPhonInventory' : appSet.broadPhonInventory,
                'broadPhonValidation' : appSet.broadPhonValidation,
                'morphPhonInventory' : appSet.morphPhonInventory,
                'morphDelimiters' : appSet.morphDelimiters,
                'morphPhonValidation' : appSet.morphPhonValidation,
                'punctuation' : appSet.punctuation,
                'grammaticalities' : appSet.grammaticalities
            }

            unrestrictedUsers = json.loads(appSet.unrestrictedUsers)
            for ur in unrestrictedUsers:
                urKey = 'unrestrictedUsers-%s.unrestrictedUser' % ur
                values[urKey] = ur

        else:
            values = {
                'OLO1Lowercase': '',
                'OLO1InitialGlottalStops': '1',
                
                'OLO2Lowercase': '1',
                'OLO2InitialGlottalStops': '1',
                
                'OLO3Lowercase': '1',
                'OLO3InitialGlottalStops': '1',
                
                'OLO4Lowercase': '1',
                'OLO4InitialGlottalStops': '1',

                'OLO5Lowercase': '1',
                'OLO5InitialGlottalStops': '1'
            }

        return renderEditSettings(values)

    @h.authenticate
    @h.authorize(['administrator'])
    @restrict('POST')
    def save(self):
        """Save the changed application settings.

        This action both saves the application settings to the model and updates
        app_globals with the application settings info.

        """

        c.colorsCSSOptions = os.listdir(os.path.join(
            config['pylons.paths']['root'], 'public', 'css', 'colors'
        ))

        schema = AlterSettingsForm()
        values = dict(request.params)
        try:
            self.form_result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            return renderEditSettings(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                )
            )
            return render('/derived/settings/index.html')
        else:
            # Make sure all object language orthographies are mutually
            #  compatible; return the form with a flash message if this is not
            #  the case
            objectLanguageOrthography1 = h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography1'])
            OLO1Lowercase = self.form_result['OLO1Lowercase']
            OLO1InitialGlottalStops = self.form_result['OLO1InitialGlottalStops']
            olo1 = h.Orthography(objectLanguageOrthography1,
                                 lowercase=OLO1Lowercase,
                                 initialGlottalStops=OLO1InitialGlottalStops)

            objectLanguageOrthography2 = h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography2'])
            OLO2Lowercase = self.form_result['OLO2Lowercase']
            OLO2InitialGlottalStops = self.form_result['OLO2InitialGlottalStops']
            olo2 = h.Orthography(objectLanguageOrthography2,
                                 lowercase=OLO2Lowercase,
                                 initialGlottalStops=OLO2InitialGlottalStops)

            objectLanguageOrthography3 = h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography3'])
            OLO3Lowercase = self.form_result['OLO3Lowercase']
            OLO3InitialGlottalStops = self.form_result['OLO3InitialGlottalStops']
            olo3 = h.Orthography(objectLanguageOrthography3,
                                 lowercase=OLO3Lowercase,
                                 initialGlottalStops=OLO3InitialGlottalStops)

            objectLanguageOrthography4 = h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography4'])
            OLO4Lowercase = self.form_result['OLO4Lowercase']
            OLO4InitialGlottalStops = self.form_result['OLO4InitialGlottalStops']
            olo4 = h.Orthography(objectLanguageOrthography4,
                                 lowercase=OLO4Lowercase,
                                 initialGlottalStops=OLO4InitialGlottalStops)

            objectLanguageOrthography5 = h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography5'])
            OLO5Lowercase = self.form_result['OLO5Lowercase']
            OLO5InitialGlottalStops = self.form_result['OLO5InitialGlottalStops']
            olo5 = h.Orthography(objectLanguageOrthography5,
                                 lowercase=OLO5Lowercase,
                                 initialGlottalStops=OLO5InitialGlottalStops)
            olos = [x for x in [olo1, olo2, olo3, olo4, olo5] if x.orthographyAsString]

            if olos:
                try:
                    translators = getOLOrthographyTranslators(olos)
                except h.OrthographyCompatibilityError:
                    return renderEditSettings(
                        values=values,
                        errors={
                            'OLOrthographiesWarning': """You have entered one or
                            more incompatible object language orthographies.
                            Please ensure that all output orthographies have the
                            same structure and that there is a graph in
                            orthography X for each one in orthography Y."""
                            }
                        )

            defaultOrthography = ','.join(list(string.ascii_lowercase))

            appSet = model.ApplicationSettings()

            appSet.objectLanguageName = self.form_result['OLName']
            appSet.objectLanguageId = self.form_result['OLId']

            appSet.metaLanguageName = self.form_result['MLName']
            appSet.metaLanguageId = self.form_result['MLId']
            appSet.metaLanguageOrthography = h.removeAllWhiteSpace(
                self.form_result['MLOrthography']) or defaultOrthography

            appSet.headerImageName = self.form_result['headerImageName']
            appSet.colorsCSS = self.form_result['colorsCSS']

            appSet.storageOrthography = self.form_result['storageOrthography']

            def assignOrthographyIfDefined(orthId, form_result):
                propertyName = 'objectLanguageOrthography' + orthId[-1]
                result = getattr(form_result, propertyName, None)
                if not result:
                    return u'Orthography 1'
                return orthId

            appSet.storageOrthography = assignOrthographyIfDefined(
                self.form_result['storageOrthography'], self.form_result)
            appSet.defaultInputOrthography = assignOrthographyIfDefined(
                self.form_result['defaultInputOrthography'], self.form_result)
            appSet.defaultOutputOrthography = assignOrthographyIfDefined(
                self.form_result['defaultOutputOrthography'], self.form_result)

            appSet.objectLanguageOrthography1Name = self.form_result[
                'objectLanguageOrthography1Name']
            appSet.objectLanguageOrthography1 = h.NFD(h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography1']
            )) or defaultOrthography

            appSet.OLO1Lowercase = self.form_result['OLO1Lowercase']
            appSet.OLO1InitialGlottalStops = self.form_result[
                'OLO1InitialGlottalStops']

            appSet.objectLanguageOrthography2Name = self.form_result[
                'objectLanguageOrthography2Name']
            appSet.objectLanguageOrthography2 = h.NFD(h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography2']))
            appSet.OLO2Lowercase = self.form_result['OLO2Lowercase']
            appSet.OLO2InitialGlottalStops = self.form_result[
                'OLO2InitialGlottalStops']

            appSet.objectLanguageOrthography3Name = self.form_result[
                'objectLanguageOrthography3Name']
            appSet.objectLanguageOrthography3 = h.NFD(h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography3']))
            appSet.OLO3Lowercase = self.form_result['OLO3Lowercase']
            appSet.OLO3InitialGlottalStops = self.form_result[
                'OLO3InitialGlottalStops']

            appSet.objectLanguageOrthography4Name = self.form_result[
                'objectLanguageOrthography4Name']
            appSet.objectLanguageOrthography4 = h.NFD(h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography4']))
            appSet.OLO4Lowercase = self.form_result['OLO4Lowercase']
            appSet.OLO4InitialGlottalStops = self.form_result[
                'OLO4InitialGlottalStops']

            appSet.objectLanguageOrthography5Name = self.form_result[
                'objectLanguageOrthography5Name']
            appSet.objectLanguageOrthography5 = h.NFD(h.removeAllWhiteSpace(
                self.form_result['objectLanguageOrthography5']))
            appSet.OLO5Lowercase = self.form_result['OLO5Lowercase']
            appSet.OLO5InitialGlottalStops = self.form_result[
                'OLO5InitialGlottalStops']

            appSet.morphemeBreakIsObjectLanguageString = self.form_result[
                'morphemeBreakIsObjectLanguageString']

            unrestrictedUsers = self.form_result['unrestrictedUsers']

            appSet.unrestrictedUsers = unicode(
                json.dumps([x['unrestrictedUser'] for x in unrestrictedUsers]))


            appSet.orthographicValidation = self.form_result['orthographicValidation']

            appSet.narrPhonInventory = h.NFD(h.removeAllWhiteSpace(
                                        self.form_result['narrPhonInventory']))
            appSet.narrPhonValidation = self.form_result['narrPhonValidation']

            appSet.broadPhonInventory = h.NFD(h.removeAllWhiteSpace(
                                        self.form_result['broadPhonInventory']))
            appSet.broadPhonValidation = self.form_result['broadPhonValidation']

            appSet.morphPhonInventory = h.NFD(h.removeAllWhiteSpace(
                                        self.form_result['morphPhonInventory']))
            appSet.morphDelimiters = h.NFD(h.removeAllWhiteSpace(
                                        self.form_result['morphDelimiters']))
            appSet.morphPhonValidation = self.form_result['morphPhonValidation']

            appSet.punctuation = h.NFD(h.removeAllWhiteSpace(
                                        self.form_result['punctuation']))
            appSet.grammaticalities = h.NFD(h.removeAllWhiteSpace(
                                        self.form_result['grammaticalities']))

            # Enter the data
            meta.Session.add(appSet)
            meta.Session.commit()

            # Update App_Globals with the newly saved application settings info
            h.applicationSettingsToAppGlobals(app_globals, appSet)

            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(
                controller='settings', action='index')
            return "Moved temporarily"

    @h.authenticate
    def orthography(self):
        """Renders the Orthographies & Inventories page.
        
        Allows users to see if they can correctly enter the graphs of the
        orthographies and to test the orthography conversion.

        """

        c.applicationSettings = meta.Session.query(
            model.ApplicationSettings).order_by(
                desc(model.ApplicationSettings.id
                )
            ).first()

        # Get obj lang orthographies as Inventoriy objects
        c.orthographiesAsInventories = getOrthographiesAsInventories(
                                                        c.applicationSettings)

        # Get metalanguage orthography, and other graph sets as Inventory objects
        getInventoriesAsPropertiesOfC(c.applicationSettings)

        c.orthOptions = [(id, c.orthographiesAsInventories[id][0])
                        for id in c.orthographiesAsInventories]

        return render('/derived/settings/orthography.html')

    @h.authenticate
    def translate(self):
        """Take a string (input) and translate it from the inputOrthography to
        the output orthography.  This action is called asynchronously when the
        'Translate' button is clicked on the /settings/orthography page.

        """

        # Get the GET values
        values = dict(request.params)
        inputOrthography = values['inputOrthography']
        outputOrthography = values['outputOrthography']
        input = h.NFD(values['input'])

        # Create the translator object
        inputOrthography = app_globals.OLOrthographies[inputOrthography][1]
        outputOrthography = app_globals.OLOrthographies[outputOrthography][1]

        try:
            translator = h.OrthographyTranslator(inputOrthography, outputOrthography)
            return translator.translate(input)
        except h.OrthographyCompatibilityError:
            return """Sorry, there is a problem with the selected orthographies.
                They appear to be incompatible."""

    @h.authenticate
    @h.authorize(['administrator'])
    def getmatchinglanguages(self):
        """Get suggestions for languages based on input from user.
        
        This method is used for the Ajax-based auto-suggest feature of the
        settings/edit page.
        
        """
        
        values = dict(request.params)
        uInput = h.unescape(values['input'])
        sourceID = values['sourceID']
        mode = values['mode']
        
        languages_q = meta.Session.query(model.Language)
        languages_q = languages_q.filter(
            getattr(model.Language, mode).op("regexp")('^' + uInput)
        )
        languages_q = languages_q.order_by(getattr(model.Language, mode))
        languages = languages_q.all()[:10]
        
        languages = ['<language>\n\t<id>%s</id>\n\t<name>%s</name>\n</language>' \
            % (x.Id, x.Ref_Name) for x in languages]
        languages = '<languages>\n%s\n</languages>' % '\n'.join(languages)
        response.headers['content-type'] = 'text/xml; charset=utf-8'
        return languages


    def getCharacterCodesAndNames(self):
        input = h.NFD(dict(request.params)['input'])
        response.headers['Content-Type'] = 'application/json'
        return json.dumps(
            (h.getUnicodeCodePoints(input), h.getUnicodeNames(input)))

    def testvalidation(self):
        response.headers['Content-Type'] = 'application/json'
        validationId = dict(request.params)['validationId']

        appSettings = meta.Session.query(model.ApplicationSettings).order_by(
            desc(model.ApplicationSettings.id)).first()

        # Get the appropriate Inventory object for validation from app_globals
        #  These objects are saved by functions/applicationSettingsToAppGlobals
        #  when the application settings are saved
        if validationId == u'testOrthographicValidation':
            inventory = app_globals.orthTranscrInvObj
            fieldName = u'transcription'
        elif validationId == u'testNarrPhonValidation':
            inventory = app_globals.narrPhonInvObj
            fieldName = u'narrowPhoneticTranscription'
        elif validationId == u'testBroadPhonValidation':
            inventory = app_globals.broadPhonInvObj
            fieldName = u'phoneticTranscription'
        elif validationId in [u'testMorphophonValidation',
                              u'testOrthographicMBValidation']:
            inventory = app_globals.morphBreakInvObj
            fieldName = u'morphemeBreak'

        # regex is the regular expression that valid fields will match
        regex = inventory.getRegexValidator()

        # NFDFixes returns True if unicode canonical decompositional
        #  normalization makes the data valid
        def NFDFixes(string, regex):
            string = h.NFD(string)
            patt = re.compile(regex)
            if patt.match(string):
                return True
            return False

        # Count the forms in the db
        formCount = meta.Session.query(model.Form).count()

        # Get the invalid forms using regex and SQLAlchemy
        invalidForms = meta.Session.query(model.Form).filter(not_(
            getattr(model.Form, fieldName).op('regexp')(regex))).all()

        # Build the result to return to the user
        result = {'formCount': formCount, 'invalidCount': len(invalidForms),
                  'NFDFixes': 0, 'invalid': [],
                  'validationInventory': inventory.inputList}

        for f in invalidForms :
            if NFDFixes(getattr(f, fieldName), regex):
                result['NFDFixes'] += 1
            else:
                result['invalid'].append([f.id,
                        h.NFD(getattr(f, fieldName)),
                        h.getUnicodeCodePoints(h.NFD(getattr(f, fieldName)))])

        return json.dumps(result)
