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

"""This module contains functionality for converting OLD-specific markup into
HTML.

Basically, there are two types of OLD markup:

1. embedding markup -- replace expression with a representation of the entity
2. linking markup -- replace expression with a link to the entity

Embedding markup uses brackets around the ID [1] while linking markup uses
parentheses (1).

Note: a complication is that the contents field of Collections contains Form
embedding markup that triggers the creation of relational associations between
the Collection and the Forms referenced in its contents.  Collection contents
also allow the possibility of references to the enumerators of the example
tables containing the representation of the embedded form.  For these reasons,
the handling of Form embedding markup is handled in collection.py.  It might be
desirable to modularize that code and bring parts of it here or else create an
alternate/general-purpose Form embedding markup function here...

Linking Markup
==============

 - form(1), file(1), collection(1), speaker(1), user(1), researcher(1)
    - see linkToOLDEntitites below
    
Embedding Markup
================

- form[1]

  - see embedForms below
  - see also collection.getCollectionContents(), collection.getFormAsHTMLTable()
    and lib.oldCoreObjects.form.getIGTHTMLTable()

- collection[1]

  - see embedContentsOfCollections below

- file[1]

  - see embedFiles below

"""

import os
import shutil
import re
import helpers as h
import codecs
import htmlentitydefs
import string

from docutils import core

from pylons import session, app_globals, config, url

from sqlalchemy import desc

import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta


def linkToOLDEntitites(input):
    """OLDEntities2Link searches input for strings like:
        
        'form(99)'
        'researcher(22)(Mary Smith)'
    
    and returns input with these strings replaced by HTML links:
    
        "<a href='form/view/99' title='Click to view Form 99'>
            Form 99</a>" 
        "<a href='researcher/view/22' title='Click to view Researcher 22'>
            Mary Smith</a>",
    
    respectively.
    
    """

    def ref2link(match):
        controller = match.group(2).lower()
        if controller == 'user':
            controller = 'researcher'
        id = match.group(3)
        defaultText = '%s %s' % (controller.capitalize(), str(id))
        try:
            text = match.group(5)
            if not text:
                text = defaultText
        except IndexError:
            text = defaultText
        URL = url(controller=controller, action='view', id=id)
        title = 'Click to view %s %s' % (controller.capitalize(), str(id))
        return "<a href='%s' title='%s'>%s</a>" % (URL, title, text)

    patt = re.compile('(([Ff]orm|[Ff]ile|[Cc]ollection|[Ss]peaker|[Uu]ser|[Rr]esearcher)\(([0-9]+)\)(\((.+?)\))?)')
    return patt.sub(lambda x: ref2link(x), input)


def embedContentsOfCollections(input):
    """Take a reference to a Collection of the form 'collection[X]' and return
    the contents (verbatim) of Collection with id=X.
    
    This is useful for making Collections whose contents is composed of those
    of other Collections.  The possibility of such Collections means that the
    collection.py 'add' and 'update' actions will need to be changed so that
    such composite Collections have all the right Forms in collection.forms...
    
    """

    def ref2representation(match):
        
        # get collection contents
        id = match.group(2)
        try:
            collection = meta.Session.query(model.Collection).filter_by(id=id).first()
            contents = collection.contents
        except AttributeError:
            contents = u'Warning: There is no Collection with id=%s' % str(id)
        
        # Remove any reStructuredText TOC directives that shouldn't be in an
        #  embedded contents
        #  THIS NEEDS TO BE MORE COMPREHENSIVE.  I.e., remove options, etc...
        contents = contents.replace('.. contents::', '').replace('.. sectnum::', '')
        
        return '\n%s\n' % contents
    
    patt = re.compile('([Cc]ollection\[([0-9]+)\])')
    return patt.sub(lambda x: ref2representation(x), input)


def embedFiles(input):
    """Replace each embedding reference to a File in input with a
    representation of the File referenced.  Do this intelligently so that image
    Files are embedded as <img /> tags, audio files as <audio></audio>, etc.
    
    """

    def ref2representation(match):
        
        # get File
        id = int(match.group(2))
        option = match.group(4)
        if option:
            option = option.strip()
        print option
        try:
            file = meta.Session.query(model.File).get(id)
            fileType = file.getFileType()
            #result = file.getFileMedia(False)
            result = file.getHTMLRepresentation(forCollection=True)
        except AttributeError:
            result = u'Warning: There is no File with id=%s' % str(id)

        return '\n%s\n' % result
    
    patt = re.compile('([Ff]ile\[([0-9]+)( *, *(embed|forCollection) *)?\])')
    return patt.sub(lambda x: ref2representation(x), input)

def embedForms(input):
    """Replace each embedding reference to a Form in input with a
    representation of the Form referenced.
    
    """

    def ref2representation(match):
        
        # get Form
        id = int(match.group(2))
        try:
            form = meta.Session.query(model.Form).filter_by(id=id).first()
            result = form.getIGTHTMLTable()
        except AttributeError:
            result = u'Warning: There is no Form with id=%s' % str(id)

        return '\n%s\n' % result
    
    patt = re.compile('([Ff]orm\[([0-9]+)\])')
    return patt.sub(lambda x: ref2representation(x), input)