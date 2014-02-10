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
import time

try:
    import json
except ImportError:
    import simplejson as json

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons import config
from pylons.controllers.util import abort, redirect, forward
from pylons.decorators import validate
from pylons.decorators.rest import restrict
from pylons.decorators import jsonify

import webhelpers.paginate as paginate

from formencode.schema import Schema
from formencode.validators import Invalid, FancyValidator
from formencode.validators import Int, DateConverter, UnicodeString, OneOf, Regex
from formencode import variabledecode
from formencode import htmlfill, All
from formencode.foreach import ForEach
from formencode.api import NoDefault

from sqlalchemy.sql import or_, desc

from paste.fileapp import FileApp

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

from sqlalchemy import desc

log = logging.getLogger(__name__)


################################################################################
# Inventory-based Transcription Validation Logic
################################################################################

class ValidOrthographicTranscription(UnicodeString):
    """Validates orthographic transcription input.  If orthographic
    transcription validation is set to 'Error' in application settings, this
    validator will forbid orthographic transcriptions that are not constructable
    using the storage orthography and the specified punctuation.  A validation
    setting of 'Warning' or 'Error' will cause validate_transcription to
    call validate_python directly and asynchronously return a warning message.

    """

    messages = {u'invalid_transcription':
                u'''Error: the orthographic transcription you have entered is
not valid. Only graphemes from the input orthography, punctuation characters and
the space character are permitted.  See the Application Settings and
Orthographies & Inventories pages for more details.''',
                u'invalid_transcription_warning':
                u'''Warning: the orthographic transcription you have entered
is not constructable using only the input orthography, punctuation characters
and the space character.'''}

    def validate_python(self, value, state, validationSetting=None):
        tr = h.inputToStorageTranslate(unicode(h.removeWhiteSpace(h.NFD(value))))
        if not formIsForeignWord(state.full_dict) and \
            not orthTranscrIsValid(tr, validationSetting):
            raise Invalid(self.message(getValMsgKey(validationSetting), state),
                          value, state)

class ValidBroadPhoneticTranscription(UnicodeString):
    """Validates broad phonetic transcription input.  If broad phonetic
    transcription validation is set to 'Error' in application settings, this
    validator will forbid broad phonetic transcriptions that are not
    constructable using the broad phonetic inventory.  A validation
    setting of 'Warning' or 'Error' will cause validate_transcription to
    call validate_python directly and asynchronously return a warning message.

    """

    messages = {u'invalid_transcription':
                u'''Error: the broad phonetic transcription you have entered is
not valid.  Only graphemes from the broad phonetic inventory and the space
character are permitted.  See the Application Settings and Orthographies &
Inventories pages for more details.''',
                u'invalid_transcription_warning':
                u'''Warning: the broad phonetic transcription you have entered
is not constructable using only the broad phonetic inventory and the space
character.'''}

    def validate_python(self, value, state, validationSetting=None):
        bptr = h.removeWhiteSpace(h.NFD(value))
        if not formIsForeignWord(state.full_dict) and \
            not broadPhonTranscrIsValid(bptr, validationSetting):
            raise Invalid(self.message(getValMsgKey(validationSetting), state),
                          value, state)


class ValidNarrowPhoneticTranscription(UnicodeString):
    """Validates narrow phonetic transcription input.  If narrow phonetic
    transcription validation is set to 'Error' in application settings, this
    validator will forbid narrow phonetic transcriptions that are not
    constructable using the narrow phonetic inventory.  A validation
    setting of 'Warning' or 'Error' will cause validate_transcription to
    call validate_python directly and asynchronously return a warning message.

    """

    messages = {u'invalid_transcription':
                u'''Error: the narrow phonetic transcription you have entered is
not valid.  Only graphemes from the narrow phonetic inventory and the space
character are permitted.  See the Application Settings and Orthographies &
Inventories pages for more details.''',
                u'invalid_transcription_warning':
                u'''Warning: the narrow phonetic transcription you have entered
is not constructable using only the narrow phonetic inventory and the space
character.'''}

    def validate_python(self, value, state, validationSetting=None):
        nptr = h.removeWhiteSpace(h.NFD(value))
        if not formIsForeignWord(state.full_dict) and \
            not narrPhonTranscrIsValid(nptr, validationSetting):
            raise Invalid(self.message(getValMsgKey(validationSetting), state),
                          value, state)


class ValidMorphemeBreakTranscription(UnicodeString):
    """Validates morpheme break input.  If morphophonemic segmentation
    validation is set to 'Error' in application settings, this validator will
    forbid morpheme break transcriptions that are not constructable using the
    relevant grapheme inventory (i.e., either the storage orthography or the
    morphophonemic segmentation inventory) and the specified morpheme
    delimiters.  A validation setting of 'Warning' or 'Error' will cause
    validate_transcription to call validate_python directly and asynchronously
    return a warning message.

    """

    inv = u'morphophonemic segmentation inventory'
    if app_globals.morphemeBreakIsObjectLanguageString == u'yes':
        inv = u'input orthography'

    messages = {u'invalid_transcription':
                u'''Error: the morpheme segmentation you have entered is not
valid. Only graphemes from the %s, morpheme delimiters and the space character
are permitted.  See the Application Settings and Orthographies & Inventories
pages for more details.''' % inv,
                u'invalid_transcription_warning':
                u'''Warning: the morpheme segmentation you have entered is not
constructable using only the %s, punctuation characters and the space
character.''' % inv}

    def validate_python(self, value, state, validationSetting=None):
        mb = h.removeWhiteSpace(h.NFD(value))
        if app_globals.morphemeBreakIsObjectLanguageString == u'yes':
            mb = h.inputToStorageTranslate(mb)
        if not formIsForeignWord(state.full_dict) and \
            not morphBreakTranscrIsValid(mb, validationSetting):
            raise Invalid(self.message(getValMsgKey(validationSetting), state),
                          value, state)


def formIsForeignWord(formDict):
    """Returns False if the form being entered is tagged as a foreign
    word, else True.

    """

    keywordIds = [int(k['keyword'])
                for k in formDict.get('keywords', [])]
    if keywordIds and [i for i in h.getForeignWordKeywordIds()
                     if i in keywordIds]:
        return True
    return False


def getValMsgKey(validationSetting):
    if validationSetting:
        return u'invalid_transcription_warning'
    return u'invalid_transcription'


def orthTranscrIsValid(transcription, validationSetting=None):
    if app_globals.orthographicValidation == u'Error' or \
                                    validationSetting in [u'Error', u'Warning']:
        return app_globals.orthTranscrInvObj.stringIsValid(transcription)
    return True

def broadPhonTranscrIsValid(transcription, validationSetting=None):
    if app_globals.broadPhonValidation == u'Error' or \
                                    validationSetting in [u'Error', u'Warning']:
        return app_globals.broadPhonInvObj.stringIsValid(transcription)
    return True

def narrPhonTranscrIsValid(transcription, validationSetting=None):
    if app_globals.narrPhonValidation == u'Error' or \
                                    validationSetting in [u'Error', u'Warning']:
        return app_globals.narrPhonInvObj.stringIsValid(transcription)
    return True

def morphBreakTranscrIsValid(transcription, validationSetting=None):
    if app_globals.morphPhonValidation == u'Error' or \
                                    validationSetting in [u'Error', u'Warning']:
        return app_globals.morphBreakInvObj.stringIsValid(transcription)
    return True

################################################################################


class AtLeastOneGloss(FancyValidator):
    """Custom validator.  Ensures that at least one gloss field contains data.
    This is used in the RIA version of the OLD.

    """

    messages = {'one_gloss': 'Please enter one or more glosses'}
    def validate_python(self, value, state):
        glosses = [v['gloss'] for v in value if v['gloss'].strip()]
        if not glosses:
            raise Invalid(self.message("one_gloss", state), value, state)


class FirstGlossNotEmpty(FancyValidator):
    """Custom validator.  Ensures that the first gloss field, 'gloss-0.text',
    has some content.
    
    """
    
    messages = {'one_gloss': 'Please enter a gloss in the first gloss field'}
    def validate_python(self, value, state):
        if value[0]['gloss'] == '':
            raise Invalid(self.message("one_gloss", state), value, state)


class Keyword(Schema):
    """Keyword validator ensures that keywords are unicode strings."""
    keyword = UnicodeString()


class NewFormForm(Schema):
    """NewFormForm is a Schema for validating the data entered at the Add Form
    page.
    
    """

    allow_extra_fields = True
    filter_extra_fields = True
    pre_validators = [variabledecode.NestedVariables()]
    transcription = ValidOrthographicTranscription(not_empty=True)
    phoneticTranscription = ValidBroadPhoneticTranscription()
    narrowPhoneticTranscription = ValidNarrowPhoneticTranscription()
    morphemeBreak = ValidMorphemeBreakTranscription()
    grammaticality = UnicodeString()
    morphemeGloss = UnicodeString()
    glosses = FirstGlossNotEmpty()
    comments = UnicodeString()
    speakerComments = UnicodeString()
    elicitationMethod = UnicodeString()
    keywords = ForEach(Keyword())
    syntacticCategory = UnicodeString()
    speaker = UnicodeString()
    elicitor = UnicodeString()
    verifier = UnicodeString()
    source = UnicodeString()
    dateElicited = DateConverter(month_style='mm/dd/yyyy')

class NewFormFormDM(NewFormForm):
    dateElicited = DateConverter(month_style='dd/mm/yyyy')

class NewFormAjaxForm(NewFormForm):
    glosses = AtLeastOneGloss()
    keywords = ForEach(UnicodeString())

class UpdateFormForm(NewFormForm):
    ID = UnicodeString()

class UpdateFormFormDM(UpdateFormForm):
    dateElicited = DateConverter(month_style='dd/mm/yyyy')

class RestrictorStruct(Schema):
    location = UnicodeString()
    containsNot = UnicodeString()
    allAnyOf = UnicodeString
    options = ForEach(UnicodeString())

class DateRestrictorStruct(Schema):
    location = UnicodeString()
    relation = UnicodeString()
    date = DateConverter(month_style='mm/dd/yyyy')

class IntegerRestrictorStruct(Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    location = UnicodeString()
    relation = UnicodeString()
    integer = Regex(r'^ *[0-9]+(\.[0-9]+)? *$')

class EmptyRestrictorStruct(Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    location = UnicodeString()
    relation = UnicodeString()

class SearchFormForm(Schema):
    """SearchForm is a Schema for validating the search terms entered at the
    Search Forms page.

    """

    allow_extra_fields = True
    filter_extra_fields = True
    pre_validators = [variabledecode.NestedVariables()]
    searchTerm1 = UnicodeString()
    searchType1 = UnicodeString()
    searchLocation1 = UnicodeString()
    searchTerm2 = UnicodeString()
    searchType2 = UnicodeString()
    searchLocation2 = UnicodeString()
    andOrNot = UnicodeString()
    restrictors = ForEach(RestrictorStruct())
    dateRestrictors = ForEach(DateRestrictorStruct())
    integerRestrictors = ForEach(IntegerRestrictorStruct())
    emptyRestrictors = ForEach(EmptyRestrictorStruct())
    orderByColumn = UnicodeString()
    orderByDirection = UnicodeString()
    limit = Regex(r'^ *[0-9]+ *$')

class AssociateFormFileForm(Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    fileID = Regex(r'^ *[1-9]+[0-9]* *( *, *[1-9]+[0-9]* *)*$', not_empty=True)

def renderAddForm(values=None, errors=None, addUpdate='add'):
    """Function is called by both the add and update actions to create the
    Add Form and Update Form html forms.  The create and save actions can also
    call this function if any errors are present in the input.
    
    """

    c.transcriptionKeyboardTable = h.getKeyboardTable('transcription')
    c.morphemeBreakKeyboardTable = h.getKeyboardTable('morphemeBreak')

    # if addUpdate is set to 'update', render update.html instead of add.html
    html = render('/derived/form/add.html')
    if addUpdate == 'update':
        html = render('/derived/form/update.html')

    # Replace 'glosses' with 'glosses-0.gloss' in errors dict
    # so that error messages are put in the proper place
    if errors and 'glosses' in errors:
        errors['glosses-0.gloss'] = errors['glosses']
        del errors['glosses']

    return htmlfill.render(html, defaults=values, errors=errors)


def getFormAttributes(form, result, createOrSave):
    """Given a Form object and a result dictionary populated by
    user-entered data, this action populates the appropriate attributes with the
    appropriate values.  
    
    This function is called by both the create() and save() actions.
    
    Note: the values entered into the orthographic transcription and
    morphemeBreak fields are converted from the input orthography to the storage
    orthography using the functions.inputToStorageTranslate function.
    <orth>-prefixed and </orth>-suffixed substrings of the values entered into the
    comments and speakerComments fields are converted from the input orthography
    to the storage orthography using the functions.inputToStorageTranslateOLOnly
    function.  See the lib/functions and lib/orthography modules for details.

    """

    # Textual Data
    form.transcription = h.inputToStorageTranslate(
        unicode(h.removeWhiteSpace(h.NFD(result['transcription']))))

    form.phoneticTranscription = h.removeWhiteSpace(h.NFD(
        result['phoneticTranscription']))

    form.narrowPhoneticTranscription = h.removeWhiteSpace(h.NFD(
        result['narrowPhoneticTranscription']))

    form.morphemeBreak = h.inputToStorageTranslate(
        h.removeWhiteSpace(h.NFD(result['morphemeBreak'])), True)

    form.morphemeGloss = h.removeWhiteSpace(h.NFD(result['morphemeGloss']))
    form.comments = h.inputToStorageTranslateOLOnly(h.NFD(result['comments']))
    form.speakerComments = h.inputToStorageTranslateOLOnly(
        h.NFD(result['speakerComments']))
    form.grammaticality = result['grammaticality']
    form.dateElicited = result['dateElicited']

    # One-to-Many Data: Glosses
    # First check if the user has made any changes to the glosses.
    # If there are any changes, just delete all glosses and replace with new
    #  ones.  (Note: this will result in the deletion of a gloss and the
    #  recreation of an identical one with a different index.  There may be a
    #  "better" way of doing this, but this way is simple...
    glossesToAdd = [[gloss['gloss'], gloss['grammaticality']] for gloss in \
        result['glosses'] if gloss['gloss']]
    glossesWeHave = [[gloss.gloss, gloss.glossGrammaticality] for gloss in \
        form.glosses]
    if glossesToAdd != glossesWeHave:
        form.glosses = []
        for gloss in glossesToAdd:
            glossObject = model.Gloss()
            glossObject.gloss = h.removeWhiteSpace(h.NFD(gloss[0]))
            glossObject.glossGrammaticality = gloss[1]
            form.glosses.append(glossObject)

    # Many-to-One Data

    if result['elicitationMethod']:
        form.elicitationMethod = meta.Session.query(
            model.ElicitationMethod).get(int(result['elicitationMethod']))
    else:
        form.elicitationMethod = None
    
    if result['syntacticCategory']:
        form.syntacticCategory = meta.Session.query(
            model.SyntacticCategory).get(int(result['syntacticCategory']))
    else:
        form.syntacticCategory = None
    
    if result['source']:
        form.source = meta.Session.query(model.Source).get(
            int(result['source']))
    else:
        form.source = None
    
    if result['elicitor']:
        form.elicitor = meta.Session.query(model.User).get(
            int(result['elicitor']))
    else:
        form.elicitor = None
    
    if result['verifier']:
        form.verifier = meta.Session.query(model.User).get(
            int(result['verifier']))
    else:
        form.verifier = None
    
    if result['speaker']:
        form.speaker = meta.Session.query(model.Speaker).get(
            int(result['speaker']))
    else:
        form.speaker = None
        
    # Many-to-Many Data: Keywords
    # First check if the user has made any changes to the keywords.
    # If there are any changes, just delete all keywords and replace with new
    #  ones
    try:
        keywordsToAdd = [int(kw['keyword']) for kw in result['keywords']]
    except TypeError:
        # In the RIA version of the OLD, keyword entry is via a multi-select
        #  and, therefore, keywords is a list, not a dict
        keywordsToAdd = [int(kw) for kw in result['keywords']]
    keywordsWeHave = [kw.id for kw in form.keywords]
    if keywordsToAdd != keywordsWeHave:
        form.keywords = []
        for keyword in keywordsToAdd:
            keywordObject = meta.Session.query(model.Keyword).get(keyword)
            form.keywords.append(keywordObject)

    # OLD-generated Data
    now = datetime.datetime.utcnow()
    if createOrSave == 'create':
        form.datetimeEntered = now
    form.datetimeModified = now

    # Add the Enterer as the current user, if we are creating.  If we are saving,
    #  leave the enterer as it is
    if createOrSave == 'create':
        form.enterer = meta.Session.query(model.User).get(
            int(session['user_id']))

    # Create the morphemeBreakIDs and morphemeGlossIDs attributes;
    #  these are lists of lists representing words, containing lists of Form IDs
    #  for their matching morphemes, e.g., [[[1], [2]], [[3], [2]]];
    #  We add the form first to get an ID so that monomorphemic Forms can be self-referential
    meta.Session.add(form)
    form.getMorphemeIDLists(meta, model)

    # Save the form just entered to the session as the lastFormEntered so that
    #  we can implement the defaultMetadataFromPreviousForm setting.
    session['lastFormEntered'] = form
    session.save()

    return form


def backupForm(form):
    """When a Form is being updated or deleted, it is first added to the
    formbackup table.
    
    """
    
    # transform nested data structures to JSON for storage in a 
    #  relational database unicode text column    
    formBackup = model.FormBackup()
    user = unicode(json.dumps({
        'id': session['user_id'],
        'firstName': session['user_firstName'],
        'lastName': session['user_lastName']
    }))
    formBackup.toJSON(form, user)
    meta.Session.add(formBackup)


def rememberPreviousSearches(searchToRemember):
    """Function stores the last 10 searches in the session.
    
    These searches are stored as a list of dictionaries; the same dictionaries
    outputed by the query action.
    
    """
    
    if 'previousSearches' in session:
        previousSearches = session['previousSearches']
        previousSearches.reverse()
        previousSearches.append(searchToRemember)
        previousSearches.reverse()
        if len(previousSearches) > app_globals.maxNoPreviousSearches:
            del previousSearches[-1]
        session['previousSearches'] = previousSearches
    else:
        session['previousSearches'] = [searchToRemember]
    session.save()


class DictStack(dict):
    """A subclass of dict that allows only maxItems keys; when additional keys
    are added, the oldest keys are deleted to make room.

    """

    def __init__(self, maxItems=100):
        self.keysAdded = []
        self.maxItems = maxItems
        dict.__init__(self)

    def __setitem__(self, key, val):
        while len(self.keys()) >= self.maxItems:
            del self[self.keysAdded[0]]
            self.keysAdded = self.keysAdded[1:]
        self.keysAdded.append(key)
        dict.__setitem__(self, key, val)


class JSONOLDEncoder(json.JSONEncoder):
    """Permits the jsonification of OLD class instances via

        >>> jsonString = json.dumps(obj, cls=JSONOLDEncoder)

    Note: support for additional OLD classes will be implemented as needed ...

    """

    def default(self, obj):
        try:
            return json.JSONEncoder.default(self, obj)
        except TypeError:
            if isinstance(obj, (datetime.datetime, datetime.date)):
                return obj.isoformat()
            elif isinstance(obj, model.Form):
                result = obj.__dict__
                result.update({
                    'enterer': obj.enterer,
                    'speaker': obj.speaker,
                    'elicitationMethod': obj.elicitationMethod,
                    'syntacticCategory': obj.syntacticCategory,
                    'elicitor': obj.elicitor,
                    'enterer': obj.enterer,
                    'verifier': obj.verifier,
                    'source': obj.source,
                    'glosses': obj.glosses,
                    'files': obj.files,
                    'collections': obj.collections,
                    'keywords': obj.keywords,
                    'morphemeBreakIDs': json.loads(obj.morphemeBreakIDs),
                    'morphemeGlossIDs': json.loads(obj.morphemeGlossIDs)
                })
                return result
            elif isinstance(obj, (model.Gloss, model.ElicitationMethod,
                    model.Keyword, model.SyntacticCategory,
                    model.Speaker, model.User, model.Source, model.File)):
                return obj.__dict__
            else:
                return None


def updateContextWithPhoneticFieldDisplaySettings(values=None):
    """Sets two properties of global c which determine whether the phonetic
    transcription fields are displayed in the add and update interfaces.  User-
    specific settings are the first determinant.  However, the presence of a
    non-empty string in the relevant field/comment will cause the field to be
    displayed, overriding any contrary user setting.

    """


    c.displayNarrowPhoneticTranscriptionField = session['userSettings'].get(
        'displayNarrowPhoneticTranscriptionField', False)
    c.displayBroadPhoneticTranscriptionField = session['userSettings'].get(
        'displayBroadPhoneticTranscriptionField', False)

    if values:
        if values.get('narrowPhoneticTranscription'):
            c.displayNarrowPhoneticTranscriptionField = True
        if values.get('phoneticTranscription'):
            c.displayBroadPhoneticTranscriptionField = True


def getRestrictedFormErrorPage(form):
    """Return the error page to display when a form is restricted."""
    c.code = 403
    c.message = 'Sorry, you do not have access to form %d' % form.id
    return render('/derived/error/document.html')


class FormController(BaseController):
    """Form Controller contains actions about OLD Forms.  Authorization and
    authentication are implemented by the helper decorators authenticate and
    authorize which can be found in lib/auth.py.
    
    """

    @h.authenticate
    def browse(self):
        """Browse through all Forms in the system.
        
        """

        form_q = meta.Session.query(model.Form).order_by(desc(
            model.Form.id)).limit(1000)

        form_items_per_page = app_globals.form_items_per_page
        try:
            form_items_per_page = {'tabular': 50, 'IGT': 10}[
                session['defaultFormView']]
        except KeyError:
            pass

        c.paginator = paginate.Page(
            form_q,
            page=int(request.params.get('page', 1)),
            items_per_page = form_items_per_page
        )
        c.browsing = True
        
        return render('/derived/form/results.html')

    # Custom decoder & encoder for json
    # http://stackoverflow.com/questions/2343535/easiest-way-to-serialize-a-simple-class-object-with-simplejson
    
    # Python classes, instances and __dict__, etc.
    # http://www.cafepy.com/article/python_attributes_and_methods/python_attributes_and_methods.html
    
    # Understanding Pylons decorators
    # http://www.mail-archive.com/pylons-discuss@googlegroups.com/msg13311.html
    
    # JavaScript prototypal inheritance
    # http://laktek.com/2011/02/02/understanding-prototypical-inheritance-in-javascript/

    #@h.authenticate_ajax
    def browse_ajax(self):
        """Browse through all Forms in the system.  This method returns a
        jsonified paginator object, i.e., a list of items (i.e., Forms) as well
        as a handful of properties useful for pagination: first_item,
        first_page, item_count, items_per_page, last_item, last_page, next_page,
        page, page_count, previous_page.

        """

        response.headers['Content-Type'] = 'application/json'
        query = meta.Session.query(model.Form).order_by(desc(model.Form.id))
        items_per_page = app_globals.form_items_per_page

        # The paginate.Page object
        #  provide an item_count value to speed things up (the downside is that
        #  browsing would not, then, keep pace with newly entered data -- we
        #  could keep track of modifications to the form table via datetime ...)
        paginator = paginate.Page(
            query,
            page = int(request.params.get('page', 1)),
            items_per_page = int(request.params.get(
                'items_per_page', items_per_page)),
        )

        result = json.dumps(paginator.__dict__, cls=JSONOLDEncoder)
        return result

    @h.authenticate
    def view(self, id):
        """View a BLD Form.  Requires a Form ID as input.
        
        """

        if id is None:
            abort(404)
        
        # Redirect to results action
        redirect(url(controller='form', action='results', id=id))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Display HTML form for adding a new BLD Form. HTML form calls create
        action.
        
        """
        
        # Make extra glosses fields invisible by default
        c.viewExtraGlossesFields = False

        updateContextWithPhoneticFieldDisplaySettings()

        values = {}

        if 'user_defaultMetadataFromPreviousForm' in session and \
        session['user_defaultMetadataFromPreviousForm'] and \
        'lastFormEntered' in session:
            lastFormEntered = session['lastFormEntered']

            values = {
                'syntacticCategory': lastFormEntered.syntacticcategory_id,
                'speaker': lastFormEntered.speaker_id,
                'elicitor': lastFormEntered.elicitor_id,
                'verifier': lastFormEntered.verifier_id,
                'source': lastFormEntered.source_id,
                'dateElicited': lastFormEntered.dateElicited 
            }

            if lastFormEntered.dateElicited:
                dateFormat = session.get('userSettings').get('dateFormat')
                if dateFormat == 'DD/MM/YYYY':
                    values['dateElicited'] = \
                    lastFormEntered.dateElicited.strftime('%d/%m/%Y')
                else:
                    values['dateElicited'] = \
                    lastFormEntered.dateElicited.strftime('%m/%d/%Y')

        return renderAddForm(values)

    @h.authenticate
    def get_keyboard_grapheme_list(self):
        """Return the appropriate list of graphemes for the keyboard for
        fieldName.

        """

        response.headers['Content-Type'] = 'application/json'
        fieldName = dict(request.params)['fieldName']
        return json.dumps(h.getInventoryListForKeyboard(fieldName))

    @h.authenticate
    def validate_transcription(self):
        """If transcription field fieldName has validation set to 'Error' or
        'Warning', return the error message that the appropriate validator would
        return if validation were set to 'Error' and the form were submitted.

        """

        response.headers['Content-Type'] = 'application/json'

        values = dict(request.params)
        fieldName = values['fieldName']

        # Get validator object and validation setting based on fieldName
        validator, validationSetting = {
            u'transcription': (ValidOrthographicTranscription(),
                                app_globals.orthographicValidation),
            u'morphemeBreak': (ValidMorphemeBreakTranscription(),
                                app_globals.morphPhonValidation),
            u'phoneticTranscription': (ValidBroadPhoneticTranscription(),
                                app_globals.broadPhonValidation),
            u'narrowPhoneticTranscription': (ValidNarrowPhoneticTranscription(),
                                app_globals.narrPhonValidation)
        }[fieldName]

        # Only Error and Warning validation settings can return warnings
        if validationSetting not in [u'Error', u'Warning']:
            return json.dumps({'valid': True})

        # Create a fake state object to pass to the formencode validator
        class State(object):
            pass
        state = State()
        state.full_dict = values

        # Try to validate the field and return JSON-ified errors if necessary
        try:
            validator.validate_python(values[fieldName], state,
                                      validationSetting=validationSetting)
            result = {'valid': True}
        except Invalid, e:
            result = {'valid': False, 'errors': e.unpack_errors()}

        return json.dumps(result)

    @h.authenticate
    def search(self, values=None, errors=None):
        """Display HTML form for searching for BLD Forms.  The HTML form calls
        the query action.
        
        """
        
        # if no user-entered defaults are set, make gloss the default for
        #  searchLocation2
        if not values:
            values = {'searchLocation2': u'gloss'}
            values['orderByColumn'] = 'id'

        # By default, the additional search restrictors are hidden
        c.viewRestrictors = False

        # check if this is a redirect from the searchprevious action
        if 'searchToRepeat' in session:
            values = session['searchToRepeat']['values']
            result = session['searchToRepeat']['result']
            del session['searchToRepeat']
            session['flash'] = u'This is a previous search'
            session.save()
            # If the previous search had restrictors specified, make the
            #  restrictor fields visible
            restrictors = [restrictor for restrictor in result['restrictors']
                           if restrictor['options']]
            dateRestrictors = [restrictor for restrictor in
                               result['dateRestrictors'] if restrictor['date']]
            if restrictors or dateRestrictors:
                c.viewRestrictors = True

        # Get today in MM/DD/YYYY form
        c.today = datetime.date.today().strftime('%m/%d/%Y')
        html = render('/derived/form/search.html')
        
        return htmlfill.render(html, defaults=values, errors=errors)

    @h.authenticate
    def previoussearches(self):
        """Display this user's last 10 searches so that any can be repeated
        and/or altered.
        
        """
        
        c.previousSearches = []
        if 'previousSearches' in session:
            c.previousSearches = session['previousSearches']
        c.maxNoPreviousSearches = app_globals.maxNoPreviousSearches
        return render('/derived/form/previoussearches.html')

    @h.authenticate
    def searchprevious(self, id):
        """Here id represents the index of the search to be repeated from
        the list of previous searches stored in session['previousSearches'].
        If the id/index does not correspond to a stored search, the system
        simply redirects to the (blank) search action.
        
        """
        
        if id and len(session['previousSearches']) >= int(id):
            session['searchToRepeat'] = session['previousSearches'][int(id)]
            session.save()
        redirect(url(controller='form', action='search', id=None))

    #@h.authenticate_ajax
    @jsonify
    def get_form_options_ajax(self):
        """Return a dictionary containing the global data required to populate
        the select inputs of the add and update Form pages.

        """

        return {
            'grammaticalities': app_globals.grammaticalities,
            'elicitationMethods': [[u'', u'']] + app_globals.elicitationMethods,
            'keywords': app_globals.keywords,
            'categories': [[u'', u'']] + app_globals.syncats,
            'speakers': [[u'', u'']] + app_globals.speakers,
            'users': [[u'', u'']] + app_globals.users,
            'sources': [[u'', u'']] + app_globals.sources
        }

    #@h.authenticate_ajax
    @restrict('POST')
    def add_ajax(self):
        #time.sleep(5)
        schema = NewFormAjaxForm()
        values = variabledecode.variable_decode(request.params)
        try:
            result = schema.to_python(values)
        except Invalid, e:
            result = {'valid': False, 'errors': e.unpack_errors()}
        else:
            # Create a new Form object
            form = model.Form()
            form = getFormAttributes(form, result, 'create')
            # Enter it in the database
            meta.Session.add(form)
            meta.Session.commit()
            formCount = h.getFormCount()
            app_globals.formCount += 1
            result = {'valid': True, 'form': form}

        response.headers['Content-Type'] = 'application/json'
        result = json.dumps(result, cls=JSONOLDEncoder)
        return result

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def create(self):
        """Enter BLD Form data into the database.  This is the action referenced
        by the html form rendered by the add action.
        
        """

        dateFormat = session.get('userSettings').get('dateFormat')
        if dateFormat == 'DD/MM/YYYY':
            schema = NewFormFormDM()
        else:
            schema = NewFormForm()

        values = dict(request.params)

        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            updateContextWithPhoneticFieldDisplaySettings(values)
            return renderAddForm(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                )
            )
        else:
            # Create a new Form object and populate its attributes with the results
            form = model.Form()
            form = getFormAttributes(form, result, 'create')
            # Enter the data
            meta.Session.add(form)
            meta.Session.commit()

            formCount = h.getFormCount()
            app_globals.formCount += 1

            # Foreign word forms will change the inventory-based validation
            h.updateInventoryObjsIfFormIsForeignWord(form)

            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(controller='form', action='view',
                                               id=form.id)
            return "Moved temporarily"

    @h.authenticate
    @restrict('POST')
    def query(self):
        """Query action validates the search input values; if valid, query
        stores the search input values in the session and redirects to results;
        if invalid, query redirect to search action (though I don't think it's
        possible to enter an invalid query...).  Query is the action referenced
        by the html form rendered by the search action.

        """

        schema = SearchFormForm()
        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            return self.search(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                )
            )
        else:
            # put result into session as formSearchValues
            session['formSearchValues'] = result

            # Add timestamp to result
            result['timeSearched'] = datetime.datetime.utcnow()

            # NFD normalize values and result
            values = h.NFDDict(values)
            result = h.NFDDict(result)

            # Put both the result and the values (the unmodified user-entered
            #  search terms) into the session so that they can be saved for
            #  "Previous Search" functionality.
            searchToRemember = {'result': result, 'values': values}
            rememberPreviousSearches(searchToRemember)
            session.save()

            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(controller='form',
                                               action='results')
            return "Moved temporarily"

    @h.authenticate
    def results(self, id=None):
        """Results action uses the filterSearchQuery helper function to filter
        the query based on the values entered by the user in the search form.

        An optional id argument can be provided in the URL (usually because of a 
        redirect from the view() action.  This id can be a single digit or 
        multiple comma-separated digits.

        """

        if id:
            patt = re.compile('^[0-9 ]+$')
            IDs = [int(ID.strip().replace(' ', '')) for ID in id.split(',')
                   if patt.match(ID)]
            if not IDs:
                IDs = [0]
            form_q = meta.Session.query(model.Form).filter(
                model.Form.id.in_(IDs))
        else:
            if 'formSearchValues' in session:
                result = session['formSearchValues']
                form_q = meta.Session.query(model.Form)
                form_q = h.filterSearchQuery(result, form_q, 'Form')
            else:
                form_q = meta.Session.query(model.Form)

        try:
            limit = session.get('formSearchValues').get('limit')
        except AttributeError:
            limit = None

        if limit:
            form_q = form_q.limit(int(limit))
        else:
            # Default is to limit query to 1000 results max
            form_q = form_q.limit(1000)

        forms = form_q.all()

        form_items_per_page = app_globals.form_items_per_page
        try:
            form_items_per_page = {'tabular': 50, 'IGT': 10}[
                session['defaultFormView']]
        except KeyError:
            pass

        c.paginator = paginate.Page(
            form_q,
            page=int(request.params.get('page', 1)),
            items_per_page = form_items_per_page
        )

        return render('/derived/form/results.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def update(self, id=None):
        """Displays an HTML form for updating a BLD Form.  The HTML form calls
        the save action.
        
        """

        if id is None:
            abort(404)
        form_q = meta.Session.query(model.Form)
        form = form_q.filter_by(id=id).first()
        if form is None:
            abort(404)
        c.formID = form.id

        # If user is not authorized to access this form, let them know.
        if not h.userIsAuthorizedToAccessForm(session['user'], form):
            return getRestrictedFormErrorPage(form)


        values = {
            'ID': form.id,
            'transcription': h.storageToInputTranslate(form.transcription),
            'phoneticTranscription': form.phoneticTranscription,
            'narrowPhoneticTranscription': form.narrowPhoneticTranscription,
            'grammaticality': form.grammaticality,
            'morphemeBreak': h.storageToInputTranslate(form.morphemeBreak, True),
            'morphemeGloss': form.morphemeGloss,
            'comments': h.storageToInputTranslateOLOnly(form.comments),
            'speakerComments': h.storageToInputTranslateOLOnly(form.speakerComments),
            'elicitationMethod': form.elicitationmethod_id,
            'syntacticCategory': form.syntacticcategory_id,
            'speaker': form.speaker_id,
            'elicitor': form.elicitor_id,
            'verifier': form.verifier_id,
            'source': form.source_id,
            'dateElicited': form.dateElicited
        }

        # re-format the keys and values of the values dict into a flat structure
        #  so that htmlfill can fill in the form properly. 
        if form.dateElicited:
            dateFormat = session.get('userSettings').get('dateFormat')
            if dateFormat == 'DD/MM/YYYY':
                values['dateElicited'] = form.dateElicited.strftime('%d/%m/%Y')
            else:
                values['dateElicited'] = form.dateElicited.strftime('%m/%d/%Y')

        for i in range(len(form.glosses)):
            gKey = 'glosses-%s.gloss' % i
            ggKey = 'glosses-%s.grammaticality' % i
            iKey = 'glosses-%s.ID' % i
            values[gKey] = form.glosses[i].gloss   
            values[ggKey] = form.glosses[i].glossGrammaticality
            values[iKey] = form.glosses[i].id
        for keyword in form.keywords:
            kKey = 'keywords-%s.keyword' % keyword.id
            values[kKey] = keyword.id

        # Make extra glosses fields visible if there are data in them
        c.viewExtraGlossesFields = False
        if 'glosses-1.ID' in values or 'glosses-2.ID' in values or \
            'glosses-3.ID' in values:
            c.viewExtraGlossesFields = True

        # Make phonetic transcription fields visible, if needed
        updateContextWithPhoneticFieldDisplaySettings(values)

        return renderAddForm(values, None, 'update')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def save(self):
        """Updates an existing Form.  This is the action referenced by the html
        form rendered by the update action.

        """

        dateFormat = session.get('userSettings').get('dateFormat')
        if dateFormat == 'DD/MM/YYYY':
            schema = UpdateFormFormDM()
        else:
            schema = UpdateFormForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            c.id = values['ID']
            c.formID = c.id

            # Make extra glosses fields visible if there are data in them
            c.viewExtraGlossesFields = False
            if 'glosses-1.ID' in values or 'glosses-2.ID' in values or \
                'glosses-3.ID' in values:
                c.viewExtraGlossesFields = True

            # Make phonetic transcription fields visible, if needed
            updateContextWithPhoneticFieldDisplaySettings(values)

            return renderAddForm(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                ),
                addUpdate='update'
            )
        else:

            # Get the Form object with ID from hidden field in update.html
            form_q = meta.Session.query(model.Form)
            form = form_q.filter_by(id=result['ID']).first()

            # Backup the form to the formbackup table
            backupForm(form)

            # Populate the Form's attributes with the data from the user-entered
            #  result dict
            form = getFormAttributes(form, result, 'save')

            # Commit the update
            meta.Session.commit()

            # Foreign word forms will change the inventory-based validation
            h.updateInventoryObjsIfFormIsForeignWord(form)

            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(
                controller='form', action='view', id=form.id)

            return "Moved temporarily" 

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD form with ID=id.
        
        """

        if id is None:
            abort(404)
        form_q = meta.Session.query(model.Form)
        form = form_q.get(int(id))
        if form is None:
            abort(404)


        # If user is not authorized to access this form, let them know.
        if not h.userIsAuthorizedToAccessForm(session['user'], form):
            return getRestrictedFormErrorPage(form)

        # Back up Form to formbackup table
        backupForm(form)

        # Delete Form
        meta.Session.delete(form)
        meta.Session.commit()

        formCount = h.getFormCount()
        app_globals.formCount -= 1

        # Foreign word forms will change the inventory-based validation
        h.updateInventoryObjsIfFormIsForeignWord(form)

        # Create the flash message
        session['flash'] = "Form %s has been deleted" % id
        session.save()
        redirect(url(controller='form', action='results'))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def duplicate(self, id=None):
        """Displays an HTML form for creating a new Form with all of the same
        data as the Form with id=id.
        
        """

        if id is None:
            abort(404)
        form_q = meta.Session.query(model.Form)
        form = form_q.filter_by(id=id).first()
        if form is None:
            abort(404)
        c.formID = form.id

        # If user is not authorized to access this form, let them know.
        if not h.userIsAuthorizedToAccessForm(session['user'], form):
            return getRestrictedFormErrorPage(form)


        values = {
            'ID': form.id,
            'transcription': h.storageToInputTranslate(form.transcription),
            'phoneticTranscription': form.phoneticTranscription,
            'narrowPhoneticTranscription': form.narrowPhoneticTranscription,
            'grammaticality': form.grammaticality,
            'morphemeBreak': h.storageToInputTranslate(form.morphemeBreak, True),
            'morphemeGloss': form.morphemeGloss,
            'comments': h.storageToInputTranslateOLOnly(form.comments),
            'speakerComments': h.storageToInputTranslateOLOnly(form.speakerComments),
            'elicitationMethod': form.elicitationmethod_id,
            'syntacticCategory': form.syntacticcategory_id,
            'speaker': form.speaker_id,
            'elicitor': form.elicitor_id,
            'verifier': form.verifier_id,
            'source': form.source_id,
            'dateElicited': form.dateElicited
        }

        updateContextWithPhoneticFieldDisplaySettings(values)

        # re-format the keys and values of the values dict into a flat structure
        #  so that htmlfill can fill in the form properly. 
        if form.dateElicited:
            dateFormat = session.get('userSettings').get('dateFormat')
            if dateFormat == 'DD/MM/YYYY':
                values['dateElicited'] = form.dateElicited.strftime('%d/%m/%Y')
            else:
                values['dateElicited'] = form.dateElicited.strftime('%m/%d/%Y')

        for i in range(len(form.glosses)):
            gKey = 'glosses-%s.gloss' % i
            ggKey = 'glosses-%s.grammaticality' % i
            iKey = 'glosses-%s.ID' % i
            values[gKey] = form.glosses[i].gloss
            values[ggKey] = form.glosses[i].glossGrammaticality
            values[iKey] = form.glosses[i].id

        for keyword in form.keywords:
            kKey = 'keywords-%s.keyword' % keyword.id
            values[kKey] = keyword.id

        # Make extra glosses fields visible if there are data in them
        c.viewExtraGlossesFields = False
        if 'glosses-1.ID' in values or 'glosses-2.ID' in values or 'glosses-3.ID' in values:
            c.viewExtraGlossesFields = True 

        return renderAddForm(values)

    @h.authenticate
    def history(self, id=None):
        """Display previous versions (i.e., history) of BLD Form with id=id.
        
        """

        if id is None:
            abort(404)
        form = c.form = meta.Session.query(model.Form).get(int(id))  

        if c.form is None:
            abort(404)

        # If user is not authorized to access this form, let them know.
        if not h.userIsAuthorizedToAccessForm(session['user'], form):
            return getRestrictedFormErrorPage(form)

        c.formBackups = meta.Session.query(model.FormBackup).filter(
            model.FormBackup.form_id==int(id)).order_by(
            desc(model.FormBackup.datetimeModified)).all()

        return render('/derived/form/history.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def associate(self, id):
        """Display the page for associating a BLD Form with id=id to a BLD File.
        The HTML form in the rendered page ultimately references the link
        action.
        
        """
        
        if id is None:
            abort(404)

        form = c.form = meta.Session.query(model.Form).get(int(id))
        if c.form is None:
            abort(404)

        # If user is not authorized to access this form, let them know.
        if not h.userIsAuthorizedToAccessForm(session['user'], form):
            return getRestrictedFormErrorPage(form)

        c.associateForm = render('/derived/form/associateForm.html')

        return render('/derived/form/associate.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def link(self, id):
        """Associate BLD Form with id=id to a BLD File.  The ID of the File is
        passed via a POST form.  This "ID" may in fact be a comma-separated list
        of File IDs.
        
        This method handles the request made by the form generated by the
        associate method.
        
        """

        schema=AssociateFormFileForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            c.form = meta.Session.query(model.Form).filter_by(id=id).first()
            associateForm = render('/derived/form/associateForm.html')
            errors = variabledecode.variable_encode(
                e.unpack_errors() or {},
                add_repetitions=False
            )
            c.associateForm = htmlfill.render(associateForm, defaults=values,
                                              errors=errors)
            return render('/derived/form/associate.html')
        else:
            # Get the Form
            if id is None:
                abort(404)
            form = meta.Session.query(model.Form).get(int(id))  
            if form is None:
                abort(404)
    
            # Get the File(s)
            fileID = result['fileID']
            patt = re.compile('^[0-9 ]+$')
            fileIDs = [int(ID.strip().replace(' ', ''))
                       for ID in fileID.split(',')
                       if patt.match(ID)]
            files = meta.Session.query(model.File).filter(
                        model.File.id.in_(fileIDs)).all()
    
            if files:
                for file in files:
                    if file in form.files:
                        msg = '<p>File %d is already associated ' % file.id + \
                              'to Form %d.</p>' % form.id
                        h.appendMsgToFlash(h.literal(msg))
                    else:
                        form.files.append(file)
                        msg = '<p>File %d successfully associated ' % file.id + \
                              'to Form %d.</p>' % form.id
                        h.appendMsgToFlash(h.literal(msg))
                meta.Session.commit()
                session.save()
            else:
                msg = u'<p>Sorry, no Files have any of the following IDs: ' + \
                      '%s.</p>' % fileID
                session.save()
    
            return redirect(url(controller='form', action='view', id=form.id))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def disassociate(self, id, otherID):
        """Disassociate BLD Form id from BLD File otherID.
        
        """

        if id is None or otherID is None:
            abort(404)
        form = meta.Session.query(model.Form).get(int(id)) 
        file = meta.Session.query(model.File).get(int(otherID))

        # If user is not authorized to access this form, let them know.
        if form and not h.userIsAuthorizedToAccessForm(session['user'], form):
            return getRestrictedFormErrorPage(form)

        if file is None:
            if form is None:
                abort(404)
            else:
                session['flash'] = 'There is no File with ID %s' % otherID
        if file in form.files:
            form.files.remove(file)
            meta.Session.commit()
            session['flash'] = 'File %s disassociated' % otherID
        else:
            session['flash'] = 'Form %s was never associated to File %s' % (
                id, otherID)
        session.save()
        redirect(url(controller='form', action='view', id=id))

    @h.authenticate
    def remember(self, id=None):
        """Put BLD Form with id=id into memory.  If no id is provided, put
        either all of the previous search results or all of the forms in the
        database into memory, up to a maximum of 500 forms.
        
        """
        
        max = 500

        if id is None:
            if 'formSearchValues' in session:
                result = session['formSearchValues']
                form_q = meta.Session.query(model.Form)
                c.forms = h.filterSearchQuery(result, form_q, 'Form').limit(
                    max).all()
            else:
                c.forms = meta.Session.query(model.Form).limit(max).all()
        else:
            form_q = meta.Session.query(model.Form)
            c.forms = [form_q.get(int(id))]
            if not c.forms:
                abort(404)

        user = meta.Session.query(model.User).filter(
            model.User.id==session['user_id']).first()
        msg = ''

        formsAppended = 0
        for form in c.forms:
            if form in user.rememberedForms:
                msg += u'<p>Form %s is already in memory</p>' % form.id
            else:
                if h.userIsAuthorizedToAccessForm(user, form):
                    msg += u'<p>Form %s has been remembered</p>' % form.id
                    user.rememberedForms.append(form)
                    formsAppended += 1
                else:
                    msg += u'<p>Sorry, you do not have access to form %d</p>' \
                           % form.id
        msg = u'<h1>%d %s been put into your memory.</h1>\n%s' % (
            formsAppended,
            (lambda x: 'form has' if x == 1 else 'forms have')(formsAppended),
            msg)
        meta.Session.commit()
        session['flash'] = h.literal(msg)
        session.save()
        redirect(url(controller='form', action='results'))

    @h.authenticate
    def export(self, id=None):
        """Export a set of one or more BLD Forms.

        If id is None, export all Forms from last search
        (using session['formSearchValues']); if id is 'memory', export Forms in
        Memory; otherwise, export Form with id == id.

        This action renders an html form (templates/base/export) where the user
        chooses an export type.
        
        """

        c.id = id
        return render('/derived/form/export.html')

    @h.authenticate
    @restrict('POST')
    def exporter(self, id=None):
        """Produce an export document based on the export type chosen by the
        user in the form rendered by the export action.

        An empty id indicates that the set of forms to be exported should be
        queried from the database based on the values of
        session['formSearchValues'].

        An id of 'memory' indicates that we should export everything in Memory.

        To add new export types, add a def to '/base/exporter.html' and add your
        def name and description to app_globals.exportOptions.
        
        """

        if id and id=='memory':
            user = meta.Session.query(model.User).filter(
                model.User.id==session['user_id']).first()
            c.forms = meta.Session.query(model.Form).order_by(
                model.Form.id).filter(
                model.Form.memorizers.contains(user)).all() 
        elif id:
            form_q = meta.Session.query(model.Form)
            c.forms = form_q.filter(model.Form.id==id).all()
        else:
            if 'formSearchValues' in session:
                result = session['formSearchValues']
                form_q = meta.Session.query(model.Form)
                c.forms = h.filterSearchQuery(result, form_q, 'Form').order_by(
                    model.Form.id).all()
            else:
                c.forms = meta.Session.query(model.Form)
        if c.forms is None:
            abort(404)
        c.exportType = request.params['exportType']
        return render('/base/exporter.html')

    @h.authenticate
    def findduplicate(self, id):
        """This method searches the forms table of the db for exact matches to
        the transcription entered on the add or update Form pages.  (The id
        variable contains the transcription entered since I don't want to screw
        around with the routes mappers.)
        
        If matches are found, the return value is an HTML representation of
        those matches.
        
        This method is called asynchronously by the JavaScript
        checkForDuplicateTranscription function defined in
        templates/base/javascriptDefs.html.
        
        """

        searchTerm = h.NFD(id)
        duplicates = meta.Session.query(model.Form).filter(
            model.Form.transcription==searchTerm).all()
        meta.Session.commit()

        if duplicates:
            num = u''
            if len(duplicates) > 1:
                num = u's'
            
            result = u'<span class="warning-message">Potential '
            result += u'duplicate%s found</span>' % num
            duplicateList = []
            for duplicate in duplicates:
                firstGloss = u'%s%s' % (
                    duplicate.glosses[0].gloss,
                    duplicate.glosses[0].glossGrammaticality
                )
                ID = duplicate.id
                URL = url(controller='form', action='view', id=ID)
                title = u'Click to view Form %s' % ID
                duplicateList.append(
                    u'<a href="%s" title="%s">%s</a>' % (
                        URL, title, firstGloss)
                )
            return '%s: %s' % (result, '; '.join(duplicateList))
        else:
            return None

    @h.authenticate
    def guessmorphology(self, id):
        """This method tries to return a morphological analysis for each word in
        the transcription

        This method is called asynchronously by the JavaScript guessMorphology
        function defined in templates/base/javascriptDefs.html.

        To do:
        - account for orthography conversions
        - do fuzzy searches ...

        """

        transcription = h.NFD(id)

        def getMatch(word):
            if 'wordAnalyses' in session and word in session['wordAnalyses']:
                return session['wordAnalyses'][word]
            result = {}
            wordRE = u'(^| )%s($| )' % word
            matches = meta.Session.query(model.Form).filter(
                model.Form.transcription.op('regexp')(wordRE)).filter(
                model.Form.morphemeBreak != u'').filter(
                model.Form.morphemeGloss != u'').all()
            meta.Session.commit()
            for form in matches:
                t, mb, mg = form.transcription, form.morphemeBreak, form.morphemeGloss
                tL, mbL, mgL = t.split(), mb.split(), mg.split()
                if len(tL) == len(mbL) == len(mgL):
                    i = tL.index(word)
                    match = (mbL[i], mgL[i])
                    try:
                        result[(mbL[i], mgL[i])] += 1
                    except KeyError:
                        result[(mbL[i], mgL[i])] = 1
            result = sorted(result.items(), key=lambda (k, v): (v, k))
            result = [x[0] for x in result]
            result.reverse()
            if result == []:
                result = [(word, u'???')]
            if 'wordAnalyses' not in session:
                session['wordAnalyses'] = DictStack()
            session['wordAnalyses'][word] = result
            session.save()
            return result

        result = u''
        words = transcription.split()
        bestGuesses = [getMatch(word)[0] for word in words]
        mbGuess = ' '.join([x[0] for x in bestGuesses])
        mgGuess = ' '.join([x[1] for x in bestGuesses])
        return json.dumps((mbGuess, mgGuess))

    @h.authenticate
    def quicksearch(self, id):
        """This method is called asynchronously from the quicksearch JavaScript
        function defined in /base/index.html.
        
        """

        def formatForm(form, term, direction):
            url_ = url(controller='form', action='results', id=form.id)
            glosses = ', '.join(['%s%s' % (
                gloss.glossGrammaticality,
                gloss.gloss) for gloss in form.glosses])
            transcription = '%s%s' % (form.grammaticality, form.transcription)

            if direction == 'ol':
                transcription = highlightMatches(transcription, term)
            else:
                glosses = highlightMatches(glosses, term)

            result = '<a href="%s">%s; %s; %s; %s; %d</a>' % (url_,
                transcription, form.morphemeBreak, form.morphemeGloss,
                glosses, form.id)
            return result

        def highlightMatches(string, pattern):
            replacement = '<span class="warning-message">%s</span>' % pattern
            return string.replace(pattern, replacement)

        def getOLSearchResults(term):
            # First, try exact search
            result = meta.Session.query(model.Form).filter(
                model.Form.transcription==term).limit(20).all()
            # Then, try regular expression "as a word" search
            if not result:
                termRE = '(^| )%s($| )' % term
                result = meta.Session.query(model.Form).filter(
                    model.Form.transcription.op('regexp')(termRE)).limit(20).all()
            # Finally, try substring (like) search
            if not result:
                likeTerm = '%s%s%s' % ('%', term, '%')
                result = meta.Session.query(model.Form).filter(
                    model.Form.transcription.like(likeTerm)).limit(20).all()
            return [f for f in result
                    if h.userIsAuthorizedToAccessForm(session['user'], f)]

        def getMLSearchResults(term):
            # First, try exact search
            result = meta.Session.query(model.Form, model.Gloss).filter(
                model.Gloss.form_id==model.Form.id).filter(
                model.Gloss.gloss==term).limit(20).all()
            # Then, try regular expression "as a word" search
            if not result:
                termRE = '(^| )%s($| )' % term
                result = meta.Session.query(model.Form, model.Gloss).filter(
                    model.Gloss.form_id==model.Form.id).filter(
                    model.Gloss.gloss.op('regexp')(termRE)).limit(20).all()
            # Finally, try substring (like) search
            if not result:
                likeTerm = '%s%s%s' % ('%', term, '%')
                result = meta.Session.query(model.Form, model.Gloss).filter(
                    model.Gloss.form_id==model.Form.id).filter(
                    model.Gloss.gloss.like(likeTerm)).limit(20).all()
            return [t[0] for t in result
                    if h.userIsAuthorizedToAccessForm(session['user'], t[0])]

        direction = id.split('|')[0]
        term = h.NFD(''.join(id.split('|')[1:]))

        if direction == 'ol':
            result = getOLSearchResults(term)
        else:
            result = getMLSearchResults(term)

        if result:
            return '<ul>\n\t<li>' + '</li>\n\t<li>'.join(
                [formatForm(form, term, direction) for form in result]) + \
                '</li>\n</ul>'
        else:
            return 'No matches for "%s".' % term

    @h.authenticate
    def gettree(self, id):
        """gettree action is referenced by the <img> tags to display trees in
        files/trees.
        
        """

        filesPath = config['app_conf']['permanent_store']
        treesPath = os.path.join(filesPath, 'trees')
        path = os.path.join(treesPath, id, 'tree.png')
        app = FileApp(path)
        return forward(app)