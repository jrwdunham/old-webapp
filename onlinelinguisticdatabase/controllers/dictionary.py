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
import shutil
from mimetypes import guess_type
import re
import zipfile

from paste.fileapp import FileApp

from pylons import config
from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url
from pylons.controllers.util import abort, redirect, forward
from pylons.decorators import validate
from pylons.decorators.rest import restrict

import webhelpers.paginate as paginate

from formencode.schema import Schema
from formencode.validators import Invalid, FancyValidator
from formencode.validators import Int, DateConverter, UnicodeString, OneOf, Regex
from formencode import variabledecode
from formencode import htmlfill
from formencode.foreach import ForEach
from formencode.api import NoDefault

from sqlalchemy.sql import not_, and_
from sqlalchemy import desc


from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

log = logging.getLogger(__name__)


class SearchDictionaryForm(Schema):
    """SearchDictionaryForm is a Schema for validating the search term entered
    at the Dictionary page.
    
    """
    
    allow_extra_fields = True
    filter_extra_fields = True
    dictionarySearchTerm = UnicodeString(not_empty=True)
    dictionarySearchType = UnicodeString()


class ThinForm():
    """Defines a Form-like object with only id, transcription and gloss
    attributes.  The transcription attribute allows a ThinForm to be sorted
    by h.CustomSorter.sort() just like a regular Form.
    
    """
    
    def __init__(self, identifier, transcription, gloss, keywords):
        self.id = identifier
        self.transcription = transcription
        self.gloss = gloss
        self.keywords = keywords


def getSuperGraphs(graph, orthographyAsList):
    """Given a graph x, return a list of those graphs in 
    orthographyAsList of which x is a substring.
    
    e.g., 
        graph = ['a']
        orthographyAsList = [['a', 'ae'], ['o']]
        getSuperGraphs(graph, orthographyAsList) returns ['ae']
    """ 
    result = []
    for x in orthographyAsList:
        for y in graph:
            for z in x:
                if y in z and graph != x:
                    result.append(z)
    return result


class DictionaryController(BaseController):
    """Dictionary Controller object provides a dictionary-like interface to
    the OLD database.
    
    """
    
    @h.authenticate
    def index(self):
        """Index action redirects to browse action.
        
        """
        
        response.status_int = 302
        response.headers['location'] = url(controller='dictionary',
                                                 action='browse')
        return "Moved temporarily"

    @h.authenticate
    def search(self, values=None, errors=None):
        """Display HTML form for searching in Dictionary mode.  HTML form calls
        query action.
        
        """
        
        html = render('/derived/dictionary/search.html')
        return htmlfill.render(html, defaults=values, errors=errors)

    @h.authenticate
    @restrict('POST')
    def query(self):
        """Query action validates the search input values; if valid, query
        stores the search input values in the session and redirects to results;
        if invalid, query redirect to search action (though I don't think it's
        possible to enter an invalid query...).  Query is the action referenced
        by the HTML form rendered by the search action.
        
        """
        
        schema = SearchDictionaryForm()
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
            # result is a Python dict nested structure representing the user's
            # query we put result into session['dictionarySearchValues'] so that the
            # results action can use it to build the SQLAlchemy query.
            session['dictionarySearchValues'] = result
            session.save()
            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(controller='dictionary',
                                                     action='results')
            return "Moved temporarily"

    @h.authenticate
    def results(self):
        """Results action uses the filterSearchQuery helper function to build
        a query based on the values entered by the user in the search file.
        
        """

        result = session['dictionarySearchValues']
        pattern = h.inputToStorageTranslate(result['dictionarySearchTerm'])
        direction = c.languageToSortBy = result['dictionarySearchType']
        
        def getOLQuery(pattern, orthography):
            # Exact query
            general_q = meta.Session.query(model.Form)
            general_q = general_q.filter(not_(
                model.Form.transcription.like(unicode(u'% %'))))
            exactMatch_q = general_q.filter(model.Form.transcription==pattern)
            c.exactMatchList = exactMatch_q.all()

            # Fuzzy query
            general_q = meta.Session.query(model.Form)
            general_q = general_q.filter(not_(
                model.Form.transcription.like(unicode(u'% %'))))
            pattern = unicode('%' + pattern + '%')
            fuzzyMatch_q = general_q.filter(
                model.Form.transcription.like(pattern))  
            c.fuzzyMatchList = fuzzyMatch_q.all()

            if c.exactMatchList or c.fuzzyMatchList:
                cs = h.CustomSorter(orthography)
                c.exactMatchList = cs.sort(c.exactMatchList)
                c.fuzzyMatchList = cs.sort(c.fuzzyMatchList)

        def getMLQuery(pattern, orthography):
            # Exact query
            general_q = meta.Session.query(model.Form)
            general_q = general_q.filter(not_(
                model.Form.transcription.like(unicode(u'% %'))))
            general_q = general_q.outerjoin(model.Form.glosses)
            exactMatch_q = general_q.filter(model.Gloss.gloss==pattern)
            c.exactMatchList = exactMatch_q.all()

            # Fuzzy query
            general_q = meta.Session.query(model.Form)
            general_q = general_q.filter(not_(
                model.Form.transcription.like(unicode(u'% %'))))
            general_q = general_q.outerjoin(model.Form.glosses)
            likePattern = unicode('%' + pattern + '%')
            fuzzyMatch_q = general_q.filter(model.Gloss.gloss.like(likePattern))
            c.fuzzyMatchList = fuzzyMatch_q.all()

            if c.exactMatchList or c.fuzzyMatchList:
                newWordList = []
                for form in c.exactMatchList:
                    goodGlosses = [gloss.gloss for gloss in form.glosses
                                   if pattern == gloss.gloss]
                    for gg in goodGlosses:  
                        newForm = ThinForm(form.id, gg, form.transcription, form.keywords)
                        newWordList.append(newForm)
                c.exactMatchList = newWordList
                exactIds = [x.id for x in c.exactMatchList]

                newWordList = []
                for form in c.fuzzyMatchList:
                    goodGlosses = [gloss.gloss for gloss in form.glosses
                                   if pattern in gloss.gloss]
                    for gg in goodGlosses:  
                        newForm = ThinForm(form.id, gg, form.transcription, form.keywords)
                        newWordList.append(newForm)
                c.fuzzyMatchList = [x for x in newWordList
                                    if x.id not in exactIds]

                cs = h.CustomSorter(orthography)
                c.exactMatchList = cs.sort(c.exactMatchList)
                c.fuzzyMatchList = cs.sort(c.fuzzyMatchList)
                
        directionToOrthography = {
            'ol': app_globals.storageOrthography[1],
            'ml': app_globals.metaLanguageOrthography
        }
        directionToResultListsGetter = {
            'ol': getOLQuery,
            'ml': getMLQuery
        }
                    
        orthography = directionToOrthography[direction]
        directionToResultListsGetter[direction](pattern, orthography)
        return render('/derived/dictionary/search.html')


    @h.authenticate
    def browse(self, id=None): 
        """Generates page for browsing Forms as dictionary entries.
        
        Id variable (regex '[0-9]+_(ol|ml)') encodes both 
        the index of the first letter of the words being browsed and
        the language (object or meta-) being browsed.
        
        A first letter index of 1000000 means browse everything.
        
        """

        # Get OL orthography as an HTML table of links to browse actions
        OLOrthography = app_globals.defaultOutputOrthography[1]
        OLOrthographyAsList = OLOrthography.orthographyAsList
        OLOrthographyX = ['<a href="%s" %s>%s</a>' % (
            url(
                controller='dictionary', 
                action='browse', 
                id=str(OLOrthographyAsList.index(x)) + '_ol', 
                anchor='hl'
            ),
            'title="browse by %s character \'%s\'"' % (
                app_globals.objectLanguageName, h.storageToOutputTranslate(x[0])
            ),
            h.storageToOutputTranslate(x[0])
            ) for x in OLOrthographyAsList]
        c.OLOrthographyTable = h.literal(
            h.tablify(OLOrthographyX, 14, 'orthographyAsLinks'))
        
        # Get ML orthography as an HTML table of links to browse actions
        MLOrthography = app_globals.metaLanguageOrthography
        MLOrthographyAsList = MLOrthography.orthographyAsList
        MLOrthographyX = ['<a href="%s" %s>%s</a>' % (
            url(
                controller='dictionary', 
                action='browse', 
                id=str(MLOrthographyAsList.index(x)) + '_ml', 
                anchor='hl'
            ),
            'title="browse by %s character \'%s\'"' % (
                app_globals.metaLanguageName, x[0]),
            x[0]
            ) for x in MLOrthographyAsList]        
        c.MLOrthographyTable = h.literal(
            h.tablify(MLOrthographyX, 14, 'orthographyAsLinks'))
        
        # If there is a valid first-letter index,
        #  build a query and return the appropriate variables.
        patt = re.compile('^[0-9]+_(ol|ml)$')
        if id and patt.search(id):
            headCharIndex = id.split('_')[0]
            c.languageToSortBy = id.split('_')[1]
            langToOrth = {
                'ol': [app_globals.storageOrthography[1], OLOrthographyAsList,
                       'transcription'],
                'ml': [MLOrthography, MLOrthographyAsList, 'gloss']
            }
            orthography = langToOrth[c.languageToSortBy][0]
            orthographyAsList = langToOrth[c.languageToSortBy][1]
            try:
                c.headChar = orthographyAsList[int(headCharIndex)]
            except IndexError:
                c.headChar = None
            wordList_q = meta.Session.query(model.Form)
            wordList_q = wordList_q.filter(
                not_(model.Form.transcription.like(u'% %'))
            )
            
        # The default case
        #  Non-empty headChar means a letter was clicked on
        if id and c.headChar:
        
            # filter and sort wordList for object-language-to-metalanguage view
            if c.languageToSortBy == 'ol':
                wordList_q = wordList_q.filter(
                    model.Form.transcription.op('regexp')(
                        '^(%s)' % '|'.join(c.headChar))
                )
                    
                # existence of supergraphs means we have to filter the query
                #  of Forms whose transcription/gloss begins with a supergraph
                superGraphs = getSuperGraphs(c.headChar, OLOrthographyAsList)
                if superGraphs:
                    wordList_q = wordList_q.filter(
                        not_(model.Form.transcription.op('regexp')(
                            '^(%s)' % '|'.join(superGraphs)))
                    )
                
                # sort wordList using functions.CustomSorter class
                c.wordList = wordList_q.all()   
                if c.wordList:
                    cs = h.CustomSorter(orthography)
                    c.wordList = cs.sort(c.wordList)
            # filter and sort wordList for metalanguage-to-object-metalanguage view
            elif c.languageToSortBy == 'ml':
                wordList_q = wordList_q.outerjoin(
                    model.Form.glosses
                )
                wordList_q = wordList_q.filter(
                    model.Gloss.gloss.op('regexp')('^(%s)' % '|'.join(c.headChar))
                )
                
                # existence of supergraphs means we have to filter the query
                #  of Forms whose transcription/gloss begins with a supergraph
                superGraphs = getSuperGraphs(c.headChar, MLOrthographyAsList)
                if superGraphs:
                    wordList_q = wordList_q.filter(
                        not_(model.Gloss.gloss.op('regexp')(
                            '^(%s)' % '|'.join(superGraphs)))
                    )
                wordList = wordList_q.all()
                
                if wordList:
                    patt = re.compile('^%s' % c.headChar)
                    newWordList = []
                    for form in wordList:
                        goodGlosses = [gloss.gloss for gloss in form.glosses
                                       if patt.match(gloss.gloss)]
                        for gg in goodGlosses:  
                            newForm = ThinForm(form.id, gg, form.transcription, form.keywords)
                            newWordList.append(newForm)
                    cs = h.CustomSorter(orthography)
                    c.wordList = cs.sort(newWordList)
        # The special case
        #  id of a million means we are browsing everything!
        elif id and int(headCharIndex) == 1000000:
            wordList = wordList_q.all()
            if c.languageToSortBy == 'ml':
                newWordList = []
                for form in wordList:
                    goodGlosses = [gloss.gloss for gloss in form.glosses]
                    for gg in goodGlosses:  
                        newForm = ThinForm(form.id, gg, form.transcription, form.keywords)
                        newWordList.append(newForm)
                cs = h.CustomSorter(orthography)
                c.wordList = cs.sort(newWordList)
            else:
                cs = h.CustomSorter(orthography)
                c.wordList = cs.sort(wordList)

        return render('/derived/dictionary/browse.html') 