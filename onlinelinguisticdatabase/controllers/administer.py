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
import os
import subprocess
import codecs
import unicodedata as ud

from paste.fileapp import FileApp

from pylons import request, response, session, app_globals, tmpl_context as c
from pylons import url, config
from pylons.controllers.util import abort, redirect
from pylons.decorators.rest import restrict

from sqlalchemy import func 

from onlinelinguisticdatabase.lib.base import BaseController, render
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h
import onlinelinguisticdatabase.lib.createSQLiteDBCopy as createSQLiteDBCopy

from formencode.schema import Schema
from formencode.validators import OneOf
from formencode import variabledecode
from formencode import htmlfill, All

try:
    from nltk import Tree
except ImportError:
    pass

try:
    import json
except ImportError:
    import simplejson as json


log = logging.getLogger(__name__)



class GetCharactersForm(Schema):
    allow_extra_fields = True
    filter_extra_fields = True
    field = OneOf([u'transcription', u'phoneticTranscription',
                   u'narrowPhoneticTranscription', u'morphemeBreak'])

def nltk2svg(nltkTree):
    """Return an SVG tree from an NLTK tree.  An SVG tree is a JavaScript object
    that conforms to the format of svg-tree-drawer.js.  That is, it is a dict
    with 'label' and 'children' keys whose values are a string and a list,
    respectively.  See http://weston.ruter.net/projects/syntax-tree-drawer/.

    """

    svgTree = {'label': nltkTree.__dict__['node']}

    def getChildren(svgTree, nltkTree):
        svgTree['children'] = []
        for subTree in nltkTree:
            try:
                svgSubTree = {'label': subTree.__dict__['node']}
                getChildren(svgSubTree, subTree)
                svgTree['children'].append(svgSubTree)
            except AttributeError, ValueError:
                svgTree['children'].append({'label': subTree})

    getChildren(svgTree, nltkTree)

    return json.dumps(svgTree)


def ptb2nltk(ptbTree):
    """Convert a PTB tree to a NLTK one but return None if unparseable."""
    try:
        return Tree(ptbTree)
    except ValueError:
        return None


def nltkModuleIsInstalled():
    """Check if the NLTK module is installed."""
    try:
        from nltk import Tree
        return True
    except ImportError:
        return False


def saveState(name, value):
    """Assign value to name in user's session.  Persist immediately.

    """

    session[name] = value
    session.save()
    session.persist()

def getState(name):
    """Return value of name in user's session.

    """

    return session.get(name, None)


def saveState_(name, value):
    """Assign value to name in app_globals.

    """

    setattr(app_globals, name, value)

def getState_(name):
    """Return value of name from app_globals.

    """

    return getattr(app_globals, name, None)


class AdministerController(BaseController):

    @h.authenticate
    @h.authorize(['administrator'])
    def index(self):
        return render('/derived/administer/index.html')


    @h.authenticate
    def normalizeNFDEverythingCheck(self):
        """normalizeNFDEverythingCheck is called repeatedly by
        pollNormalizeNFDEverything in administer/index.html to see how much of
        normalizeNFDEverything's work is complete.

        """

        response.headers['Content-Type'] = 'application/json'
        normalizeStatus = getState('normalizeNFDEverythingStatus')
        return json.dumps(normalizeStatus)



    @h.authenticate
    @h.authorize(['administrator'])
    def normalizeNFDEverything(self):
        """NFD normalize all relevant data in the database.

        """

        response.headers['Content-Type'] = 'application/json'

        saveState('normalizeNFDEverythingStatus', {
            'statusMsg': 'Normalization has begun.',
            'complete': False
        })

        forms = meta.Session.query(model.Form).all()

        for i in range(len(forms)):
            form = forms[i]
            form.transcription = h.NFD(form.transcription)
            try:
                form.phoneticTranscription = h.NFD(form.phoneticTranscription)
            except TypeError:
                pass
            try:
                form.narrowPhoneticTranscription = h.NFD(form.narrowPhoneticTranscription)
            except TypeError:
                pass
            form.morphemeBreak = h.NFD(form.morphemeBreak)
            form.morphemeGloss = h.NFD(form.morphemeGloss)
            form.comments = h.NFD(form.comments)
            form.speakerComments = h.NFD(form.speakerComments)
            try:
                form.syntacticCategoryString = h.NFD(form.syntacticCategoryString)
            except TypeError:
                pass
            try:
                form.morphemeBreakIDs = h.NFD(form.morphemeBreakIDs)
            except TypeError:
                pass
            try:
                form.morphemeGlossIDs = h.NFD(form.morphemeGlossIDs)
            except TypeError:
                pass
            try:
                form.breakGlossCategory = h.NFD(form.breakGlossCategory)
            except TypeError:
                pass
            for gloss in form.glosses:
                gloss.gloss = h.NFD(gloss.gloss)

            if i != 0 and i % 100 == 0:
                saveState('normalizeNFDEverythingStatus', {
                    'statusMsg': '%d forms normalized.' % i,
                    'complete': False
                })
                meta.Session.commit()

        meta.Session.commit()

        files = meta.Session.query(model.File).all()

        for i in range(len(files)):
            file = files[i]
            file.name = h.NFD(file.name)
            file.description = h.NFD(file.description)
            if i != 0 and i % 100 == 0:
                saveState('normalizeNFDEverythingStatus', {
                    'statusMsg': '%d files normalized.' % i,
                    'complete': False
                })
                meta.Session.commit()

        meta.Session.commit()


        collections = meta.Session.query(model.Collection).all()

        for i in range(len(collections)):
            collection = collections[i]
            collection.title = h.NFD(collection.title)
            collection.type = h.NFD(collection.type)
            if collection.url:
                collection.url = h.NFD(collection.url)
            collection.description = h.NFD(collection.description)
            collection.contents = h.NFD(collection.contents)

            if i != 0 and i % 100 == 0:
                saveState('normalizeNFDEverythingStatus', {
                    'statusMsg': '%d collections normalized.' % i,
                    'complete': False
                })
                meta.Session.commit()

        meta.Session.commit()

        saveState('normalizeNFDEverythingStatus', {
            'statusMsg': 'All forms, files and collections normalized.',
            'complete': True
        })


    @h.authenticate
    @h.authorize(['administrator'])
    def recomputeMorphemeReferences(self):
        """Compute the values of Form.morphemeBreakIDs, Form.morphemeGlossIDs
        and Form.syntacticCategoryString for each Form in the database.

        WARNING, this is a computationally intensive and long-running script.
        With a database of 20,000 Forms, this took about 20 minutes to run on
        a MBP 2.26GHz 2GB ram.

        """

        highestID = meta.Session.query(func.max(model.Form.id)).first()[0]
        for i in range(1, int(highestID) + 1):
            form = meta.Session.query(model.Form).get(i)
            if form:
                syntacticCategoryString = form.syntacticCategoryString
                form.getMorphemeIDLists(meta, model)
                meta.Session.commit()
            i += 1
        meta.Session.commit()

        session['flash'] = 'Morpheme references have been recomputed.'
        session.save()

        return render('/derived/administer/index.html')


    @h.authenticate
    @h.authorize(['administrator'])
    def recomputeMorphemeReferences_(self):
        """Compute the values of Form.morphemeBreakIDs, Form.morphemeGlossIDs
        and Form.syntacticCategoryString for each Form in the database.

        WARNING, this is a computationally intensive and long-running script.
        With a database of 20,000 Forms, this took about 20 minutes to run on
        a MBP 2.26GHz 2GB ram.
        
        """

        i = 1
        forms = meta.Session.query(model.Form).all()
        for form in forms:
            syntacticCategoryString = form.syntacticCategoryString
            form.getMorphemeIDLists(meta, model)
            meta.Session.commit()
            i += 1
        meta.Session.commit()

        session['flash'] = 'Morpheme references have been recomputed.'
        session.save()

        return render('/derived/administer/index.html')


    @h.authenticate
    @h.authorize(['administrator'])
    def createSQLiteDBCopy(self):
        """Create a SQLite3 db file containing all of the data in the MySQL
        database.

        """

        createSQLiteDBCopy.createSQLiteDBCopy()

        session['flash'] = 'SQLite3 copy of database created.'
        session.save()

        return render('/derived/administer/index.html')

    @h.authenticate
    @h.authorize(['administrator'])
    def getSVGTree(self, id):
        """Draw a tree using NLTK and the svg-tree-drawer JavaScript library.
        
        """

        # PTB Tree
        #ptbTree = '(S (NP (N John)) (VP (V ran)))'
        #ptbTree = '(TOP (S (NP-SBJ (PRP It)) (VP (VBZ has) (NP (NP (DT no) (NN bearing)) (PP-DIR (IN on) (NP (NP (PRP$ our) (NN work) (NN force)) (NP-TMP (NN today)))))) (. .)))'
        #ptbTree = u"(TP (DP (D the) (NP (NP (N dog)) (CP (DP 0) (C' (C that) (TP (DP I) (T' (T 0_PAST) (VP (V see) (DP who)))))))) (T' (T 0_PAST) (VP (V be) (AP (A black)))))"
        #ptbTree = u'(TOP (S (NP-SBJ (NP (NNP Pierre) (NNP Vinken)) (, ,) (ADJP (NP (CD 61) (NNS years)) (JJ old)) (, ,)) (VP (MD will) (VP (VB join) (NP (DT the) (NN board)) (PP-CLR (IN as) (NP (DT a) (JJ nonexecutive) (NN director))) (NP-TMP (NNP Nov.) (CD 29)))) (. .)))'

        ptbTree = id

        # NLTK Tree
        nltkTree = ptb2nltk(ptbTree)

        # SVG Tree
        if nltkTree:
            svgTree = nltk2svg(nltkTree)
            result = h.literal(svgTree)
        else:
            result = u'Invalid Tree'

        return result


    @h.authenticate
    @h.authorize(['administrator'])
    def drawTreeTest(self):
        """Draw a tree using NLTK, the Qtree TeX package, and ImageMagick.
        
        This doesn't really work.  It is very slow (esp. XeLaTeX typesetting)
        and the trees often spill over the page and are cut up.

        """

        report = []

        def getSubprocess(programName):
            try:
                return subprocess.Popen([programName], shell=False,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            except OSError:
                return None

        def programIsInstalled(command, name, check):
            try:
                process = getSubprocess(command)
                communication = process.communicate()
                response = communication[0].decode('utf-8')
                if check in response:
                    result = True
                else:
                    result = False
            except AttributeError:
                result = False
            return result

        # See if NLTK is installed
        nltkInstalled = nltkModuleIsInstalled()

        # See if XeLaTeX is installed
        xelatexInstalled = programIsInstalled('xelatex', 'XeLaTeX',
                                            'This is XeTeX')

        # See if ImageMagick is installed
        imagemagickInstalled = programIsInstalled('convert', 'ImageMagick',
                                            'ImageMagick')

        if not nltkInstalled or not xelatexInstalled or not imagemagickInstalled:
            session['flash'] = 'Dependencies for Tree drawing are not installed'
            session.save()
            return render('/derived/administer/index.html')

        # Create the Qtree using NLTK's nltk.Tree class
        from nltk import Tree
        #tree = Tree('(TOP (S (NP-SBJ (PRP It)) (VP (VBZ has) (NP (NP (DT no) (NN bearing)) (PP-DIR (IN on) (NP (NP (PRP$ our) (NN work) (NN force)) (NP-TMP (NN today)))))) (. .)))')
        tree = Tree(u"(TP (DP (D the) (NP (NP (N dog)) (CP (DP 0) (C' (C that) (TP (DP I) (T' (T 0_PAST) (VP (V see) (DP who)))))))) (T' (T 0_PAST) (VP (V be) (AP (A black)))))")
        tree = tree.pprint_latex_qtree()

        # Write the XeLaTeX file
        filesPath = config['app_conf']['permanent_store']
        treesPath = os.path.join(filesPath, 'trees')
        if not os.path.exists(treesPath):
            os.makedirs(treesPath)

        formID = str(11)
        formTreesPath = os.path.join(treesPath, formID)
        if not os.path.exists(formTreesPath):
            os.makedirs(formTreesPath)

        xelatexDoc = u'%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s\n%s' % (
            '\documentclass{article}',
            '\usepackage{fontspec}',
            '\setmainfont{Times}',
            '\usepackage{qtree}',
            '\\begin{document}',
            '\pagestyle{empty}',
            '\\tiny',
            '%s' % tree,
            '\end{document}'
        )

        xelatexDocPath = os.path.join(formTreesPath, 'tree.tex')
        pdfDocPath = os.path.join(formTreesPath, 'tree.pdf')
        pngDocPath = os.path.join(formTreesPath, 'tree.png')

        xelatexDocFile = codecs.open(xelatexDocPath, 'w', 'utf-8')
        xelatexDocFile.write(xelatexDoc)
        xelatexDocFile.close()

        # Typeset the XeLaTeX file
        if not os.path.exists(pdfDocPath):
            outDirOpt = '-output-directory=%s' % formTreesPath
            args = ('xelatex', outDirOpt, xelatexDocPath,
                    '-interaction=nonstopmode')
            s = subprocess.call(args, shell=False, stdout=subprocess.PIPE)

        # Convert the PDF to a PNG
        if not os.path.exists(pngDocPath):
            args = ('convert', '-density',  '400', pdfDocPath, '-resize', '75%',
                '-flatten', '-trim', pngDocPath)
            s = subprocess.call(args, shell=False, stdout=subprocess.PIPE)

        fileReference = url('gettree', id=formID)
        img = '<img src="%s" />' % fileReference

        c.img = img

        return render('/derived/administer/index.html')


    #@h.authenticate_ajax
    #@h.authorize(['administrator'])
    @restrict('POST')
    def getCharacters(self):

        schema = GetCharactersForm()
        values = variabledecode.variable_decode(request.params)
        try:
            result = schema.to_python(values)
        except Invalid, e:
            result = {'valid': False, 'errors': e.unpack_errors()}
        else:
            # Count all the characters tokens by type
            result = {}
            forms = meta.Session.query(model.Form).all()
            field = values['field']
            fieldBag = ''.join([getattr(f, field) for f in forms
                                if getattr(f, field)])
            for c in fieldBag:
                try:
                    result[c] += 1
                except KeyError:
                    result[c] = 1

            # Sort the tokens by count in descending order
            result = [[k, result[k]] for k in result]
            result = sorted(result, key=lambda x: x[1], reverse=True)

            # Add some character information
            result = [[c[0], c[1], h.getUnicodeNames(c[0]),
                       h.getUnicodeCodePoints(c[0]), ud.normalize('NFC', c[0]),
                       h.getUnicodeCodePoints(ud.normalize('NFC', c[0]))]
                     for c in result]

            result = {'valid': True, 'response': result}

        response.headers['Content-Type'] = 'application/json'
        return json.dumps(result)