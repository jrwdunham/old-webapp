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

"""Query Builder

Functions used to add filters to an SQLAlchemy query based
on the search options set by a user.

filterSearchQuery is the primary function.  It takes a dict 
of user-entered search key-values and a SQLAlchemy query,
adds filters to the query as appropriate and returns a new
query object.

THIS ENTIRE MODULE NEEDS TO BE RE-WRITTEN.  It is very poorly written and
probably full of bugs I just haven't noticed yet (Oct 5, 2010).

"""
from pylons import app_globals

from sqlalchemy.sql import and_, or_, not_, asc, desc

import onlinelinguisticdatabase.model as model
from functions import removeWhiteSpace, filesize_to_bytes, escapeUnderscores
import helpers as h

import datetime
import logging

log = logging.getLogger(__name__)

def getOperatorPlusTerm(searchType, term):
    """Return an appropriate SQLAlchemy operator + term combination."""
    if searchType == 'as a phrase':
        return '.like(u"%s")' % term
    elif searchType == 'as a reg exp':
        # an empty search term with regexp type will cause an error, so use '.'
        if term is u'':
            term = u'.'
        return '.op("regexp")(u"%s")' % term
    else:
        return '==u"%s"' % term

def filterBySingleTerm(term, searchType, location, table):
    """Filter query for "as a phrase", "exactly" and "as a reg exp" search types."""
    # table variable holds name of table to base filter on (default is Form)
    if location == 'gloss':
        table = 'Gloss'
    # as a phrase searches are SQL "like" queries and require search term to
    #  be surrounded by "%"
    if searchType == 'as a phrase':
        term = u'%' + term + u'%'
    # get operator and term as a string, depending on the searchType
    operatorPlusTerm = getOperatorPlusTerm(searchType, term)
    # compose string to build filter
    filterString = "model.%s.%s%s" % (table, location, operatorPlusTerm)
    return filterString 

def filterByMultipleTerms(term, searchType, location, table):
    """Filter query for "all of these" and "any of these" search types."""
    # table variable holds name of table to base filter on (default is Form)
    if location == 'gloss':
        table = 'Gloss'
    # translate searchType to SQLAlchemy boolean operator
    typeToBoolean = {'all of these': 'and_', 'any of these': 'or_'}
    boolean = typeToBoolean[searchType]
    # get space-delimited terms and surround each by %
    terms = term.split(' ')
    terms = [u'%' + term + u'%' for term in terms]
    # compose string to build filter
    filterString = '%s(' % boolean + ', '.join(['model.%s.%s.like(u"%s")' % (table, location, term) for term in terms]) + ')'
    return filterString

def apo(location):
    """Patch-up function that returns a double quote if the location value is
    a string type.  This function is needed by the filterByRestrictor function.
    """
    if location in ['grammaticality', 'glossGrammaticality', 'utteranceType']:
        return '"'
    else:
        return ''
    
    
def filterByRestrictor(restrictor, table):
    """Given a dictionary of restrictor k-v pairs,
    returns an SQLAlchemy ORM filter string based on the restrictor."""
    containsNot = restrictor['containsNot']
    allAnyOf = restrictor['allAnyOf']
    location = restrictor['location']
    options = restrictor['options']
    # table variable holds name of table to base filter on (default is Form)
    if location == 'glossGrammaticality':
        table = 'Gloss'
    elif location == 'keywords':
        table = 'Keyword'
    # translate containsNot and allAnyOf values to SQLAlchemy boolean operators
    containsNotToBoolean = {'contains':'', 'does not contain': 'not_', 'is': '', 'is not': 'not_'}
    containsNot = containsNotToBoolean[containsNot]
    allAnyOfToBoolean = {'all of': 'and_', 'any of': 'or_'}
    allAnyOf = allAnyOfToBoolean[allAnyOf]
    # translate locations into names of columns where appropriate
    locationToColumnName = {
        'speaker': 'speaker_id', 
        'elicitor': 'elicitor_id', 
        'enterer': 'enterer_id', 
        'verifier': 'verifier_id', 
        'syntacticCategory': 'syntacticcategory_id', 
        'elicitationMethod': 'elicitationmethod_id', 
        'source': 'source_id', 
        'keywords': 'id'
    }
    if location in locationToColumnName:
        location = locationToColumnName[location]
    # create filter string stage 1 - conjunction or disjunction of options
    filterString = '%s(' % allAnyOf + ', '.join(['model.%s.%s == %s%s%s' % (table, location, apo(location), option or None, apo(location)) for option in options]) + ')'
    # create filter string stage 2 - add negation if requested
    if containsNot:
        filterString = containsNot + '(' + filterString + ')'
    return filterString

def filterByDateRestrictor(dateRestrictor, table):
    """Given a dictionary of dateRestrictor k-v pairs,
    returns an SQLAlchemy ORM filter string based on the dateRestrictor."""
    location = dateRestrictor['location']
    relation = dateRestrictor['relation']
    relation = {'earlier_than':'<', 'later_than':'>', '':'', 'not_':'not_'}[relation]
    date = dateRestrictor['date']
    date = datetime.datetime.combine(date, datetime.time())
    print '\n\n\n%s\n\n\n' % type(date)
    if relation=='' or relation=='not_':
        nextDay = date + datetime.timedelta(1)
        previousDay = date - datetime.timedelta(1)
        filterString = '%s(and_(model.%s.%s > "%s", model.Form.%s < "%s"))' % (relation, table, location, previousDay, location, nextDay)     
    else:
        filterString = 'model.%s.%s %s "%s"' % (table, location, relation, date)      
    return filterString

def filterByIntegerRestrictor(integerRestrictor, table):
    """Given a dictionary of integerRestrictor k-v pairs,
    returns an SQLAlchemy ORM filter string based on the integerRestrictor."""
    location = integerRestrictor['location']
    relation = integerRestrictor['relation']
    relation = {'lt':'<', 'gt':'>', '==':'==', '!=':'!='}[relation]
    integer = integerRestrictor['integer']
    if 'unit' in integerRestrictor:
        unit = integerRestrictor['unit']
    if unit:
        integer = filesize_to_bytes(integer, unit)
    else:
        integer = int(integer.split('.')[0])
    filterString = 'model.%s.%s %s %s' % (table, location, relation, integer)      
    return filterString

def orthoTranslateSearchTerm(term, location):
    """A user may be using an input orthography different from the storage
    orthography.  Therefore, their searches on the transcription, morphemeBreak,
    comments and speakerComments fields may contain strings in the input
    orthography that need to be translated into the storage orthography.  This
    function performs that translation.
    
    """
    if location not in [
        'transcription', 'morphemeBreak', 'comments', 'speakerComments']:
        return term
    elif location in ['transcription']:
        return h.inputToStorageTranslate(term)
    elif location in ['morphemeBreak']:
        return h.inputToStorageTranslate(term, True)
    else:
        return h.inputToStorageTranslateOLOnly(term)
    
    
def filterSearchQuery(searchValuesDict, query, table):
    """Function takes a SQLAlchemy ORM query and filters it
    using the keys and values from the HTML search form."""

    searchTerm1 = escapeUnderscores(removeWhiteSpace(searchValuesDict['searchTerm1']))
    searchType1 = searchValuesDict['searchType1']
    searchLocation1 = searchValuesDict['searchLocation1']
    searchTerm2 = escapeUnderscores(removeWhiteSpace(searchValuesDict['searchTerm2']))
    searchType2 = searchValuesDict['searchType2']
    searchLocation2 = searchValuesDict['searchLocation2']
    
    # Translate the search terms into the storage orthography, if necessary
    searchTerm1 = orthoTranslateSearchTerm(searchTerm1, searchLocation1)
    searchTerm2 = orthoTranslateSearchTerm(searchTerm2, searchLocation2)
    
    andOrNot = searchValuesDict['andOrNot']
    restrictors = searchValuesDict['restrictors']
    dateRestrictors = searchValuesDict['dateRestrictors']
    if 'integerRestrictors' in searchValuesDict:
        integerRestrictors = searchValuesDict['integerRestrictors']
    else:
        integerRestrictors = []
    orderByColumn = searchValuesDict['orderByColumn']
    orderByDirection = searchValuesDict['orderByDirection']

    # Dictionary from search type value to appropriate filter function
    functionsBySearchType = {
        'as a phrase': filterBySingleTerm, 
        'as a reg exp': filterBySingleTerm,
        'exactly': filterBySingleTerm,
        'all of these': filterByMultipleTerms, 
        'any of these': filterByMultipleTerms
    }
        
    # Get strings representing the filter(s) on the query:
    filterString = functionsBySearchType[searchType1](searchTerm1, searchType1, searchLocation1, table)
    if searchTerm2:
        filterString2 = functionsBySearchType[searchType2](searchTerm2, searchType2, searchLocation2, table)
        # Put boolean operators in the right place, with brackets
        if andOrNot == 'not_':
            filterString = 'and_(%s, not_(%s))' % (filterString, filterString2)
        else:
            filterString = '%s(%s, %s)' % (andOrNot, filterString, filterString2)

    # Add a a left outer join to the keyword and formkeyword tables if appropriate
    #  otherwise add a left outer join to the gloss table if appropriate,
    #   otherwise no left outer join.
    keywordsRestrictors = [restrictor for restrictor in restrictors if restrictor['location'] == 'keywords']
    if sum([len(restrictor['options']) for restrictor in keywordsRestrictors]):    
        outerjoin = '.outerjoin(model.Form.glosses, model.formkeyword_table, model.Keyword)'
    elif (searchTerm1 and searchLocation1 == 'gloss') or (searchTerm2 and searchLocation2 == 'gloss'):
        outerjoin = '.outerjoin(model.Form.glosses)'
    else:
        outerjoin = ''

    # Compose the right hand side of the filtered query expression
    filterString = 'query%s.filter(%s)' % (outerjoin, filterString)
    
    # Evaluate the object and methods mentioned in the string using Python's eval(),
    # Update the query object using Python's exec()
    cmd = "query = eval('%s' % filterString)"
    exec(cmd)

    # If there are restrictors, filter the query further
    for restrictor in restrictors:
        if len(restrictor['options']):
            filterString = filterByRestrictor(restrictor, table)
            filterString = 'query.filter(%s)' % filterString
            cmd = "query = eval('%s' % filterString)"
            exec(cmd)

    # If there are date restrictors, filter the query further
    for dateRestrictor in dateRestrictors:
        if dateRestrictor['date']:
            filterString = filterByDateRestrictor(dateRestrictor, table)
            filterString = 'query.filter(%s)' % filterString
            cmd = "query = eval('%s' % filterString)"
            exec(cmd)

    # If there are integer restrictors, filter the query further
    for integerRestrictor in integerRestrictors:
        if integerRestrictor['integer']:
            filterString = filterByIntegerRestrictor(integerRestrictor, table)
            filterString = 'query.filter(%s)' % filterString
            cmd = "query = eval('%s' % filterString)"
            exec(cmd)
    
    # Finally add the ordering
    query = eval('query.order_by(%s(model.%s.%s))' % (orderByDirection, table, orderByColumn))
    #query = query.order_by(desc(model.Form.transcription))    

    # Return the filtered query
    return query
