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

import re
import datetime
import logging
from os import path
from random import randrange
try:
    import json
except ImportError:
    import simplejson as json
from pylons import app_globals, url, session
import helpers as h

log = logging.getLogger(__name__)

class Column(object):
    """Empty class that the fromJSON() methods of FormBackup and
    CollectionBackup use to convert their dicts into objects that are attributes
    of FormBackup and CollectionBackup.  See FormBackup.fromJSON() and
    CollectionBackup.fromJSON() below.

    """

    pass



################################################################################
#################  Form and FormBackup Classes  ################################
################################################################################


class Form(object):

    def get_sublist_splitter(self, word_lists, max_length, decrementor):
        """Return a function that splits lists of strings into lists of lists of strings.

        :param list word_lists: a list of sublists of equal length where the elements
            of the sublists are strings representing words.
        :param int max_length: the maximum length permitted for the abstract sublist that
            is constructed by concatenating the longest word at each position across all
            sublists.
        :param int decrementor: a value to remove from ``max_length`` whenever a new
            sublist is created.
        :returns: a function that splits a list of words into a list of sublists of words.

        This method returns a splitter function.  The splitter function takes a list of
        strings (words) as input and returns a list of sublists of word strings.  The way
        the sublists are constructed is determined by the lengths of the words in
        ``word_lists``.

        """
        word_tuples = zip(*word_lists)
        # Get a list of the lengths of the longest string in each tuple_ of word_tuples
        longestLengths = [max([len(word) for word in tuple_]) for tuple_ in word_tuples]
        lengthsList = [[]]
        for length in longestLengths:
            lengthsList[-1].append(length)
            if sum(lengthsList[-1]) >= max_length:
                # Oops we appended too much!
                max_length = max_length - decrementor
                # If there's only one length in the sublist, leave it there and append a new sublist
                if len(lengthsList[-1]) == 1:
                    lengthsList.append([])
                # Otherwise, remove the last length and add it to a newly appended sublist
                else:
                    lengthToMove = lengthsList[-1].pop()
                    lengthsList.append([lengthToMove])
        start_end_doubles = [
            (sum([len(x) for x in lengthsList[:i]]),
             sum([len(x) for x in lengthsList[:i]]) + len(lengthsList[i]))
            for i in range(len(lengthsList))
        ]
        return lambda l: [l[start:end] for start, end in start_end_doubles]

    def listifyCoreData(self, max_length=55, decrementor=3):
        """Generate lists of sublists of words for the IGT-alignable values.

        :param int max_length: maximum length (in characters) of the longest
            row in an IGT representation.
        :param int decrementor: value used to decrement ``max_length`` on each
            successive row (responsible for the "cascade" effect).
        :returns: ``None``.
        :side-effects: valuates a subset of the following attributes of the form:
            ``transcriptionList``
            ``narrowPhoneticTranscriptionList``
            ``phoneticTranscriptionList``
            ``morphemeBreakList`` (and ``morphemeBreakIDsList``)
            ``morphemeGlossList`` (and ``morphemeGlossIDsList``)

        """

        alignable_attrs = self.alignable_igt_attrs
        alignables = [(attr, getattr(self, attr).split())
                            for attr in alignable_attrs]
        sublist_splitter = self.get_sublist_splitter(
            [value for attr, value in alignables], max_length, decrementor)
        for attr, value in alignables:
            setattr(self, '%sList' % attr, sublist_splitter(value))
        if 'morphemeBreak' in alignable_attrs:
            morphemeBreakIDs = json.loads(self.morphemeBreakIDs) 
            self.morphemeBreakIDsList = sublist_splitter(morphemeBreakIDs)
        if 'morphemeGloss' in alignable_attrs:
            morphemeGlossIDs = json.loads(self.morphemeGlossIDs)
            self.morphemeGlossIDsList = sublist_splitter(morphemeGlossIDs)

    def getMorphemeGlossTuples(self, validDelimiters=[' ', '-', '=']):
        """From morphemeBreak and morphemeGloss, create list
        self.morphemeGlossTuples as a list of morpheme-gloss tuples (or lists).
        Do so only if morphembeBreak and morphemeGloss have equal numbers of
        morphemes/glosses.

        Allow for the possibility of multiple delimiters (e.g., ' ', '-' or '=')
        and keep track of the previous delimiter so that the original strings
        can be recreated.

        Example:
        
            self.morphemeBreak = u"kn=ts-q'way'ilc pintk"
            self.morphemeGloss = u'1sERG=CUST-dance always"

            self.morphemeGlossTuples = [(u'kn', u'1sERG', u''),
                                        (u'ts', u'CUST', u'='),
                                        (u'q'way'ilc', u'dance', u'-'),
                                        (u'pintk', u'always', u' ')]

        """

        previousDelimiter = 0
        breaks = []
        gloss = []
        delimiters = []
 
        # Goes through morphemeBreak char by char
        for i in range(len(self.morphemeBreak)):
            
            # Check if char is delimiter
            if self.morphemeBreak[i] in validDelimiters:
                # If it is not the first delimiter, add to list and take all text
                #  since previous delimiter.
                if previousDelimiter != 0:
                    delimiters.append(self.morphemeBreak[previousDelimiter])
                    breaks.append(self.morphemeBreak[previousDelimiter+1:i])
                # If it is first delimiter, take all text since beginning and
                #  append empty delimiter to list.
                else:
                    delimiters.append(u'')
                    breaks.append(self.morphemeBreak[previousDelimiter:i])
                previousDelimiter = i
            
            # If end of break, take the rest.
            elif i == len(self.morphemeBreak) - 1:
                delimiters.append(self.morphemeBreak[previousDelimiter])
                breaks.append(self.morphemeBreak[previousDelimiter+1:i+1])

        previousDelimiter = 0

        # Ditto for the gloss, but no need to append delimiters this time.
        for i in range(len(self.morphemeGloss)):
            if self.morphemeGloss[i] in validDelimiters:
                if previousDelimiter != 0:
                    gloss.append(self.morphemeGloss[previousDelimiter + 1:i])
                else:
                    gloss.append(self.morphemeGloss[previousDelimiter:i])
                previousDelimiter = i
            elif i == len(self.morphemeGloss) - 1:
                gloss.append(self.morphemeGloss[previousDelimiter+1:i+1])
 
        # Makes sure lists are equal length and no empty morphemes (no 2
        #  delimiters in a row)
        if len(breaks) == len(gloss) and not '' in breaks and not '' in gloss:
            self.morphemeGlossTuples = zip(breaks, gloss, delimiters)
        else:
            self.morphemeGlossTuples = []


    def getMorphemeIDLists(self, meta, model):
        """This method takes the morpheme-gloss components of a Form and looks
        for matches in other Forms.
        
        Specifically, it looks for Forms whose transcription matches the morpheme
        string and whose morphemeGloss matches the gloss string.  First it looks
        for perfect matches (i.e., a Form whose morphemeBreak matches the
        morpheme and whose morphemeGloss matches the gloss) and if none are
        found it looks for "half-matches" and if none of those are found, then
        form.morhemeBreakIDs and form.morhemeGlossIDs are empty lists.
    
        If any kind of match is found, the id, morpheme/gloss and syntactic
        category of the matching Forms are stored in a list of tuples:
        (id, mb/gl, sc).
        
        In short, this method generates values for the morphemeBreakIDs,
        morphemeGlossIDs and syntacticCategoryString attributes.
        
        """
        
        morphemeBreakIDs = []
        morphemeGlossIDs = []
        syncatStr = []
        # Get the valid morpheme/gloss delimiters, e.g., '-', '=', ' ', as a
        #  disjunctive regex
        validDelimiters = app_globals.morphDelimiters
        patt = '[%s]' % ''.join(validDelimiters)
        
        if self.morphemeBreak and self.morphemeGloss and \
        len(self.morphemeBreak.split()) == len(self.morphemeGloss.split()) and \
        [len(re.split(patt, x)) for x in self.morphemeBreak.split()] == \
        [len(re.split(patt, x)) for x in self.morphemeGloss.split()]:
            morphemeBreak = self.morphemeBreak
            morphemeGloss = self.morphemeGloss
            mbWords = morphemeBreak.split()
            mgWords = morphemeGloss.split()
            scWords = morphemeBreak.split()[:]
            for i in range(len(mbWords)):
                mbWordIDList = []
                mgWordIDList = []
                mbWord = mbWords[i]
                mgWord = mgWords[i]
                scWord = scWords[i]
                patt = '([%s])' % ''.join(validDelimiters)
                mbWordMorphemesList = re.split(patt, mbWord)[::2] 
                mgWordMorphemesList = re.split(patt, mgWord)[::2]
                scWordMorphemesList = re.split(patt, scWord)
                for ii in range(len(mbWordMorphemesList)):
                    morpheme = mbWordMorphemesList[ii]
                    gloss = mgWordMorphemesList[ii]
                    matches = []
                    if morpheme and gloss:
                        matches = meta.Session.query(model.Form).filter(
                            model.Form.morphemeBreak==morpheme).filter(
                            model.Form.morphemeGloss==gloss).all()
                    # If one or more Forms match both gloss and morpheme, append a
                    #  list of the IDs of those Forms in morphemeBreakIDs and
                    #  morphemeGlossIDs
                    if matches:
                        mbWordIDList.append([f.syntacticCategory and
                            (f.id, f.morphemeGloss, f.syntacticCategory.name) 
                            or (f.id, f.morphemeGloss, None) for f in matches])
                        mgWordIDList.append([f.syntacticCategory and
                            (f.id, f.morphemeBreak, f.syntacticCategory.name) 
                            or (f.id, f.morphemeBreak, None) for f in matches])
                        scWordMorphemesList[ii * 2] = matches[0].syntacticCategory and \
                        matches[0].syntacticCategory.name or '?'
                    # Otherwise, look for Forms that match only gloss or only
                    #  morpheme and append respectively
                    else:
                        morphemeMatches = []
                        if morpheme:
                            morphemeMatches = meta.Session.query(
                                model.Form).filter(
                                model.Form.morphemeBreak==morpheme).all()
                        if morphemeMatches:
                            mbWordIDList.append([f.syntacticCategory and
                                (f.id, f.morphemeGloss, f.syntacticCategory.name) 
                                or (f.id, f.morphemeGloss, None)
                                for f in morphemeMatches])
                        else:
                            mbWordIDList.append([])
                        glossMatches = []
                        if gloss:
                            glossMatches = meta.Session.query(
                                model.Form).filter(
                                model.Form.morphemeGloss==gloss).all()
                        if glossMatches:
                            mgWordIDList.append([f.syntacticCategory and
                                (f.id, f.morphemeBreak, f.syntacticCategory.name)
                                or (f.id, f.morphemeBreak, None)
                                for f in glossMatches])
                        else:
                            mgWordIDList.append([])
                        scWordMorphemesList[ii * 2] = '?'
                morphemeBreakIDs.append(mbWordIDList)
                morphemeGlossIDs.append(mgWordIDList)
                syncatStr.append(''.join(scWordMorphemesList))
        else:
            morphemeBreakIDs = [[[]]]
            morphemeGlossIDs = [[[]]]
            syncatStr = []
        # Convert the data structure into JSON for storage as a string in the DB
        self.morphemeBreakIDs = unicode(json.dumps(morphemeBreakIDs))
        self.morphemeGlossIDs = unicode(json.dumps(morphemeGlossIDs))
        self.syntacticCategoryString = unicode(' '.join(syncatStr))

    def getHTMLRepresentation(self, **kwargs):
        """Return an HTML representation of the Form.
        
        If forCollection=True, we position the Form Actions dropdown menu
        lower to accomodate the example numbers.

        If forFile=True, we do not show the associated Files of the Form,
        as to avoid an infinite loop.  Also, we provide a 'disassociate' button
        in the formMenu so that the form can be disassociated from the file.

        """

        # Return an error message if the user is not authorized to view the form
        if not h.userIsAuthorizedToAccessForm(session['user'], self):
            return 'Sorry, you do not have access to form %d.' % self.id

        # Generate a random number to try to ensure unique HTML IDs for Form
        #  representations.  ID is insufficient as the same form may be embedded
        #  twice in a page
        self.uniqueNo = randrange(0,1000)

        self.forCollection = False
        self.forFile = False
        for k in kwargs:
            setattr(self, k, kwargs[k])

        HTMLRepresentation = u'<div id="form%d_%dDiv">\n' % (
            self.id, self.uniqueNo)

        # Only show the form menu if this is not a form backup
        if not getattr(self, 'formBackup', False):
            HTMLRepresentation += self.getFormMenu()

        HTMLRepresentation += self.getIGTHTMLTable()
        HTMLRepresentation += self.getAdditionalData()

        # Forms displayed under files and formBackups do not need to display
        #  associated files.
        if not getattr(self, 'fileID', None) and \
            not getattr(self, 'formBackup', False):
            HTMLRepresentation += self.getAssociatedFiles()

        HTMLRepresentation += u'\n</div>'

        return HTMLRepresentation

    def getFormMenu(self):
        """Returns the YUI "+" menu for forms.

        """

        forCollection = getattr(self, 'forCollection', False)
        forFile = getattr(self, 'forFile', False)

        updateURL = url(controller='form', action='update', id=self.id)
        historyURL = url(controller='form', action='history', id=self.id)
        associateURL = url(controller='form', action='associate', id=self.id)
        rememberURL = url(controller='form', action='remember', id=self.id)
        exportURL = url(controller='form', action='export', id=self.id)
        deleteURL = url(controller='form', action='delete', id=self.id)
        duplicateURL = url(controller='form', action='duplicate', id=self.id)

        result = u'<div style="position: relative;">'
        if forCollection:
            result += u'\n <div style="max-width: 2em; position: absolute; \
                top: 35px; left: -52px;"'
        else:
            result += u'\n <div style="max-width: 2em; position: absolute; \
                left: -52px;"'
        result += u' class="blacklinks" id="form%d_%dMenuDiv"></div>' % (
            self.id, self.uniqueNo)
        result += u'\n</div>'
        result += u'\n<script type="text/javascript">'

        # The formMenu should permit the form to be dissociated from the file
        #  if appropriate
        if getattr(self, 'fileID', None):
            disassociateURL = url('disassociate', controller='file',
                                  id=self.fileID, otherID=self.id)
            result += u'createFormActionButton("%s", "%d", "%s", "%s", "%s", "%s", "%s", "%s", "%s", "%s");' % (
                    self.id, self.uniqueNo, updateURL, historyURL, associateURL,
                    rememberURL, exportURL, deleteURL, duplicateURL, disassociateURL)
        else:
            result += u'createFormActionButton("%s", "%d", "%s", "%s", "%s", "%s", "%s", "%s", "%s");' % (
                    self.id, self.uniqueNo, updateURL, historyURL, associateURL,
                    rememberURL, exportURL, deleteURL, duplicateURL)

        result += u'</script>'
        return result

    igt_attrs = (
        'transcription',
        'narrowPhoneticTranscription',
        'phoneticTranscription',
        'morphemeBreak',
        'morphemeGloss',
    )

    @property
    def alignable_igt_attrs(self):
        """Return the sublist of attribute names ``self.igt_attrs`` whose values are alignable.
        Return the empty list if there are no such attribute names.

        """
        try:
            return self._alignable_igt_attrs
        except AttributeError:
            igt_attrs_values = ((attr, getattr(self, attr)) for attr in self.igt_attrs)
            valued_igt_attrs = [(attr, value) for attr, value in igt_attrs_values if value]
            if len(set([len(value.split()) for attr, value in valued_igt_attrs])) == 1:
                self._alignable_igt_attrs = [attr for attr, value in valued_igt_attrs]
            else:
                self._alignable_igt_attrs = []
            return self._alignable_igt_attrs

    @property
    def alignable(self):
        """Returns True if there are the same number of "words" in all of the
        (valuated) interlinear gloss text attributes, i.e., those listed in
        ``self.igt_attrs``.  Note: if there is only one alignable IGT attribute,
        then it is the mandatory transcription and there is no point in aligning.

        """
        return len(self.alignable_igt_attrs) > 1

    def getIGTHTMLTable(self, isolatedCall=False):
        """Return an HTML representation of the primary data of the Form in
        interlinear gloss text (IGT) format.

        """

        # If getIGTHTMLTable is being accessed publicly, uniqueNo needs to be
        #  manually assigned; it's no longer probably unique though ...
        if isolatedCall:
            self.uniqueNo = 1

        # If the "word" counts are equal, align them into columns
        if self.alignable:
            result = self.getIGTHTMLTableWordsAligned()

        # Otherwise, just use a single table cell for each field
        else:
            result = u'<table>'
            result += u'<tr id="form%d_%dtranscription"><td ' % (self.id,
                                                                 self.uniqueNo)
            result += u'class="dataCellTr">%s%s</td></tr>' % (
                self.grammaticality,
                h.storageToOutputTranslate(self.transcription)
            )
            result += u'<tr><td class="dataCell">%s</td></tr>' % \
                (self.narrowPhoneticTranscription or u'')
            result += u'<tr><td class="dataCell">%s</td></tr>' % \
                (self.phoneticTranscription or u'')
            result += u'<tr><td class="dataCell">%s</td></tr>' % \
                h.storageToOutputTranslate(self.morphemeBreak, True)
            result += u'<tr><td class="dataCell">%s</td></tr>' % \
                self.morphemeGloss
            for gloss in self.glosses:
                result += u'<tr><td class="dataCell">&lsquo;%s%s&rsquo;</td></tr>' % \
                    (
                        (lambda x: x if x else u'')(gloss.glossGrammaticality),
                        gloss.gloss
                    )
            result += u'</table>'
        return result

    def getAdditionalData(self):
        """Return a non-visible HTML div (indented) containing an HTML table
        (with small font size) containing additional Form data.
        
        """

        # self.formBackup = True will make the additional data visible by default
        # and will make form_id = self.form_id
        form_id = self.id
        style = 'style="display: none;"'
        if getattr(self, 'formBackup', False):
            style = ''
            form_id = self.form_id

        result = u'<div class="containerDivIndent "'
        result += u'id="form%d_%dAdditionalDataDiv" ' % (self.id, self.uniqueNo)
        result += u'%s><table class="smallTable">' % style
        if self.comments:
            result += u'<tr><td class="label">comments</td><td>%s</td></tr>' % \
                h.storageToOutputTranslateOLOnly(
                h.linkToOLDEntitites(self.comments))
        if self.speakerComments:
            result += u'<tr><td class="label">speaker comments</td><td>%s</td>\
                </tr>' % h.storageToOutputTranslateOLOnly(self.speakerComments)
        if self.elicitationMethod:
            url_ = url(controller='method', action='view',
                       id=self.elicitationMethod.id)
            result += u'<tr><td class="label">elicitation method</td>\
                <td><a href="%s">%s</a></td></tr>' % (
                url_, self.elicitationMethod.name)
        if self.keywords:
            keywords = ['<a href="%s">%s</a>' % (url(controller='key',
                action='view', id=k.id), k.name) for k in self.keywords]
            result += u'<tr><td class="label">keywords</td><td>%s</td></tr>' % (
                ', '.join(keywords))
        if self.speaker:
            url_ = url(controller='speaker', action='view', id=self.speaker.id)
            result += u'<tr><td class="label">speaker</td><td>\
                <a href="%s">%s %s</a></td></tr>' % (
                url_, self.speaker.firstName, self.speaker.lastName)
        if self.elicitor:
            url_ = url(controller='researcher', action='view',
                id=self.elicitor.id)
            result += u'<tr><td class="label">elicitor</td>\
                <td><a href="%s">%s %s</a></td></tr>' % (url_,
                self.elicitor.firstName, self.elicitor.lastName)
        if self.source:
            url_ = url(controller='source', action='view', id=self.source.id)
            result += u'<tr><td class="label">source</td>\
                <td><a href="%s">%s, %s. %d</a></td></tr>' % (url_,
                self.source.authorLastName, self.source.authorFirstName[0],
                self.source.year)
        if self.enterer:
            url_ = url(controller='researcher', action='view', id=self.enterer.id)
            result += u'<tr><td class="label">enterer</td>\
                <td><a href="%s">%s %s</a></td></tr>' % (url_,
                self.enterer.firstName, self.enterer.lastName)
        if self.verifier:
            url_ = url(controller='researcher', action='view', id=self.verifier.id)
            result += u'<tr><td class="label">verifier</td>\
                <td><a href="%s">%s %s</a></td></tr>' % (url_,
                self.verifier.firstName, self.verifier.lastName)
        if self.dateElicited:
            result += u'<tr><td class="label">date elicited</td><td>%s</td></tr>' % (
                h.pretty_date(self.dateElicited))
        if self.datetimeEntered:
            result += u'<tr><td class="label">time entered</td><td>%s</td></tr>' % (
                h.pretty_date(self.datetimeEntered))
        if self.datetimeModified:
            result += u'<tr><td class="label">last updated</td><td>%s</td></tr>' % (
                h.pretty_date(self.datetimeModified))
        if self.syntacticCategory:
            url_ = url(controller='category', action='view',
                id=self.syntacticCategory.id)
            result += u'<tr><td class="label">category</td>\
                <td><a href="%s">%s</a></td></tr>' % (url_,
                self.syntacticCategory.name,)
        if self.syntacticCategoryString:
            result += u'<tr><td class="label">category string</td>\
                <td>%s</td></tr>' % self.syntacticCategoryString
        url_ = url(controller='form', action='view', id=form_id)
        result += u'<tr><td class="label">ID</td>\
                <td><a href="%s">%d</a></td></tr>' % (url_, form_id)
        result += u'</table></div>'

        return result

    def getAssociatedFiles(self):
        """Return an HTML representation of the Files associated to this Form.
        
        """

        result = u'<div'
        result += u' id="form%d_%dAssociatedFilesDiv"' % (self.id, self.uniqueNo)
        result += u' style="display:none;">' 

        if self.files:
            for file in self.files:
                result += u'\n<div class="containerDivIndent">'
                result += '\n\n%s\n\n' % file.getHTMLRepresentation(
                    formID=self.id)
                result += u'\n</div>'
        else:
            result += u'<p>There are no Files associated to this Form.</p>'

        result += u'</div>'

        return result

    @property
    def align_broad_phonetic(self):
        return (self.phoneticTranscription and
            len(self.transcription.split()) ==
            len(self.phoneticTranscription.split()))

    def get_igt_row(self, sublist, attr, index, style_attribute):
        """Return an HTML <tr> element representing a row of an IGT representation.

        :param list sublist: a list of words to occur in the IGT row.
        :param str attr: the name of the attribute whose words are in the row, e.g., ``transcription``.
        :param int index: the index of the row group.
        :param unicode style_attribute: the value of the HTML style attribute to put in
            the vacuous <td> tag in order to effect the cascading indentation.
        :returns: a unicode string representation of the <tr> element.

        """
        tr_tag = u'<tr>'
        if attr == 'transcription':
            tr_tag = u'<tr id="form%s_%stranscription">' % (self.id, self.uniqueNo)
        return u'%s<td style="%s"></td>%s</tr>' % (tr_tag, style_attribute,
                self.get_igt_row_cells(sublist, attr, index))

    def getIGTHTMLTableWordsAligned(self):
        """Return an HTML representation of the Form in interlinear gloss text
        (IGT) format where the words are aligned using table cells.

        """

        self.listifyCoreData()
        result = []

        for index, transcription_sublist in enumerate(self.transcriptionList):
            # ``styleAttribute`` makes a dummy <td> have a greater and greater width
            #  on each iteration, thus creating the cascade effect.
            style_attribute = (u'width: %sem;min-width: %sem; padding: 0;' %
                              ((index * 2), (index * 2)))
            result.append(u'<table>')
            for attr in self.alignable_igt_attrs:
                sublist = getattr(self, '%sList' % attr)[index]
                result.append(self.get_igt_row(sublist, attr, index, style_attribute))
            result.append(u'</table>')
        for gloss in self.glosses:
            result.extend([
                u'<table>',
                u'<tr><td class="dataCell">%s&lsquo;%s&rsquo;</td></tr>' % (
                    gloss.glossGrammaticality, gloss.gloss),
                u'</table>'
            ])
        return u''.join(result)

    def get_igt_row_cells(self, sublist, attr, index):
        """Return a string of HTML <td> elements containing the words in an IGT row.

        :param list sublist: a list of words to occur in the IGT row.
        :param str attr: the name of the attribute whose words are in the row, e.g., ``transcription``.
        :param int index: the index of the row group.
        :returns: a string of <td> tags containing words.

        """
        result = []
        for word_index, word in enumerate(sublist):
            if attr == 'transcription' and word_index == 0 and index == 0:
                result.append(u'<td class="dataCellTr">%s%s</td>' % (
                    self.grammaticality, h.storageToOutputTranslate(word)))
            elif attr == 'transcription':
                result.append(u'<td class="dataCellTr">%s</td>' %
                    h.storageToOutputTranslate(word))
            elif attr in ('morphemeBreak', 'morphemeGloss'):
                result.append(u'<td class="dataCell">%s</td>' %
                    self.get_word_with_morpheme_links(word, attr, index, word_index))
            else:
                result.append(u'<td class="dataCell">%s</td>' % word)
        return u''.join(result)

    @property
    def delimiters(self):
        """A list of strings used to delimit morphemes."""
        try:
            return self._delimiters
        except AttributeError:
            self._delimiters = app_globals.morphDelimiters
            return self._delimiters

    @property
    def morpheme_splitter(self):
        """A function that splits a string into morphemes and delimiters."""
        try:
            return self._morpheme_splitter
        except AttributeError:
            patt = u'([%s])' % u''.join(self.delimiters)
            patt = re.compile(patt)
            self._morpheme_splitter = patt.split
            return self._morpheme_splitter

    whitespace_patt = re.compile('([\t\n]| {2,})')

    def whitespace2singlespace(self, string):
        return self.whitespace_patt.sub(u' ', string)

    def get_word_with_morpheme_links(self, word, attr, index, word_index):
        """Return the word with its morphemes represented as links to their lexical entries.

        :param unicode word: the word whose morpheme forms or glosses are to be represented
            as links
        :param str attr: the name of the attribute that is the source of ``word``, e.g., "morphemeBreak".
        :param int index: the index of the IGT row group.
        :param int word_index: the index of the word within the IGT row group.
        :returns: an HTML representation of ``word`` where component morphemes matching
            lexical entries in the database are represented as links to those lexical
            entries.  Also, perfect matches (i.e., those where a morpheme's form and
            gloss match a lexical entry exactly) are given the HTML class value "match".

        """

        morphemeBreakWords = self.whitespace2singlespace(self.morphemeBreak.strip()).split()
        morphemeGlossWords = self.whitespace2singlespace(self.morphemeGloss.strip()).split()
        morpheme_splitter = self.morpheme_splitter
        morpheme_form_counts = [len(morpheme_splitter(w)) for w in morphemeBreakWords]
        morpheme_gloss_counts = [len(morpheme_splitter(w)) for w in morphemeGlossWords]
        if morpheme_form_counts == morpheme_gloss_counts:
            morphemes_and_delimiters = morpheme_splitter(word)
            morpheme_form_ids = self.morphemeBreakIDsList[index][word_index]
            morpheme_gloss_ids = self.morphemeGlossIDsList[index][word_index]
            tmp = []
            for morpheme_index, morpheme in enumerate(morphemes_and_delimiters):
                if attr == 'morphemeBreak':
                    morpheme = h.storageToOutputTranslate(morpheme, True)
                if morpheme_index % 2 == 0:
                    if attr == 'morphemeBreak':
                        morpheme_ids = morpheme_form_ids[morpheme_index / 2]
                        other_ids = morpheme_gloss_ids[morpheme_index / 2]
                    else:
                        morpheme_ids = morpheme_gloss_ids[morpheme_index / 2]
                        other_ids = morpheme_form_ids[morpheme_index / 2]
                    if ([id_ for id_, x, y in morpheme_ids] ==
                        [id_ for id_, x, y in other_ids]):
                        class_ = 'match'
                    else:
                        class_ = 'nonmatch'
                    if len(morpheme_ids) > 0:
                        id_list = ','.join([str(id_) for id_, x, y in morpheme_ids])
                        url_ = url(controller='form', action='view', id=id_list)
                        title = u'; '.join([u'%s (%s)' % (x, y or u'NULL')
                                            for id_, x, y in morpheme_ids])
                        tmp.append(u'<a class="%s" href="%s" title="%s">%s</a>' %
                                      (class_, url_, title, morpheme))
                    else:
                        # No lexical entries match this morpheme.
                        tmp.append(morpheme)
                else:
                    # We have a delimiter, not a morpheme.
                    tmp.append(morpheme)
            word = u''.join(tmp)
        else:
            if attr == 'morphemeBreak':
                word = h.storageToOutputTranslate(word, True)
        return word

    def getHTMLRowRepresentation(self):
        """Return an HTML representation of the Form as a row in a table.

        """

        # Return an error message if the user is not authorized to view the form
        if not h.userIsAuthorizedToAccessForm(session['user'], self):
            return u'<tr><td>%d</td>%s</tr>' % (self.id, u'<td>Restricted</td>' * 23)

        def punctuateGlossAsSentence(gloss):
            if gloss[-1] in ['.', '!', '?'] or \
            (gloss[-1] in ['"', '\'', u'\u2019', u'\u201D'] and \
            gloss[-2] in ['.', '!', '?']):
                return gloss
            else:
                return gloss + '.'

        def formIsASentence(form):
            return form.syntacticCategory and \
            form.syntacticCategory.name.lower() in ['s', 'sent', 'sentence']

        def getGlossesPunctuatedAndStringified(form):
            glosses = form.glosses
            if formIsASentence(form):
                return ' '.join(['%s%s' % (gloss.glossGrammaticality,
                                punctuateGlossAsSentence(gloss.gloss))
                                for gloss in glosses])
            else:
                return '; '.join(['%s%s' % (gloss.glossGrammaticality,
                                            gloss.gloss) for gloss in glosses])

        glosses = getGlossesPunctuatedAndStringified(self)

        syntacticCategory = u''
        if self.syntacticCategory:
            syntacticCategory = self.syntacticCategory.name

        dateElicited = u''
        if self.dateElicited:
            dateElicited = self.dateElicited.strftime('%b %d, %Y')

        datetimeEntered = u''
        if self.datetimeEntered:
            datetimeEntered = self.datetimeEntered.strftime(
                '%b %d, %Y at %I:%M %p (UTC)')

        datetimeModified = u''
        if self.datetimeModified:
            datetimeModified = self.datetimeModified.strftime(
                '%b %d, %Y at %I:%M %p (UTC)')

        speaker = u''
        if self.speaker:
            speaker = u'%s %s' % (self.speaker.firstName, self.speaker.lastName)

        source = u''
        if self.source:
            source = u'%s %d' % (self.source.authorLastName, self.source.year)

        elicitor = u''
        if self.elicitor:
            elicitor = u'%s %s' % (self.elicitor.firstName, self.elicitor.lastName)

        enterer = u''
        if self.enterer:
            enterer = u'%s %s' % (self.enterer.firstName, self.enterer.lastName)

        verifier = u''
        if self.verifier:
            verifier = u'%s %s' % (self.verifier.firstName, self.verifier.lastName)

        elicitationMethod = u''
        if self.elicitationMethod:
            elicitationMethod = self.elicitationMethod.name

        keywords = ', '.join([k.name for k in self.keywords])

        files = ', '.join([f.name for f in self.files])

        collections = ', '.join([c.title for c in self.collections])

        row = u'<tr>'
        row += u'<td>%d</td>' % self.id
        row += u'<td>%s</td>' % self.grammaticality
        row += u'<td>%s</td>' % self.transcription
        row += u'<td>%s</td>' % (self.narrowPhoneticTranscription or u'')
        row += u'<td>%s</td>' % (self.phoneticTranscription or u'')
        row += u'<td>%s</td>' % glosses
        row += u'<td>%s</td>' % self.morphemeBreak
        row += u'<td>%s</td>' % self.morphemeGloss
        row += u'<td>%s</td>' % self.comments
        row += u'<td>%s</td>' % self.speakerComments
        row += u'<td>%s</td>' % syntacticCategory
        row += u'<td>%s</td>' % self.syntacticCategoryString
        row += u'<td>%s</td>' % speaker
        row += u'<td>%s</td>' % source
        row += u'<td>%s</td>' % elicitor
        row += u'<td>%s</td>' % enterer
        row += u'<td>%s</td>' % verifier
        row += u'<td>%s</td>' % elicitationMethod
        row += u'<td>%s</td>' % keywords
        row += u'<td>%s</td>' % files
        row += u'<td>%s</td>' % collections
        row += u'<td>%s</td>' % dateElicited
        row += u'<td>%s</td>' % datetimeEntered
        row += u'<td>%s</td>' % datetimeModified

        row += u'</tr>'

        return row




class FormBackup(Form):
    """FormBackup subclasses Form.  FormBackup has two novel methods,
    toJSON() and fromJSON().

    toJSON() takes a Form object as input and takes its data and stores
    nested data structures as JSON dictionaries which can be stored in 
    a database char field.

    fromJSON() converts the JSONified dictionaries back into Column
    objects, thus making the FormBackup behave just like a Form object.
    
    """
 
    def toJSON(self, form, user):
        """Convert the "pertinent" nested data structures of
        a Form into a python dict and then into a JSON data structure using 
        the json module from the standard library.

        Note: the user argument is already a Python string / JSON object

        """
        
        self.form_id = form.id
        self.transcription = form.transcription
        self.phoneticTranscription = form.phoneticTranscription
        self.narrowPhoneticTranscription = form.narrowPhoneticTranscription
        self.morphemeBreak = form.morphemeBreak
        self.morphemeGloss = form.morphemeGloss
        self.grammaticality = form.grammaticality
        self.comments = form.comments
        self.speakerComments = form.speakerComments
        self.dateElicited = form.dateElicited
        self.datetimeEntered = form.datetimeEntered
        self.datetimeModified = datetime.datetime.utcnow()
        self.syntacticCategoryString = form.syntacticCategoryString
        self.morphemeBreakIDs = form.morphemeBreakIDs
        self.morphemeGlossIDs = form.morphemeGlossIDs
        self.backuper = user
        if form.elicitationMethod:
            self.elicitationMethod = unicode(json.dumps({
                'id': form.elicitationMethod.id, 
                'name': form.elicitationMethod.name
            }))
        if form.syntacticCategory:
            self.syntacticCategory = unicode(json.dumps({
                'id': form.syntacticCategory.id, 
                'name': form.syntacticCategory.name
            }))
        if form.source:
            self.source = unicode(json.dumps({
                'id': form.source.id, 
                'authorFirstName': form.source.authorFirstName, 
                'authorLastName': form.source.authorLastName, 
                'year': form.source.year, 
                'fullReference': form.source.fullReference
            }))
        if form.speaker:
            self.speaker = unicode(json.dumps({
                'id': form.speaker.id, 
                'firstName': form.speaker.firstName, 
                'lastName': form.speaker.lastName, 
                'dialect': form.speaker.dialect
            }))
        if form.elicitor:
            self.elicitor = unicode(json.dumps({
                'id': form.elicitor.id, 
                'firstName': form.elicitor.firstName, 
                'lastName': form.elicitor.lastName
        }))
        if form.enterer:
            self.enterer = unicode(json.dumps({
                'id': form.enterer.id, 
                'firstName': form.enterer.firstName, 
                'lastName': form.enterer.lastName
            }))
        if form.verifier:
            self.verifier = unicode(json.dumps({
                'id': form.verifier.id, 
                'firstName': form.verifier.firstName, 
                'lastName': form.verifier.lastName
            }))
        if form.glosses:
            self.glosses = unicode(json.dumps([{
                'id': gloss.id, 
                'gloss': gloss.gloss, 
                'glossGrammaticality': gloss.glossGrammaticality}
                for gloss in form.glosses]))
        if form.keywords:
            self.keywords = unicode(json.dumps([{
                'id': keyword.id, 
                'name': keyword.name} for keyword in form.keywords]))
        if form.files:
            self.files = unicode(json.dumps([{
                'id': file.id, 
                'name': file.name, 
                'embeddedFileMarkup': file.embeddedFileMarkup, 
                'embeddedFilePassword': file.embeddedFilePassword}
                for file in form.files]))

    def fromJSON(self):
        """Convert the JSONified dictionaries back into Column objects, 
        thus making the FormBackup behave just like a Form object.  (Almost.)
        
        """
        
        if self.elicitationMethod:
            elicitationMethod = json.loads(self.elicitationMethod)
            self.elicitationMethod = Column()
            self.elicitationMethod.id = elicitationMethod['id']
            self.elicitationMethod.name = elicitationMethod['name']
        if self.syntacticCategory:
            syntacticCategory = json.loads(self.syntacticCategory)
            self.syntacticCategory = Column()
            self.syntacticCategory.id = syntacticCategory['id']
            self.syntacticCategory.name = syntacticCategory['name']
        if self.source:
            source = json.loads(self.source)
            self.source = Column()
            self.source.id = source['id']
            self.source.authorFirstName = source['authorFirstName']
            self.source.authorLastName = source['authorLastName']
            self.source.year = source['year']
            self.source.fullReference = source['fullReference']
        if self.speaker:
            speaker = json.loads(self.speaker)
            self.speaker = Column()
            self.speaker.id = speaker['id']
            self.speaker.firstName = speaker['firstName']
            self.speaker.lastName = speaker['lastName']
            self.speaker.dialect = speaker['dialect']
        if self.elicitor:
            elicitor = json.loads(self.elicitor)
            self.elicitor = Column()
            self.elicitor.id = elicitor['id']
            self.elicitor.firstName = elicitor['firstName']
            self.elicitor.lastName = elicitor['lastName']
        if self.enterer:
            enterer = json.loads(self.enterer)
            self.enterer = Column()
            self.enterer.id = enterer['id']
            self.enterer.firstName = enterer['firstName']
            self.enterer.lastName = enterer['lastName']
        if self.verifier:
            verifier = json.loads(self.verifier)
            self.verifier = Column()
            self.verifier.id = verifier['id']
            self.verifier.firstName = verifier['firstName']
            self.verifier.lastName = verifier['lastName']
        if self.glosses:
            glosses = json.loads(self.glosses)
            self.glosses = []
            for glossDict in glosses:
                gloss = Column()
                gloss.id = glossDict['id']
                gloss.gloss = glossDict['gloss']
                gloss.glossGrammaticality = glossDict['glossGrammaticality']
                self.glosses.append(gloss)
        if self.keywords:
            keywords = json.loads(self.keywords)
            self.keywords = []
            for keywordDict in keywords:
                keyword = Column()
                keyword.id = keywordDict['id']
                keyword.name = keywordDict['name']
                self.keywords.append(keyword)
        if self.files:
            files = json.loads(self.files)
            self.files = []
            for fileDict in files:
                file = Column()
                file.id = fileDict['id']
                file.name = fileDict['name']
                file.embeddedFileMarkup = fileDict['embeddedFileMarkup']
                file.embeddedFilePassword = fileDict['embeddedFilePassword']
                self.files.append(file)
        if self.backuper:
            backuper = json.loads(self.backuper)
            self.backuper = Column()
            self.backuper.id = backuper['id']
            self.backuper.firstName = backuper['firstName']
            self.backuper.lastName = backuper['lastName']



################################################################################
#################  Collection and CollectionBackup Classes  ####################
################################################################################

class Collection(object):
    """A dummy Collection object for CollectionBackup to subclass.
    
    Perhaps some Collection-related functionality should be implemented as
    methods here.  E.g., the functions in controllers/collection.py that format
    the contents of a Collection ...
    
    """
    
    pass

class CollectionBackup(Collection):
    """CollectionBackup subclasses Collection.  CollectionBackup has two novel
    methods, toJSON() and fromJSON().

    toJSON() takes a Collection object as input and takes its data and stores
    nested data structures as JSON dictionaries which can be stored in 
    a database char field.

    fromJSON() converts the JSONified dictionaries back into Column
    objects, thus making the CollectionBackup behave just like a Collection
    object.

    """
 
    def toJSON(self, collection, user):
        """Convert the "pertinent" nested data structures of
        a Collection into a python dict and then into a JSON data structure
        using the json module from the standard library.
        
        Note: the user argument is already a Python string / JSON object
        
        """
        
        self.collection_id = collection.id
        self.dateElicited = collection.dateElicited
        self.datetimeEntered = collection.datetimeEntered
        self.datetimeModified = datetime.datetime.utcnow()
        self.backuper = user
        self.title = collection.title
        self.type = collection.type
        self.description = collection.description
        self.contents = collection.contents

        if collection.speaker:
            self.speaker = unicode(json.dumps({
                'id': collection.speaker.id, 
                'firstName': collection.speaker.firstName, 
                'lastName': collection.speaker.lastName, 
                'dialect': collection.speaker.dialect
            }))
        if collection.source:
            self.source = unicode(json.dumps({
                'id': collection.source.id, 
                'authorFirstName': collection.source.authorFirstName, 
                'authorLastName': collection.source.authorLastName, 
                'year': collection.source.year, 
                'fullReference': collection.source.fullReference
            }))
        if collection.enterer:
            self.enterer = unicode(json.dumps({
                'id': collection.enterer.id, 
                'firstName': collection.enterer.firstName, 
                'lastName': collection.enterer.lastName
            }))
        if collection.elicitor:
            self.elicitor = unicode(json.dumps({
                'id': collection.elicitor.id, 
                'firstName': collection.elicitor.firstName, 
                'lastName': collection.elicitor.lastName
            }))

        # The Many-to-Many Collection-to-File relationship is represented by
        #  a list of JS objects in JSON.
        #  Why are not the MIMEType and other data included here or in the
        #  above FormBackup.toJSON() method?
        if collection.files:
            filesList = [{
                'id': file.id, 
                'name': file.name, 
                'embeddedFileMarkup': file.embeddedFileMarkup, 
                'embeddedFilePassword': file.embeddedFilePassword} for file in collection.files]
            self.files = unicode(json.dumps(filesList))
            
            
        # The Many-to-Many Collection-to-Form relationship is recoverable from
        #  self.contents, so it is not re-stored as a JSON list of objects
        #  as is the Collection-to-File relationship (which is assumed to
        #  contain far fewer associations...)

    def fromJSON(self):
        """Convert the JSONified dictionaries back into Column objects, 
        thus making the CollectionBackup behave just like a Collection object.
        (Almost.)
        
        """

        if self.speaker:
            speaker = json.loads(self.speaker)
            self.speaker = Column()
            self.speaker.id = speaker['id']
            self.speaker.firstName = speaker['firstName']
            self.speaker.lastName = speaker['lastName']
            self.speaker.dialect = speaker['dialect']
        if self.source:
            source = json.loads(self.source)
            self.source = Column()
            self.source.id = source['id']
            self.source.authorFirstName = source['authorFirstName']
            self.source.authorLastName = source['authorLastName']
            self.source.year = source['year']
            self.source.fullReference = source['fullReference']
        if self.elicitor:
            elicitor = json.loads(self.elicitor)
            self.elicitor = Column()
            self.elicitor.id = elicitor['id']
            self.elicitor.firstName = elicitor['firstName']
            self.elicitor.lastName = elicitor['lastName']
        if self.enterer:
            enterer = json.loads(self.enterer)
            self.enterer = Column()
            self.enterer.id = enterer['id']
            self.enterer.firstName = enterer['firstName']
            self.enterer.lastName = enterer['lastName']
        if self.files:
            files = json.loads(self.files)
            self.files = []
            for fileDict in files:
                file = Column()
                file.id = fileDict['id']
                file.name = fileDict['name']
                file.embeddedFileMarkup = fileDict['embeddedFileMarkup']
                file.embeddedFilePassword = fileDict['embeddedFilePassword']
                self.files.append(file)
        if self.backuper:
            backuper = json.loads(self.backuper)
            self.backuper = Column()
            self.backuper.id = backuper['id']
            self.backuper.firstName = backuper['firstName']
            self.backuper.lastName = backuper['lastName']


################################################################################
#################  File Class ##################################################
################################################################################

# Browser HTML5 audio compatibilities
#
#                        mp3     ogg     wav     au/snd      aif/aifc/aiff   
#    Firefox (Linux, Mac)N       Y       Y       N           N               
#    Chrome (Linux)      Y       Y       N       N           N               
#    Safari (Mac)        Y       N       N       Y           N

class File(object):
    """A File object is generated by SQLAlchemy each time a File is queried.

    The methods are all related to the displaying of the File's data in HTML,
    getHTMLRepresentation being the most oft-called.

    """

    def getHTMLRepresentation(self, **kwargs):
        """Return an HTML representation of the File.  Default format is to
        display the file name and have a YUI menu '+' button to view additional
        data, file media and associated Forms.

        """

        # Generate a random number to try to ensure unique HTML IDs for File
        #  representations.  ID is insufficient as the same File may be embedded
        #  twice in a page
        self.uniqueNo = randrange(0, 1000)

        # Get a string representing the type of the file
        self.fileTypeString = self.getFileType()

        self.setOptions(kwargs)

        style = u''
        if getattr(self, 'forCollection', False):
            style = u' position: relative; left: 50px;' 

        HTMLRepresentation = u'<div id="file%d_%dDiv" ' % (self.id,
                                                           self.uniqueNo)
        HTMLRepresentation += u'style="margin: 20px 0px;%s">\n' % (style)

        HTMLRepresentation += self.getFileMenu()
        HTMLRepresentation += u'<a id="file%d_%dNameAnchor">%s</a>' % (
            self.id, self.uniqueNo, self.name)
        HTMLRepresentation += self.getFileMedia()
        HTMLRepresentation += self.getAdditionalData()
        HTMLRepresentation += self.getAssociatedForms()

        HTMLRepresentation += u'\n</div>'

        return h.literal(HTMLRepresentation)

    def setOptions(self, kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

    def getFileMenu(self):
        """Get the YUI menu button that provides the File actions, i.e., update,
        delete and associate.  The createFileActionButton JavaScript function is
        defined in public/javascript/functions.js.

        """

        updateURL = url(controller='file', action='update', id=self.id)
        deleteURL = url(controller='file', action='delete', id=self.id)
        associateURL = url(controller='file', action='associate', id=self.id)

        result = u'<div style="position: relative;">'
        result += u'\n <div style="max-width: 2em; position: absolute; '
        result += u'left: -52px;"'
        result += u' class="blacklinks" id="file%d_%dMenuDiv"></div>' % (
            self.id, self.uniqueNo)
        result += u'\n</div>'
        result += u'\n<script type="text/javascript">'

        # The fileMenu should permit the file to be dissociated from the form if appropriate
        if getattr(self, 'formID', None):
            disassociateURL = url('disassociate', controller='form',
                                  id=self.formID, otherID=self.id)
            result += u'createFileActionButton("%s", "%s", "%s", "%s", "%s", "%s");' % (
                self.id, self.uniqueNo, updateURL, associateURL, deleteURL,
                disassociateURL)
        elif getattr(self, 'collectionID', None):
            disassociateURL = url('disassociate', controller='collection',
                                  id=self.collectionID, otherID=self.id)
            result += u'createFileActionButton("%s", "%s", "%s", "%s", "%s", "%s");' % (
                self.id, self.uniqueNo, updateURL, associateURL, deleteURL,
                disassociateURL)
        else:
            result += u'createFileActionButton("%s", "%s", "%s", "%s", "%s");' % (
                self.id, self.uniqueNo, updateURL, associateURL, deleteURL)

        result += u'</script>'
        return result

    def getAdditionalData(self):
        """Return a non-visible HTML div (indented) containing an HTML table
        (with small font size) containing additional File data.
        
        """

        fileType = self.fileTypeString

        result = u'<div class="containerDivIndent" '
        result += u'id="file%d_%dAdditionalDataDiv" ' % (self.id, self.uniqueNo)
        result += u'style="display: none;"><table class="smallTable">'
        result += u'<tr><td class="label">ID</td><td>%s</td></tr>' % self.id
        result += u'<tr><td class="label">file type</td>'
        result += u'<td>%s</td></tr>' % fileType

        if self.size:
            result += u'<tr><td class="label">file size</td>'
            result += u'<td>%s</td></tr>' % h.pretty_filesize(self.size)
        if self.description:
            result += u'<tr><td class="label">description</td>'
            result += u'<td>%s</td></tr>' % (self.description)
        if self.utteranceType:
            result += u'<tr><td class="label">utterance type</td>'
            result += u'<td>%s</td></tr>' % (self.utteranceType)
        if self.speaker:
            url_ = url(controller='speaker', action='view', id=self.speaker.id)
            result += u'<tr><td class="label">speaker</td><td>\
                <a href="%s">%s %s</a></td></tr>' % (
                url_, self.speaker.firstName, self.speaker.lastName)
        if self.elicitor:
            url_ = url(controller='researcher', action='view',
                id=self.elicitor.id)
            result += u'<tr><td class="label">elicitor</td>\
                <td><a href="%s">%s %s</a></td></tr>' % (url_,
                self.elicitor.firstName, self.elicitor.lastName)
        if self.enterer:
            url_ = url(controller='researcher', action='view', id=self.enterer.id)
            result += u'<tr><td class="label">enterer</td>\
                <td><a href="%s">%s %s</a></td></tr>' % (url_,
                self.enterer.firstName, self.enterer.lastName)
        if self.dateElicited:
            result += u'<tr><td class="label">date elicited</td><td>%s</td></tr>' % (
                h.pretty_date(self.dateElicited))
        if self.datetimeEntered:
            result += u'<tr><td class="label">time entered</td><td>%s</td></tr>' % (
                h.pretty_date(self.datetimeEntered))
        if self.datetimeModified:
            result += u'<tr><td class="label">last updated</td><td>%s</td></tr>' % (
                h.pretty_date(self.datetimeModified))
        result += u'</table></div>'

        return result

    def getAssociatedForms(self):
        """Return an HTML representation of the Forms that are associated to
        this File.

        """

        result = u'<div '
        result += u'id="file%d_%dAssociatedFormsDiv" ' % (self.id, self.uniqueNo)
        result += u'style="display: none;">'

        if self.forms:
            for form in self.forms:
                result += u'<div class="containerDivIndent">'
                result += form.getHTMLRepresentation(fileID=self.id)
                result += u'\n</div>'
        else:
            result += u'<p>There are no Forms associated to this File.</p>'

        result += u'\n</div>'

        return result

    def getFileMedia(self, hidden=True):
        """Returns a representation of the media of the File.  I.e., an <img />
        tag for image file types, etc.

        """

        # Get a string representing the type of the file
        try:
            fileType = self.fileTypeString
        except AttributeError:
            self.fileTypeString = self.getFileType()
            fileType = self.fileTypeString

        fileReference = url('retrieve', path=self.name)

        result = u'<div class="fileContent" id="file%d_%dMediaDiv" ' % (
            self.id, self.uniqueNo)

        if hidden:
            result += u'style="display: none;">'

        if fileType == 'image':
            result += self.displayImage(fileReference, hidden)
        elif fileType == 'audio':
            result += self.displayAudio(fileReference, hidden)
        elif fileType == 'video':
            result += self.displayVideo(fileReference, hidden)
        elif fileType == 'embedded media':
            result += self.displayEmbeddedMedia(hidden)
        else:
            result += self.displayTextual(fileReference, hidden)

        result += u'</div>'

        return result

    def displayEmbeddedMedia(self, hidden=True):
        """An OLD File whose media is being served elsewhere is displayed using
        the HTML <embed> tag entered by the user.  The remote media are hidden
        by default and revealed with a button click.
        
        """

        buttonID = str(self.id) + 'Button'
        divID = str(self.id) + 'Div'
        
        style = u''
        if hidden:
            style = u' style="display:none;"'

        password = u''
        if self.embeddedFilePassword:
            password = u'\n<p>Password: %s</p>\n' % self.embeddedFilePassword

        divTag = u'<div%s id=\'%s\'>\n%s\n%s</div>' % (
            style, divID, self.embeddedFileMarkup, password)

        if hidden:
            result = u'<a onclick="addRemoveElement(\'%s\', \'%s\', \'media\', ' % \
                (divID, buttonID)
            result += u'\'hide media|show media\');"'
            result += u' class="buttonLink" id="%s" title="show embedded media ' % \
                buttonID
            result += u'in the page">show media</a>'
            result += divTag
        else:
            result = divTag
        
        return result

    def displayImage(self, fileReference, hidden=True):
        """An OLD File representing an image is displayed using HTML's <img />
        tag.  The image is hidden by default and is revealed with a button
        click.
        
        """
        
        fileName = path.splitext(self.name)[0]
        buttonID = fileName + 'Button'

        style = u''
        if hidden:
            style = u' style="display:none;"'

        imgTag = u'\n<img alt="%s"%s src="%s" ' % \
            (self.name, style, fileReference)
        imgTag += u'class="imageFile" id="%s" />' %  fileName

        if hidden:
            result = u'<a onclick="addRemoveElement(\'%s\', \'%s\', \'image\', ' % \
                (fileName, buttonID)
            result += u'\'hide image|show image\');"'
            result += u' class="buttonLink" id="%s" title="show image embedded ' % \
                buttonID
            result += u'in the page">show image</a>'
            result += imgTag
        else:
            result = imgTag

        return result

    def displayAudio(self, fileReference, hidden=True):
        result = self.getJavaScriptForAudio()

        fileName = self.name.replace('.', '_') 
        uniqueNo = str(randrange(0,1000))
        uniqueFileName = fileName + uniqueNo

        # A button to create an audio player in the embeddedAudioDiv
        result += u'\n\n<a '
        result += u'title="click to show audio embedded in page" '
        result += u'onclick="playAudio(\'%s\', \'%s\', \'%s\', \'%s\')">' % \
            (fileReference, fileName, self.MIMEtype, uniqueFileName)
        result += u'play audio</a> | '
        
        # A button that links directly to the audio file (for download)
        result += u'\n\n<a href="%s" ' % fileReference
        result += u'title="click to link to this audio file; '
        result += u'right-click to download this audio file">'
        result += u'link to audio</a>'
        
        # The embeddedAudioDiv for displaying the embedded audio
        result += u'\n\n<div id="%s" class="embeddedAudioDiv"></div>' % \
                  uniqueFileName

        return result

    def displayVideo(self, fileReference, hidden=True):
        """What's the problem here?...
        
        """
        
        return u'Video display has not yet been implemented ...'
    
    def displayTextual(self, fileReference, hidden=True):
        fileExtension = self.name.split('.')[-1]
        result = u'<a href="%s" class="buttonLink" ' % \
            fileReference
        result += u'title="right-click to download this %s file">' % \
            fileExtension
        result += u'link to text</a>'
        return result

    def getJavaScriptForAudio(self):
        return """
<script type="text/javascript">

  function playAudio(fileReference, fileName, MIMEtype, uniqueFileName)
  {
      var embeddedAudioDiv = document.getElementById(uniqueFileName);
      var useAudioTag = canUseHTMLAudioTag(MIMEtype);
      embeddedAudioDiv.style.display="block";
      embeddedAudioDiv.style.display="visible";
      if (useAudioTag)
      {
          var output = '<audio src="' + fileReference + '" controls="controls">';
          output += '</audio>';
      }
      else
      {
          var output = '<embed src="' + fileReference + '" autoplay="false" ';
          output += 'autostart="false" width="300" height="30" />';
      }
      embeddedAudioDiv.innerHTML = output;
  }

  function canUseHTMLAudioTag(MIMEtype)
  {
      var audio  = document.createElement("audio");
      canPlayMIMEtype = (typeof audio.canPlayType === "function" && audio.canPlayType(MIMEtype) !== "");
      return(canPlayMIMEtype);
  }

</script>"""

    def getHTMLRepresentation_(self, size=u'long'):
        """Generates an HTML representation of the File.
        
        Four components:
        
        1. metadata
        2. associated Forms
        3. action buttons
        4. representation of the File's media
        
        """

        HTMLRepresentation = u''

        # Get a string representing the type of the file
        fileType = self.getFileType()

        if size == u'long':
            # Get the metadata, associated Forms, action buttons and file data
            HTMLRepresentation += self.getMetaData(fileType)
            HTMLRepresentation += self.getAssociatedForms()

        HTMLRepresentation += self.getButtons()
        HTMLRepresentation += self.getFileMedia(fileType)
        
        if size == u'long':
            HTMLRepresentation += u'<div class="tableSpacerDiv"></div>'

        return h.literal(HTMLRepresentation)

    def getFileType(self):
        """Return the file type.  Should be one of ['audio', 'video', 'text',
        'image']
        
        """
        
        if self.MIMEtype:
            if app_globals.allowedFileTypes[self.MIMEtype]:
                return app_globals.allowedFileTypes[self.MIMEtype]
            else:
                return self.MIMEtype.split('/')[0]
        else:
            return u'embedded media'

    def getMetaData(self, fileType):
        """Returns an HTML table representation of the metadata of this File.

        """

        result = u'<table class="fileTable">'
        result += u'\n <tr>\n  <td class="fileTableRowLabel">ID</td>'
        result += u'\n  <td class="dataCell">%s</td>\n </tr>' % self.id
        result += u'\n <tr>\n  <td class="fileTableRowLabel">name</td>'
        result += u'\n  <td class="dataCellTr">%s</td>\n </tr>' % self.name
        result += u'\n <tr>\n  <td class="fileTableRowLabel">type</td>'
        result += u'\n  <td class="dataCell">%s</td>\n </tr>' % fileType
        result += u'\n <tr>\n  <td class="fileTableRowLabel">size</td>'
        result += u'\n  <td class="dataCell">%s</td>\n </tr>' % \
                  h.pretty_filesize(self.size)

        if self.description:
            result += u'\n <tr>\n  <td class="fileTableRowLabel">description</td>'
            result += u'\n  <td class="dataCell">%s</td>\n </tr>' % self.description

        if self.utteranceType:
            result += u'\n <tr>\n  <td class="fileTableRowLabel">utterance type</td>'
            result += u'\n  <td class="dataCell">%s</td>\n </tr>' % self.utteranceType

        result += u'\n <tr>\n  <td class="fileTableRowLabel">enterer</td>'
        result += u'\n  <td class="dataCell">%s %s</td>\n </tr>' % (
            self.enterer.firstName, self.enterer.lastName)

        if self.speaker:
            result += u'\n <tr>\n  <td class="fileTableRowLabel">speaker</td>'
            result += u'\n  <td class="dataCell">%s %s</td>\n </tr>' % (
                self.speaker.firstName, self.speaker.lastName)

        if self.elicitor:
            result += u'\n <tr>\n  <td class="fileTableRowLabel">elicitor</td>'
            result += u'\n  <td class="dataCell">%s %s</td>\n </tr>' % (
                self.elicitor.firstName, self.elicitor.lastName)

        if self.dateElicited:
            result += u'\n <tr>\n  <td class="fileTableRowLabel">date elicited</td>'
            result += u'\n  <td class="dataCell">%s</td>\n </tr>' % \
                      h.pretty_date(self.dateElicited)

        result += u'\n <tr>\n  <td class="fileTableRowLabel">time entered</td>'
        result += u'\n  <td class="dataCell">%s</td>\n </tr>' % \
                  h.pretty_date(self.datetimeEntered)
        result += u'\n <tr>\n  <td class="fileTableRowLabel">last updated</td>'
        result += u'\n  <td class="dataCell">%s</td>\n </tr>' % \
                  h.pretty_date(self.datetimeModified)
        result += u'</table>'

        return result

    def getButtons(self):
        """Return an HTML div containing links to various File actions: update,
        delete and associate.
        
        """

        updateURL = url(controller='file', action='update', id=self.id)
        deleteURL = url(controller='file', action='delete', id=self.id)
        associateURL = url(controller='file', action='associate', id=self.id)
        
        result = u'<div class="fileButtonsDiv">'
        
        result += u'\n <a href="%s" ' % updateURL
        result += u'class="buttonLink" title="Edit this File\'s data">' 
        result += u'\n  update\n </a>'
        
        result += u'\n <a href="%s" class="buttonLink" ' % deleteURL
        result += u'onclick="return confirmDelete(\'File\', %s)" ' % self.id
        result += u'title="Delete this File; confirmation will be requested">'
        result += u'\n  delete\n </a>'
        
        result += u'\n <a href="%s" class="buttonLink" ' % associateURL
        result += u'title="Associate one or more Forms to this File">\n  '
        result += u'associate\n </a>'
        
        result += u'</div>'

        return result


if __name__ == '__main__':
    form = Form()

    form.transcription = u'anna ninaa itsinoyii ami aakii ki ikaakomimmoka matonni'
    form.morphemeBreak = u'ann-wa ninaa it-ino-yii am-yi aakii ki iik-waakomimm-ok-wa matonni'
    form.morphemeGloss = u'DEM-3PROX man LOC-see-DIR DEM-3OBV woman and INT-love-INV-3SG yesterday'
    form.gloss = u'the man saw that woman and he loved her yesterday'   

    preppedForm = getPreppedForm(form)
