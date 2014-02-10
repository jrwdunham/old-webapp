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
from sqlalchemy.sql import or_, not_

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h
from onlinelinguisticdatabase.lib.oldMarkup import embedContentsOfCollections, linkToOLDEntitites, embedFiles

from sqlalchemy import desc

try:
    import json
except ImportError:
    import simplejson as json

log = logging.getLogger(__name__)


class NewCollectionForm(Schema):
    """NewCollectionForm is a Schema for validating the data entered at the Add Collection page."""
    allow_extra_fields = True
    filter_extra_fields = True
    title = UnicodeString(not_empty=True)
    url = Regex('[a-zA-Z0-9_/-]+')
    type = UnicodeString()
    description = UnicodeString()
    speaker = UnicodeString()
    elicitor = UnicodeString()
    source = UnicodeString()
    dateElicited = DateConverter(month_style='mm/dd/yyyy')
    contents = UnicodeString()

class NewCollectionFormDM(NewCollectionForm):
    dateElicited = DateConverter(month_style='dd/mm/yyyy')

class UpdateCollectionForm(NewCollectionForm):
    ID = UnicodeString()

class UpdateCollectionFormDM(UpdateCollectionForm):
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

class SearchCollectionForm(Schema):
    """SearchCollection is a Schema for validating the search terms entered at
    the Search Collections page.

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
    orderByColumn = UnicodeString()
    orderByDirection = UnicodeString()

class AssociateCollectionFileForm(Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    fileID = Regex(r'^ *[1-9]+[0-9]* *( *, *[1-9]+[0-9]* *)*$', not_empty=True)

def renderAddCollection(values=None, errors=None, addUpdate='add'):
    """Function is called by both the add and update actions to create the
    Add Collection and Update Collection HTML forms.  The create and save
    actions can also call this function if any errors are present in the input.
    
    """
    
    # if addUpdate is set to 'update', render update.html instead of add.html
    if addUpdate == 'add':
        html = render('/derived/collection/add.html')
    else:
        html = render('/derived/collection/update.html')

    return htmlfill.render(html, defaults=values, errors=errors)


def getCollectionAttributes(collection, result, createOrSave):
    """Given a (SQLAlchemy) Collection object and a result dictionary populated
    by user-entered data, this function populates the appropriate attributes
    with the appropriate values.  This function is called by both create and
    save actions.
    
    """

    # User-entered Data
    collection.title = h.NFD(result['title'])
    collection.type = h.NFD(result['type'])
    collection.url = h.NFD(result['url'])
    collection.description = h.NFD(result['description'])
    if result['speaker']:
        collection.speaker = meta.Session.query(model.Speaker).get(int(result['speaker']))
    if result['elicitor']:
        collection.elicitor = meta.Session.query(model.User).get(int(result['elicitor']))
    if result['source']:
        collection.source = meta.Session.query(model.Source).get(int(result['source']))
    if result['dateElicited']:
        collection.dateElicited = result['dateElicited']

    # OLD-generated Data
    now = datetime.datetime.utcnow()
    collection.datetimeModified = now

    if createOrSave == 'create':
        collection.datetimeEntered = now
        # Add the Enterer as the current user
        collection.enterer = meta.Session.query(model.User).get(
            int(session['user_id']))

    # Extract component Forms from the collection objects contents field and
    #  append them to collection.forms
    collection.forms = []
    collection.contents = h.NFD(result['contents'])
    patt = re.compile('[Ff]orm\[([0-9]+)\]')
    formIDs = patt.findall(collection.contents)
    for formID in formIDs:
        form = meta.Session.query(model.Form).get(int(formID))
        if form:
            collection.forms.append(form)

    return collection


def backupCollection(collection):
    """When a Collection is being updated or deleted, it is first added to the
    collectionbackup table.
    
    """
    
    # transform nested data structures to JSON for storage in a 
    #  relational database unicode text column
    collectionBackup = model.CollectionBackup()
    user = json.dumps({
        'id': session['user_id'],
        'firstName': session['user_firstName'],
        'lastName': session['user_lastName']
    })
    collectionBackup.toJSON(collection, user)
    meta.Session.add(collectionBackup)


def getExampleTable(enumerator, match, formID):
    """This function returns an HTML table for displaying a linguistic example
    form.  The Form embedding reference expression (e.g., 'form[88]') is left
    unaltered.  This function simply wraps it in an HTML table for display as
    an example in a Collection contents field.
    
    Argument explanation:
    
    - enumerator is an int representing the example number, e.g., 2
    - match is the string matching the pattern, e.g., 'form[88]'
    - formID is an int: the ID of the form, e.g., 88
    
    """
    
    temp = u'\n\n<table class="igt">\n <tr>\n  <td class="enumerator">'
    temp += u'<a href="%s" title="View this Form">(%s)</a></td>\n  <td>%s</td>\n' % (
        url(controller='form', action='view', id=formID),
        str(enumerator),
        match
    )
    temp += u'</tr>\n</table>\n\n'
    return temp

def getEnumerator(formID2Enumerator, key):
    try:
        return formID2Enumerator[key]
    except KeyError:
        return '???'

def getFormFromID(formsDict, formID):
    try:
        return formsDict[formID]
    except KeyError:
        return 'THERE IS NO FORM WITH ID %s\n\n<br /><br />\n\n' % str(formID)

def getFormAsHTMLTable(match, formsDict):
    """getFormAsHTMLTable uses the form method getIGTHTMLTable (see
    lib/oldCoreObjects.py to return an HTML representation of the Form.
    
    """
    
    form = getFormFromID(formsDict, int(match.group(2)))

    try:
        return '%s\n\n<br />\n\n' % form.getHTMLRepresentation(forCollection=True)
    # AttributeError means getFormFromID gave us an error string, so pass it on
    except AttributeError:
        return form

def getCollectionContentsAsHTML(collection):
    """This function formats the contents of a Collection as HTML.  It assumes
    the contents text is written in reStructuredText.
    
    """
    
    contents = collection.contents
    
    # formID2Enumerator example: {'9': '4'} means that the first Form with ID=9
    #  occurs as the fourth example (i.e., enumerator = '4') in the Collection
    formID2Enumerator = {}
    
    # enumerator gives example numbers to embedded forms
    enumerator = 1
    
    # c.formsDict will be used by template to get the correct Form
    c.formsDict = dict([(form.id, form) for form in collection.forms])
    
    # Replace each embedding reference to a Collection with its contents
    #  (verbatim). Do this first so that the subsequent rst2html conversion will
    #  convert the composite collection in one go.  This seems easier than doing
    #  rst2html(collection.contents) for each embedded Collection...
    contents = embedContentsOfCollections(contents)

    # Convert collection's contents to HTML using rst2html
    contents = h.rst2html(contents)
    
    # Replace "form[X]" with an example table, i.e., enumerator in first cell,
    #  form data in second:
    #
    #   (23)    blah    blahblah x
    #           blah    blah-blah x
    #           xyz     xyz-xyz-33
    #           zyz3 3 ayaazy883
    #
    patt = re.compile('([Ff]orm\[([0-9]+)\])')
    newContentsLinesList = []
    contentsLinesList = patt.sub('\n\\1\n', contents).split('\n')

    for line in contentsLinesList:
        if patt.search(line):
            
            # Update formID2Enumerator only if this is this form's first occurrence
            if patt.search(line).group(2) not in formID2Enumerator:
                formID2Enumerator[patt.search(line).group(2)] = str(enumerator)
            
            # Replace each match with an example table with an enumerator
            newContentsLinesList.append(
                patt.sub(
                    lambda x: getExampleTable(
                        enumerator, x.group(1), int(x.group(2))),
                    line
                )
            )

            enumerator += 1
        else:
            newContentsLinesList.append(line)
            
    contents = '\n'.join(newContentsLinesList)

    # Replace "ref[x]" with the enumerator of the first occurrence of the Form
    #  with id=x that is embedded in this Collection's content
    refPatt = re.compile('([Rr]ef\[([0-9]+)\])')
    contents = refPatt.sub(
        lambda x: getEnumerator(formID2Enumerator, x.group(2)), contents)

    # Replace each embedding reference to a Form with a representation of that
    #  Form.
    contents = patt.sub(
        lambda x: getFormAsHTMLTable(x, c.formsDict),
        contents
    )

    # Embed OLD Files
    contents = embedFiles(contents)

    # Replace each linking reference to an OLD entity with an HTML link
    contents = linkToOLDEntitites(contents)
    
    return contents


class CollectionController(BaseController):
    """Collection Controller contains actions about OLD Collections.
    Authorization and authentication are implemented by the
    helper decorators authenticate and authorize which can be
    found in lib/auth.py."""

    @h.authenticate
    def browse(self):
        """Browse through all Collections in the system.
        
        """
        c.collections = {}
        for cType in app_globals.collectionTypes:
            c.collections[cType] = meta.Session.query(model.Collection).filter(
                model.Collection.type==cType).order_by(
                model.Collection.title).all()
        c.collectionCount = sum([len(c.collections[x]) for x in c.collections])
        c.browsing = True
        c.oddlyTypedCollections = meta.Session.query(model.Collection).filter(
                not_(model.Collection.type.in_(app_globals.collectionTypes))).order_by(
                model.Collection.title).all()
        return render('/derived/collection/results.html')

    @h.authenticate
    def view(self, id, option=None):
        """View a BLD Collection.  Requires a Collection ID as input.
        
        """
        
        # Get the Collection with id=id
        if id is None:
            abort(404)
        collection_q = meta.Session.query(model.Collection)
        try:
            c.collection = collection_q.get(int(id))
        except ValueError:
            abort(404)
        if c.collection is None:
            abort(404)

        # Convert the Collection contents (assumed to be in reStructuredText
        #  with OLDMarkup) to HTML
        c.contents = getCollectionContentsAsHTML(c.collection)

        return render('/derived/collection/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Display HTML form for adding a new BLD Collection.
        HTML form calls create action."""
        return renderAddCollection()

    @h.authenticate
    def search(self, values=None, errors=None):
        """Display HTML form for searching for BLD Collections.  HTML form calls
        query action.

        """

        # if no user-entered defaults are set, make gloss the default for searchLocation2
        if not values:
            values = {'searchLocation2': u'description'}
            values['orderByColumn'] = 'id'
        # By default, the additional search restrictors are hidden
        c.viewRestrictors = False
        # Get today in MM/DD/YYYY collection    
        c.today = datetime.date.today().strftime('%m/%d/%Y')
        html = render('/derived/collection/search.html')      
        return htmlfill.render(html, defaults=values, errors=errors)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def create(self):
        """Enter BLD Collection data into the database.  This is the action
        referenced by the HTML form rendered by the add action.

        """

        dateFormat = session.get('userSettings').get('dateFormat')
        if dateFormat == 'DD/MM/YYYY':
            schema = NewCollectionFormDM()
        else:
            schema = NewCollectionForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            return renderAddCollection(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                )
            )
        else:
            # Create a new Collection SQLAlchemy Object and populate its attributes with the results
            collection = model.Collection()
            collection = getCollectionAttributes(collection, result, 'create')
            # Enter the data
            meta.Session.add(collection)
            meta.Session.commit()
            # Issue an HTTP redirect
            redirect(url(controller='collection', action='view', id=collection.id))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def getmemory(self):
        """Insert references to Forms in Memory into the content field of
        the Collection being added or updated."""
        values = dict(request.params)
        # Get all Forms that user has memorized ordered by Form ID 
        #  by using the 'memorizers' backreference
        user = meta.Session.query(model.User).filter(model.User.id==session['user_id']).first()
        rememberedForms = meta.Session.query(model.Form).order_by(model.Form.id).filter(model.Form.memorizers.contains(user)).all()         
        rememberedFormIDs = ['form[%s]' % form.id for form in rememberedForms]
        return '\n'.join(rememberedFormIDs)

    @h.authenticate
    @restrict('POST')
    def query(self):
        """Query action validates the search input values; if valid, query
        stores the search input values in the session and redirects to results;
        if invalid, query redirect to search action (though I don't think it's
        possible to enter an invalid query...).  Query is the action referenced
        by the HTML form rendered by the search action.

        """

        schema = SearchCollectionForm()
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
            #  query.  We put result into session['collectionSearchValues'] so
            #  that the results action can use it to build the SQLAlchemy query
            session['collectionSearchValues'] = result
            session.save() 
            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(
                controller='collection', action='results')
            return "Moved temporarily"

    @h.authenticate
    def results(self):
        """Results action uses the filterSearchQuery helper function to build
        a query based on the values entered by the user in the search
        collection.

        """

        collection_q = meta.Session.query(model.Collection)
        if 'collectionSearchValues' in session:
            result = session['collectionSearchValues']
            collection_q = h.filterSearchQuery(
                result, collection_q, 'Collection')

        c.paginator = paginate.Page(
            collection_q,
            page=int(request.params.get('page', 1)),
            items_per_page = app_globals.collection_items_per_page
        )

        return render('/derived/collection/results.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def update(self, id=None):
        """Displays an HTML form for updating a BLD Collection.  HTML form calls
        save action.

        """

        if id is None:
            abort(404)
        collection_q = meta.Session.query(model.Collection)
        collection = collection_q.filter_by(id=id).first()
        if collection is None:
            abort(404)
        c.collection = collection

        values = {
            'ID': collection.id,
            'title': collection.title,
            'type': collection.type,
            'url': collection.url,
            'description': collection.description,
            'elicitor': collection.elicitor_id,
            'speaker': collection.speaker_id,
            'source': collection.source_id,
            'contents': collection.contents
        }

        if collection.dateElicited:
            dateFormat = session.get('userSettings').get('dateFormat')
            if dateFormat == 'DD/MM/YYYY':
                values['dateElicited'] = collection.dateElicited.strftime(
                    '%d/%m/%Y')
            else:
                values['dateElicited'] = collection.dateElicited.strftime(
                    '%m/%d/%Y')

        return renderAddCollection(values, None, 'update')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def save(self):
        """Updates existing BLD Collection.  This is the action referenced by
        the HTML form rendered by the update action.

        """

        dateFormat = session.get('userSettings').get('dateFormat')
        if dateFormat == 'DD/MM/YYYY':
            schema = UpdateCollectionFormDM()
        else:
            schema = UpdateCollectionForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            id = int(values['ID'])
            collection_q = meta.Session.query(model.Collection)
            collection = collection_q.filter_by(id=id).first()
            c.collection = collection
            c.id = values['ID']
            return renderAddCollection(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                ),
                addUpdate='update'
            )
        else:
            # Get the Collection object with ID from hidden field in update.html
            collection_q = meta.Session.query(model.Collection)
            collection = collection_q.filter_by(id=result['ID']).first()
            
            # Backup the Collection to the collectionbackup table
            backupCollection(collection)
            
            # Populate the Collection's attributes with the data from the user-entered result dict
            collection = getCollectionAttributes(collection, result, 'save')
            
            # Commit the update
            meta.Session.commit()
            
            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(controller='collection', action='view', id=collection.id)

            return "Moved temporarily" 

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD collection with ID=id."""
        
        if id is None:
            abort(404)
        collection_q = meta.Session.query(model.Collection)
        collection = collection_q.get(int(id))
        if collection is None:
            abort(404)

        # Back up Form to formbackup table
        backupCollection(collection)

        # Delete Collection info in database
        meta.Session.delete(collection)
        meta.Session.commit()
        
        # Create the flash message
        session['flash'] = "Collection %s has been deleted" % id
        session.save()
        redirect(url(controller='collection', action='results'))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def associate(self, id):
        """Display the page for associating a BLD Collection with id=id 
        to a BLD File.  The HTML form in the rendered page ultimately
        references the link action."""
        if id is None:
            abort(404)
        c.collection = meta.Session.query(model.Collection).get(int(id))  
        if c.collection is None:
            abort(404)   
        return render('/derived/collection/associate.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    @validate(schema=AssociateCollectionFileForm(), form='associate')
    def link(self, id):
        """Associate BLD Collection with id=id to a BLD File.  The ID of the 
        File is passed via a POST form.  This "ID" may in fact be a 
        comma-separated list of File IDs."""
        # Get the Form
        if id is None:
            abort(404)
        collection = meta.Session.query(model.Collection).get(int(id))  
        if collection is None:
            abort(404)
        # Get the File(s)   
        fileID = self.form_result['fileID']
        patt = re.compile('^[0-9 ]+$')
        fileIDs = [ID.strip().replace(' ', '') for ID in fileID.split(',') if patt.match(ID)]
        file_q = meta.Session.query(model.File)
        filterString = 'or_(' + ', '.join(['model.File.id==%s' % ID for ID in fileIDs]) + ')'
        filterString = 'file_q.filter(%s)' % filterString
        cmd = "file_q = eval('%s' % filterString)"
        exec(cmd)
        files = file_q.all()
        if files:
            for file in files:
                if file in collection.files:
                    if 'flash' in session:
                        session['flash'] += 'File %s is already associated to Collection %s ' % (file.id, collection.id)
                    else:
                        session['flash'] = 'File %s is already associated to Collection %s ' % (file.id, collection.id)
                else:
                    collection.files.append(file)
            meta.Session.commit()
            session.save()
        else:
            session['flash'] = u'Sorry, no Files have any of the following IDs: %s' % fileID
            session.save()
        return redirect(url(controller='collection', action='view', id=collection.id))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def disassociate(self, id, otherID):
        """Disassociate BLD Collection id from BLD File otherID.

        """

        if id is None or otherID is None:
            abort(404)
        collection = meta.Session.query(model.Collection).get(int(id)) 
        file = meta.Session.query(model.File).get(int(otherID)) 
        if file is None:
            if collection is None:
                abort(404)
            else:
                session['flash'] = 'There is no File with ID %s' % otherID
        if file in collection.files:
            collection.files.remove(file)
            meta.Session.commit()
            session['flash'] = 'File %s disassociated' % otherID
        else:
            session['flash'] = 'Collection %s was never associated to File %s' % (id, otherID)
        session.save()
        redirect(url(controller='collection', action='view', id=id))

    @h.authenticate
    def export(self, id=None):
        return 'NO COLLECTION EXPORT YET'

    def redirectfromurl(self, URL=None):
        """This method catches all urls that are not caught by the Routes in
        config/routing.py.  It then searches through the Collections for a
        Collection.url=url match and returns the appropriate Collection or an
        error page.

        """
        
        collection = meta.Session.query(model.Collection).filter_by(
            url=URL).first()
        if collection:
            #redirect(url(
            #    controller='collection', action='view', id=collection.id)
            #)
            return self.view(collection.id)
        else:
            abort(404)