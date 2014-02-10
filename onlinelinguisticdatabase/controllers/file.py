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
from pylons.controllers.util import abort, forward, redirect
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

from sqlalchemy.sql import or_
from sqlalchemy import desc

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h


log = logging.getLogger(__name__)


class NewFileForm(Schema):
    """NewFileForm is a Schema for validating the data entered at the Add File page."""
    allow_extra_fields = True
    filter_extra_fields = True
    dateElicited = DateConverter(month_style='mm/dd/yyyy')
    description = UnicodeString()
    speaker = UnicodeString()
    elicitor = UnicodeString()
    utteranceType = UnicodeString()

class NewFileFormDM(NewFileForm):
    dateElicited = DateConverter(month_style='dd/mm/yyyy')

class UpdateFileForm(NewFileForm):
    ID = UnicodeString()

class UpdateFileFormDM(UpdateFileForm):
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
    unit = UnicodeString()

class SearchFileForm(Schema):
    """SearchFile is a Schema for validating the search terms entered at the Search Files page."""
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


class AssociateFileFormForm(Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    formID = Regex(r'^ *[1-9]+[0-9]* *( *, *[1-9]+[0-9]* *)*$', not_empty=True)

def renderAddFile(values=None, errors=None, addUpdate='add'):
    """Function is called by both the add and update actions to create the
    Add File and Update File HTML forms.  The create and save actions can also
    call this function if any errors are present in the input.
    
    """

    # if addUpdate is set to 'update', render update.html instead of add.html
    if addUpdate == 'add':
        form = render('/derived/file/addForm.html')
        c.heading = u'Add a File'
        c.filledForm = htmlfill.render(form, defaults=values, errors=errors)
        page = render('/derived/file/add.html')
    else:
        form = render('/derived/file/updateForm.html')
        c.heading = u'Updating File %s' % c.file.id
        c.filledForm = htmlfill.render(form, defaults=values, errors=errors)
        page = render('/derived/file/update.html')

    return page


def getFileAttributes(file, result, fileSize, fileName, createOrSave):
    """Given a (SQLAlchemy) File object, a result dictionary populated by
    user-entered data and a fileSize calculated in the create action, this
    function populates the appropriate attributes with the appropriate values.
    Function called by both create and save actions.
    
    """
    
    # User-entered Data
    file.description = h.NFD(result['description'])
    # Recording-only Data
    if result['speaker']:
        file.speaker = meta.Session.query(
            model.Speaker).get(int(result['speaker']))
    else:
        file.speaker = None
    if result['elicitor']:
        file.elicitor = meta.Session.query(
            model.User).get(int(result['elicitor']))
    else:
        file.elicitor = None
    file.dateElicited = result['dateElicited']
    file.utteranceType = result['utteranceType']
    if createOrSave == 'create':
        # Data extracted from uploaded file
        fileData = request.POST['fileData']
        file.MIMEtype = guess_type(fileData.filename)[0]
        file.size = fileSize
        file.name = h.NFD(fileName).replace("'", "").replace('"', '')
        file.pathName = os.path.join(
            config['app_conf']['permanent_store'], fileName) 
        # Add the Enterer as the current user
        file.enterer = meta.Session.query(model.User).get(
            int(session['user_id']))
    # OLD-generated Data
    now = datetime.datetime.utcnow()
    if createOrSave == 'create':
        file.datetimeEntered = now
    file.datetimeModified = now
    return file

class FileController(BaseController):
    """File Controller contains actions about OLD Files.  Authorization and
    authentication are implemented by the helper decorators authenticate and
    authorize which can be found in lib/auth.py.
    
    """

    @h.authenticate
    def retrieve(self, path):
        """retrieve action is referenced by the <a>, <img>, <audio>, <video>,
        <embed>, etc. tags.

        """

        path = os.path.join(config['app_conf']['permanent_store'], path)
        app = FileApp(path)
        return forward(app)

    @h.authenticate
    def retrieve_temp(self, path):
        """retrieve_temp action is referenced by the <a> button rendered in
        /derived/file/export.html.

        """

        path = os.path.join(config['app_conf']['temporary_store'], path)
        app = FileApp(path)
        return forward(app) 

    @h.authenticate
    def browse(self):
        """Browse through all Files in the system."""
        file_q = meta.Session.query(model.File).order_by(model.File.name)
        c.paginator = paginate.Page(
            file_q,
            page=int(request.params.get('page', 1)),
            items_per_page = app_globals.file_items_per_page
        )
        c.browsing = True
        return render('/derived/file/results.html')

    @h.authenticate
    def view(self, id):
        """View a BLD File.  Requires a File ID as input."""
        if id is None:
            abort(404)
        file_q = meta.Session.query(model.File)
        try:
            c.file = file_q.get(int(id))
        except ValueError:
            abort(404)
        if c.file is None:
            abort(404)
        return render('/derived/file/view.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def add(self):
        """Display HTML form for adding a new BLD File.  HTML form calls create
        action.
        
        """

        return renderAddFile()

    @h.authenticate
    def search(self, values=None, errors=None):
        """Display HTML form for searching for Files.  HTML form calls query
        action.
        
        """
        
        # if no user-entered defaults are set, make description the default for
        #  searchLocation2
        if not values:
            values = {'searchLocation2': u'description'}
            values['orderByColumn'] = 'id'
        # By default, the additional search restrictors are hidden
        c.viewRestrictors = False
        
        # Get today in MM/DD/YYYY file    
        c.today = datetime.date.today().strftime('%m/%d/%Y')
        html = render('/derived/file/search.html')      
        return htmlfill.render(html, defaults=values, errors=errors)

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def create(self):
        """Enter BLD File data into the database.  This is the action referenced
        by the HTML form rendered by the add action.
        
        """

        dateFormat = session.get('userSettings').get('dateFormat')
        if dateFormat == 'DD/MM/YYYY':
            schema = NewFileFormDM()
        else:
            schema = NewFileForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            return renderAddFile(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                )
            )
        else:
            # Make sure that the file type is allowed for upload
            #  and return the form if this is not the case
            if request.POST['fileData'] == '':
                return renderAddFile(
                    values=values,
                    errors={'fileData': 'please enter a file to upload'}
                )                
            fileData = request.POST['fileData']
            fileType = guess_type(fileData.filename)[0]
            if fileType not in app_globals.allowedFileTypes:
                return renderAddFile(
                    values=values,
                    errors={'fileData': 'that file type is not allowed'}
                )
            # All is good: save the file to permanent_store (see development.ini)
            fileName = fileData.filename.replace(os.sep, '_').replace(
                "'", "").replace('"', '').replace(' ', '_')
            filePathName = os.path.join(
                config['app_conf']['permanent_store'],
                fileName
            )
            # If the file already exists in permanent_store add a number to the end
            #  until we have a unique file name
            while os.path.exists(filePathName):
                patt = re.compile('[0-9]+')
                if patt.match(os.path.splitext(fileName)[0].split('_')[-1]):
                    fileName = '_'.join(os.path.splitext(fileName)[0].split('_')[:-1]) + '_' + str(int(os.path.splitext(fileName)[0].split('_')[-1]) + 1) + os.path.splitext(fileName)[1]
                else:                    
                    fileName = os.path.splitext(fileName)[0] + '_' + str(1) + os.path.splitext(fileName)[1]
                filePathName = os.path.join(
                    config['app_conf']['permanent_store'],
                    fileName
                )   
            # Create the permanent file, copy the file data to it and close
            permanent_file = open(
                filePathName,
                'wb'
            )
            shutil.copyfileobj(fileData.file, permanent_file)
            fileData.file.close()
            # Get the size of the newly uploaded file before closing it
            fileSize = os.path.getsize(permanent_file.name)
            permanent_file.close()
            # Create a new File SQLAlchemy Object and populate its attributes with the results
            file = model.File()
            file = getFileAttributes(file, result, fileSize, fileName, 'create')
            # Enter the data
            meta.Session.add(file)
            meta.Session.commit()
            # Issue an HTTP redirect
            redirect(url(controller='file', action='view', id=file.id))

    @h.authenticate
    @restrict('POST')
    def query(self):
        """Query action validates the search input values; 
        if valid, query stores the search input values in the session and redirects to results;
        if invalid, query redirect to search action (though I don't think it's possible to enter an invalid query...).  
        Query is the action referenced by the HTML form rendered by the search action."""
        schema = SearchFileForm()
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
            # result is a Python dict nested structure representing the user's query
            # we put result into session['fileSearchValues'] so that the results action
            # can use it to build the SQLAlchemy query
            session['fileSearchValues'] = result
            session.save() 
            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(controller='file', action='results')
            return "Moved temporarily"

    @h.authenticate
    def results(self):
        """Results action uses the filterSearchQuery helper function to build
        a query based on the values entered by the user in the search file."""
        if 'fileSearchValues' in session:
            result = session['fileSearchValues']
            file_q = meta.Session.query(model.File)
            file_q = h.filterSearchQuery(result, file_q, 'File')
        else:
            file_q = meta.Session.query(model.File)
        c.paginator = paginate.Page(
            file_q,
            page=int(request.params.get('page', 1)),
            items_per_page = app_globals.file_items_per_page
        )
        return render('/derived/file/results.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def update(self, id=None):
        """Displays an HTML form for updating a BLD File.  The HTML form calls
        the save action.
        
        """
        
        if id is None:
            abort(404)
        file_q = meta.Session.query(model.File)
        file = file_q.filter_by(id=id).first()
        if file is None:
            abort(404)
        c.file = file
        values = {
            'ID': file.id,
            'description': file.description,
            'elicitor': file.elicitor_id,
            'speaker': file.speaker_id,
            'utteranceType': file.utteranceType
        }
        if file.dateElicited:
            dateFormat = session.get('userSettings').get('dateFormat')
            if dateFormat == 'DD/MM/YYYY':
                values['dateElicited'] = file.dateElicited.strftime('%d/%m/%Y')
            else:
                values['dateElicited'] = file.dateElicited.strftime('%m/%d/%Y')

        return renderAddFile(values, None, 'update')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def save(self):
        """Updates existing BLD File.  This is the action referenced by the HTML
        form rendered by the update action.
        
        """

        dateFormat = session.get('userSettings').get('dateFormat')
        if dateFormat == 'DD/MM/YYYY':
            schema = UpdateFileFormDM()
        else:
            schema = UpdateFileForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            id = int(values['ID'])
            file_q = meta.Session.query(model.File)
            file = file_q.filter_by(id=id).first()
            c.file = file
            return renderAddFile(
                values=values,
                errors=variabledecode.variable_encode(
                    e.unpack_errors() or {},
                    add_repetitions=False
                ),
                addUpdate='update'
            )
        else:
            # Get the File object with ID from hidden field in update.html
            file_q = meta.Session.query(model.File)
            file = file_q.filter_by(id=result['ID']).first()
            # Populate the File's attributes with the data from the user-entered
            #  result dict
            file = getFileAttributes(file, result, file.size, file.name, 'save')
            # Commit the update
            meta.Session.commit()
            # Issue an HTTP redirect
            response.status_int = 302
            response.headers['location'] = url(controller='file', action='view', id=file.id)
            return "Moved temporarily" 

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def delete(self, id):
        """Delete the BLD file with ID=id.

        """

        if id is None:
            abort(404)
        file_q = meta.Session.query(model.File)
        file = file_q.get(int(id))
        if file is None:
            abort(404)
        # Delete File info in database
        meta.Session.delete(file)
        meta.Session.commit()
        # Delete file's media in files folder
        filePathName = os.path.join(
            config['app_conf']['permanent_store'],
            file.name
        )
        try:
            os.remove(filePathName)
        except OSError:
            pass
        # Create the flash message
        session['flash'] = "File %s has been deleted" % id
        session.save()
        redirect(url(controller='file', action='results'))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def associate(self, id):
        """Display the page for associating a BLD File with id=id to a BLD Form.
        The HTML form in the rendered page references the link action.

        """

        if id is None:
            abort(404)
        c.file = meta.Session.query(model.File).get(int(id))  
        if c.file is None:
            abort(404)
        c.associateForm = render('/derived/file/associateForm.html')

        return render('/derived/file/associate.html')

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    @restrict('POST')
    def link(self, id):
        """Associate BLD File with id=id to a BLD Form.  The ID of the Form is
        passed via a POST form.  This "ID" may in fact be a comma-separated list
        of Form IDs.

        """

        schema=AssociateFileFormForm()

        values = dict(request.params)
        try:
            result = schema.to_python(dict(request.params), c)
        except Invalid, e:
            c.file = meta.Session.query(model.File).filter_by(id=id).first()
            associateForm = render('/derived/file/associateForm.html')
            errors = variabledecode.variable_encode(
                e.unpack_errors() or {},
                add_repetitions=False
            )
            c.associateForm = htmlfill.render(associateForm, defaults=values,
                                              errors=errors)
            return render('/derived/file/associate.html')

        else:
            # Get the File
            if id is None:
                abort(404)
            file = meta.Session.query(model.File).get(int(id))  
            if file is None:
                abort(404)
    
            # Get the Form(s)
            formID = result['formID']
            patt = re.compile('^[0-9 ]+$')
            formIDs = [int(ID.strip().replace(' ', '')) for ID in formID.split(',')
                       if patt.match(ID)]
            forms = meta.Session.query(model.Form).filter(
                model.Form.id.in_(formIDs)).all()

            if forms:
                for form in forms:
                    if form in file.forms:
                        msg = '<p>Form %s is already associated ' % form.id + \
                              'to File %s.</p>' % file.id
                        h.appendMsgToFlash(h.literal(msg))
                    else:
                        if h.userIsAuthorizedToAccessForm(session['user'], form):
                            file.forms.append(form)
                            msg = '<p>Form %d successfully ' % form.id + \
                                  'associated to File %d.' % file.id
                            h.appendMsgToFlash(h.literal(msg))
                        else:
                            msg = '<p>Sorry, you are not authorized to ' + \
                                  'access form %d.</p>' % form.id
                            h.appendMsgToFlash(h.literal(msg))
                meta.Session.commit()
                session.save()
            else:
                msg = u'<p>Sorry, no Forms have any of the following ' + \
                                    u'IDs: %s.</p>' % formID
                session['flash'] = h.literal(msg)
                session.save()
    
            return redirect(url(controller='file', action='view', id=file.id))

    @h.authenticate
    @h.authorize(['administrator', 'contributor'])
    def disassociate(self, id, otherID):
        """Disassociate BLD File id from BLD Form otherID."""
        if id is None or otherID is None:
            abort(404)
        file = meta.Session.query(model.File).get(int(id)) 
        form = meta.Session.query(model.Form).get(int(otherID)) 
        if form is None:
            if file is None:
                abort(404)
            else:
                session['flash'] = 'There is no Form with ID %s' % otherID
        if form in file.forms:
            file.forms.remove(form)
            meta.Session.commit()
            session['flash'] = 'Form %s disassociated' % otherID
        else:
            session['flash'] = 'File %s was never associated to Form %s' % (id, otherID)
        session.save()
        redirect(url(controller='file', action='view', id=id))

    @h.authenticate
    def export(self, id=None):
        """Export the BLD Files matching the search criteria
        as a .zip archive.  ."""
        # Get the Files that match the search and get their full path names
        try:
            result = session['fileSearchValues']
            file_q = meta.Session.query(model.File)
            file_q = h.filterSearchQuery(result, file_q, 'File')
            files = file_q.all()
        except KeyError:
            files = meta.Session.query(model.File).all()

        fileNames = [os.path.join(config['app_conf']['permanent_store'], file.name) for file in files]

        # Create the .zip file and write the Files to it
        #  Python 2.5 was raising a UnicodeDecodeError when ZipFile.write was
        #  passed unicode arguments, so I've str()-ed them
        zfileName = str('%s_%s_file_export.zip' % \
            (session['user_firstName'].lower(), session['user_lastName'].lower()))
        zfileName = str(
            os.path.join(config['app_conf']['temporary_store'], zfileName))
        zout = zipfile.ZipFile(zfileName, "w")
        for fileName in fileNames:
            zout.write(str(fileName), os.path.basename(str(fileName)))
        zout.close()
        c.zfileName = os.path.basename(zfileName)
        c.zfileSize = os.path.getsize(zfileName)
        c.fileNames = [(file.name, os.path.getsize(os.path.join(config['app_conf']['permanent_store'], file.name))) for file in files]
        return render('/derived/file/export.html')
