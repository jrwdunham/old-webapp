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

from pylons import app_globals

from formencode.schema import Schema
from formencode.validators import Invalid, FancyValidator
from formencode.validators import Int, DateConverter, UnicodeString, OneOf, Regex
from formencode import variabledecode
from formencode import htmlfill, All
from formencode.foreach import ForEach
from formencode.api import NoDefault

class FirstGlossNotEmpty(FancyValidator):
    """
    Custom validator.  Ensures that the first gloss field, 'gloss-0.text',
    has some content.
    """
    messages = {
        'one_gloss': 'Please enter a gloss in the first gloss field'
    }
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
    transcription = UnicodeString(not_empty=True, messages={'empty':'Please enter a transcription.'})
    phoneticTranscription = UnicodeString()
    narrowPhoneticTranscription = UnicodeString()
    morphemeBreak = UnicodeString()
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