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

Functions used to add filters to an SQLAlchemy query based on the search options
set by a user.

filterSearchQuery is the primary function.  It takes a dict of user-entered
search key-values and an SQLAlchemy query object, adds filters to the query as
appropriate and returns the newly filtered query object.

"""

from pylons import app_globals

from sqlalchemy.sql import and_, or_, not_, asc, desc

import onlinelinguisticdatabase.model as model
from functions import removeWhiteSpace, filesize_to_bytes, escapeUnderscores
import helpers as h

import datetime
import logging

log = logging.getLogger(__name__)


def getFilterCondition(term, searchType, location, tableName):
    """A filterCondition is the statement passed to an SQLA query.filter method.
    Each search statement from the user is used to generate a filter condition.

    """

    # if search location is 'gloss', the filter condition must be on a Gloss col
    if location == 'gloss':
        tableName = 'Gloss'

    # Get the SQLA column object relevant to the filter condition
    tbl = getattr(model, tableName)
    col = getattr(tbl, location)

    # Define the filter condition on the col according to the searchType

    if searchType == 'as a phrase':
        term = u'%' + term + u'%'
        filterCondition = col.like(u'%s' % term)

    elif searchType == 'as a reg exp':
        term = term if term else '.'
        filterCondition = col.op('regexp')(u'%s' % term)

    elif searchType == 'exactly':
        filterCondition = col==u'%s' % term

    else:
        terms = term.split()
        terms = [u'%' + term + u'%' for term in terms]

        if searchType == 'all of these':
            filterCondition = and_([col.like(u'%s' % t) for t in terms])

        else:
            filterCondition = or_([col.like(u'%s' % t) for t in terms])

    return filterCondition


def filterQueryByRestrictor(query, restrictor, tableName):
    """Returns the query filtered according to the restrictor, e.g., 'elicitor
    is Noam Chomsky'.

    """

    containsNot = restrictor['containsNot']
    allAnyOf = restrictor['allAnyOf']
    location = restrictor['location']
    options = restrictor['options']
    options = [o or None for o in options]

    # Get SQLA table object
    if location == 'glossGrammaticality':
        tableName = 'Gloss'
    elif location == 'keywords':
        tableName = 'Keyword'

    tbl = getattr(model, tableName)

    # Get SQLA column object
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
    col = getattr(tbl, location)

    if allAnyOf == 'all of':
        filterCondition = and_(col.in_(options))
    else:
        filterCondition = or_(col.in_(options))

    if containsNot in ['does not contain', 'is not']:
        filterCondition = not_(filterCondition)

    return query.filter(filterCondition)

def filterQueryByDateRestrictor(query, dateRestrictor, tableName):
    """Returns the query filtered by the date restrictor, e.g., 'date elicited
    is earlier than 2011-11-11'.

    """

    location = dateRestrictor['location']

    relation = dateRestrictor['relation']

    date = dateRestrictor['date']
    date = datetime.datetime.combine(date, datetime.time())

    tbl = getattr(model, tableName)
    col = getattr(tbl, location)

    if relation == '' or relation == 'not_':
        nextDay = date + datetime.timedelta(1)
        previousDay = date - datetime.timedelta(1)

        if relation == '':
            filterCondition = and_(col > previousDay, col < nextDay)
        else:
            filterCondition = not_(and_(col > previousDay, col < nextDay))

    elif relation == 'earlier_than':
        filterCondition = col < date

    else:
        filterCondition = col > date

    return query.filter(filterCondition)


def filterQueryByIntegerRestrictor(query, integerRestrictor, tableName):
    """Filter the query according to the integer restrictors, e.g., 'ID is
    greater than 200' or 'file size is less than 200MB'.

    """

    # integer will match the regex /^ *[0-9]+(\.[0-9]+)? *$/
    integer = integerRestrictor['integer'].strip()

    location = integerRestrictor['location']

    relation = integerRestrictor['relation']

    if 'unit' in integerRestrictor:
        unit = integerRestrictor['unit']
    else:
        unit = None

    if unit:
        integer = filesize_to_bytes(float(integer), unit)
    else:
        integer = int(integer.split('.')[0])

    tbl = getattr(model, tableName)
    col = getattr(tbl, location)

    if relation == 'lt':
        filterCondition = col < integer
    elif relation == 'gt':
        filterCondition = col > integer
    elif relation == '==':
        filterCondition = col == integer
    else:
        filterCondition = col != integer

    return query.filter(filterCondition)

def filterQueryByEmptyRestrictor(query, emptyRestrictor, tableName):
    """Filter the query according to the empty restrictors, e.g., 'speaker is
    empty' or 'morpheme break is not an empty string'.

    """

    location = emptyRestrictor['location']
    relation = emptyRestrictor['relation']

    tbl = getattr(model, tableName)
    col = getattr(tbl, location)

    if relation == 'is null':
        filterCondition = col == None
    elif relation == 'is not null':
        filterCondition = col != None
    elif relation == 'is an empty string':
        filterCondition = col == u''
    else:
        filterCondition = col != u''

    return query.filter(filterCondition)


def orderQuery(query, orderByColumn, orderByDirection, tableName):
    """Modify the query via the order_by method, e.g., 'order by ID descending'.

    """

    tbl = getattr(model, tableName)
    if orderByColumn == 'gloss':
        tbl = getattr(model, 'Gloss')

    col = getattr(tbl, orderByColumn)

    if orderByDirection == 'desc':
        query = query.order_by(desc(col))
    else:
        query = query.order_by(asc(col))

    return query


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
    """This function takes an SQLAlchemy ORM query object and applies filters to
    it using the keys and values from the searchValuesDict.  The newly filtered
    query is returned.

    """

    searchTerm1 = escapeUnderscores(
        removeWhiteSpace(searchValuesDict['searchTerm1']))
    searchType1 = searchValuesDict['searchType1']
    searchLocation1 = searchValuesDict['searchLocation1']
    searchTerm2 = escapeUnderscores(
        removeWhiteSpace(searchValuesDict['searchTerm2']))
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

    if 'emptyRestrictors' in searchValuesDict:
        emptyRestrictors = searchValuesDict['emptyRestrictors']
    else:
        emptyRestrictors = []

    orderByColumn = searchValuesDict['orderByColumn']
    orderByDirection = searchValuesDict['orderByDirection']

    # Modify the query object by adding a left outer join to the keyword and
    #  formkeyword tables if appropriate.
    kwRestrictors = [r for r in restrictors if r['location'] == 'keywords']
    if sum([len(r['options']) for r in kwRestrictors]):
        query = query.outerjoin(model.formkeyword_table, model.Keyword)

    # Modify the query object by adding a left outer join to the Gloss table
    #  if appropriate.
    ggRestrictors = [r for r in restrictors
                     if r['location'] == 'glossGrammaticality']
    if sum([len(r['options']) for r in ggRestrictors]) or \
        (searchTerm1 and searchLocation1 == 'gloss') or \
        (searchTerm2 and searchLocation2 == 'gloss'):
        query = query.outerjoin(model.Form.glosses)

    # Get the filter condition of the first search statement
    filterCondition1 = getFilterCondition(searchTerm1, searchType1,
                                          searchLocation1, table)

    # Get the filter condition by coordinating the filter conditions of the two
    #  search statements, if there is a second such statement
    if searchTerm2:
        filterCondition2 = getFilterCondition(searchTerm2, searchType2,
                                          searchLocation2, table)
        if andOrNot == 'and_':
            filterCondition = and_(filterCondition1, filterCondition2)
        elif andOrNot == 'or_':
            filterCondition = or_(filterCondition1, filterCondition2)
        else:
            filterCondition = and_(filterCondition1, not_(filterCondition2))
    else:
        filterCondition = filterCondition1

    query = query.filter(filterCondition)

    # General restrictors
    for restrictor in restrictors:
        if restrictor['options']:
            query = filterQueryByRestrictor(query, restrictor, table)

    # Date restrictors
    for dateRestrictor in dateRestrictors:
        if dateRestrictor['date']:
            query = filterQueryByDateRestrictor(query, dateRestrictor, table)

    # Integer restrictors
    for integerRestrictor in integerRestrictors:
        if integerRestrictor['integer']:
            query = filterQueryByIntegerRestrictor(query, integerRestrictor, table)

    # Empty restrictors
    for emptyRestrictor in emptyRestrictors:
        if emptyRestrictor['relation']:
            query = filterQueryByEmptyRestrictor(query, emptyRestrictor, table)

    # Order by
    query = orderQuery(query, orderByColumn, orderByDirection, table)

    return query