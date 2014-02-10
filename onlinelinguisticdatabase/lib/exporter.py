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

import re
from pylons import session
import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta
import onlinelinguisticdatabase.lib.helpers as h

"""The exporter module defines exporter objects used to create OLD export strings
which can then be saved as files.

The global variable ``exporters`` is a list containing all the exporter instances
that will be imported by the export controller and thereby made available for
exporting.  To create a new export option, define a new exporter object and add it
to the ``exporters`` global.

This module provides several exporter classes to facilitate the creation of
exporter objects:

    ``Exporter``
    ``FormListExporter``
    ``XeLaTeXFormListExporter``
    ``XeLaTeXCollectionExporter``

A working exporter object *must* valuate the following five attributes/methods:

1. ``name``: identifies the exporter
2. ``description``: information about what the exporter does
3. ``extension``: the extension that should be given to the resultant file
4. ``input_types``: a method that takes an as input a string representing the
    type of object to be exported and returns a boolean indicating whether the
    exporter exports that type of object.
5. ``exporter``: method that takes as input a string representing the
    object to be exported and returns the export as a unicode string.

The input to ``exporter.export`` must be one of the following strings or types
of string:

1. 'form<x>', where '<x>' is the ``id`` value of a form
2. 'collectionforms<x>', where '<x>' is the ``id`` value of a collection
3. 'collectioncontent<x>', where '<x>' is the ``id`` value of a collection
4. 'memory'
5. 'lastsearch'

"""


class Exporter(object):
    """Base class for exporter instances.

    """

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def export(self, input_):
        return self.exporter_function(input_)

    ################################################################################
    # Methods for getting exportables from the ``input`` string.
    ################################################################################

    def get_form_list(self, input_):
        """Returns a list of Forms.  The value of ``input_`` must be one of the
        following four strings/ types of string:

        1. 'form<x>', where '<x>' is the ``id`` value of a form
        2. 'collectionforms<x>', where '<x>' is the ``id`` value of a collection
        3. 'memory'
        4. 'lastsearch'

        """

        if input_.startswith('form'):
            return self.get_form_list_from_form_id(int(input_[4:]))
        elif input_.startswith('collectionforms'):
            return self.get_form_list_from_collection_id(int(input_[15:]))
        elif input_ == 'memory':
            return self.get_form_list_from_memory()
        elif input_ == 'lastsearch':
            return self.get_form_list_from_last_search()
        else:
            return None

    def get_form_list_from_form_id(self, form_id):
        return [meta.Session.query(model.Form).get(form_id)]

    def get_form_list_from_collection_id(self, collection_id):
        return meta.Session.query(model.Collection).get(collection_id).forms

    def get_form_list_from_memory(self):
        """Return the list of all Forms memorized by the currently logged in user.

        """
        return meta.Session.query(model.Form).\
            order_by(model.Form.id).\
            filter(model.Form.memorizers.contains(session['user'])).all()

    def get_form_list_from_last_search(self):
        """Whenever a OLD Form search is effected, the values of the HTML Form Search
        form are stored in the session under the key 'formSearchValues'.  Use these
        values to recreate the last search and return the resultant Forms.

        """
        form_search = session.get('formSearchValues', None)
        if form_search:
            return h.filterSearchQuery(
                form_search, meta.Session.query(model.Form), 'Form').\
                order_by(model.Form.id).all()
        return []

    def get_collection_content(self, input_):
        """Return the content of the Collection with ID=collection_id.

        """
        collection_id = int(input_[17:])
        return meta.Session.query(model.Collection).get(collection_id).contents

    def get_collection(self, input_):
        """Return the Collection with ID=collection_id.

        """
        collection_id = int(input_[17:])
        return meta.Session.query(model.Collection).get(collection_id)

    ################################################################################
    # Input type selectors
    ################################################################################

    def is_form_list(self, input_):
        """Return ``True`` if ``input_`` represents a list of forms; ``False`` otherwise.
        """
        return (input_ in ('memory', 'lastsearch') or
            input_.startswith('form') or
            input_.startswith('collectionforms'))

    def is_collection_content(self, input_):
        """Return ``True`` if ``input_`` represents a collection's content; ``False`` otherwise.
        """
        return input_.startswith('collectioncontent')

    ################################################################################
    # Plain text form formatters
    ################################################################################

    def txt_tr_formatter(self, form):
        """Return the grammaticality followed by the transcription.

        """
        return '%s%s' % (form.grammaticality,
                        h.storageToOutputTranslate(form.transcription))

    def txt_tr_tl_formatter(self, form):
        """Return the (grammaticality + ) transcription, followed by each translation
        (with grammaticality) on its own line.

        """
        result = [
            '%s%s' % (form.grammaticality,
                    h.storageToOutputTranslate(form.transcription)),
            '\n%s' % '\n'.join(['%s%s' % (gloss.glossGrammaticality, gloss.gloss)
                for gloss in form.glosses])
        ]
        return u''.join(result)

    def txt_igt_formatter(self, form):
        """Interlinear Gloss Text: transcription, morphemeBreak, morphemeGloss, gloss
        all separated by newlines.

        """
        result = [u'%s%s' % (form.grammaticality,
            h.storageToOutputTranslate(form.transcription))]
        if form.morphemeBreak:
            result.append(u'\n%s' % h.storageToOutputTranslate(form.morphemeBreak, True))
        if form.morphemeGloss:
            result.append(u'\n%s' % form.morphemeGloss)
        result.append(u'\n%s' % u'\n'.join([u'%s%s' % (gloss.glossGrammaticality,
            gloss.gloss) for gloss in form.glosses]))
        return u''.join(result)

    def txt_secondary_data(self, form):
        """Comments, speaker comments and an 'OLD reference' separated by newlines.
        The 'OLD reference' is the date elicited followed by the ID in parentheses.

        """
        result = []
        if form.comments:
            result.append(h.storageToOutputTranslateOLOnly(form.comments))
        if form.speakerComments:
            result.append(h.storageToOutputTranslateOLOnly(form.speakerComments))
        if form.dateElicited:
            result.append(u'%s (%s)' % (form.dateElicited.strftime('%b %d, %Y'), form.id))
        else:
            result.append(u'(%s)' % form.id)
        return u'\n'.join(result)

    def txt_igt_secondary_formatter(self, form):
        """Plain text IGT plus secondary data.

        """
        return u'%s\n%s' % (self.txt_igt_formatter(form), self.txt_secondary_data(form))

    def no_tabs(self, string):
        return string.replace(u'\t', u' ')

    def all_tab_delimited_formatter(self, form):
        """All the data of a form, tab-delimited.

        """
        form_list = [
            str(form.id),
            self.no_tabs(u'%s%s' % (form.grammaticality,
                    h.storageToOutputTranslate(form.transcription))),
            self.no_tabs(form.narrowPhoneticTranscription) or u'',
            self.no_tabs(form.phoneticTranscription) or u'',
            self.no_tabs(h.storageToOutputTranslate(form.morphemeBreak, True)) or u'',
            self.no_tabs(form.morphemeGloss) or u'',
            self.no_tabs(u'; '.join(['%s%s' % (x.glossGrammaticality,
                            x.gloss.replace(';', '.')) for x in form.glosses])),
            form.comments and self.no_tabs(h.storageToOutputTranslateOLOnly(form.comments)) or u'',
            form.speakerComments and self.no_tabs(h.storageToOutputTranslateOLOnly(
                form.speakerComments)) or u'',
            form.dateElicited and self.no_tabs(form.dateElicited.strftime('%b %d, %Y')) or u'',
            form.datetimeEntered and self.no_tabs(form.datetimeEntered.strftime(
                '%b %d, %Y at %I:%M %p')) or u'',
            form.datetimeModified and self.no_tabs(form.datetimeModified.strftime(
                '%b %d, %Y at %I:%M %p')) or u'',
            form.syntacticCategoryString and self.no_tabs(form.syntacticCategoryString) or u'',
            form.elicitor and self.no_tabs(u'%s %s' % (form.elicitor.firstName,
                                        form.elicitor.lastName)) or u'',
            form.enterer and self.no_tabs(u'%s %s' % (form.enterer.firstName,
                                        form.enterer.lastName)) or u'',
            form.verifier and self.no_tabs(u'%s %s' % (form.verifier.firstName,
                                        form.verifier.lastName)) or u'',
            form.speaker and self.no_tabs(u'%s %s' % (form.speaker.firstName,
                                        form.speaker.lastName)) or u'',
            form.elicitationMethod and self.no_tabs(form.elicitationMethod.name) or u'',
            form.syntacticCategory and self.no_tabs(form.syntacticCategory.name) or u'',
            form.source and self.no_tabs(u'%s (%s)' % (form.source.authorLastName,
                                        form.source.year)) or u'',
            form.keywords and self.no_tabs(u'; '.join(
                [x.name.replace(u';', u'.') for x in form.keywords])) or u''
        ]
        return u'\t'.join([x.replace('\t', ' ') for x in form_list])

    ################################################################################
    # XeLaTeX form formatters
    ################################################################################

    def esc_latex(self, string):
        """Escape the 10 LaTeX special characters.

        """
        try:
            return string.replace('\\', r'\textbackslash').\
                    replace('{', r'\{').\
                    replace('}', r'\}').\
                    replace('textbackslash', 'textbackslash{}').\
                    replace('&', r'\&').\
                    replace('%', r'\%').\
                    replace('$', r'\$').\
                    replace('#', r'\#').\
                    replace('_', r'\_').\
                    replace('~', r'\textasciitilde{}').\
                    replace('^', r'\textasciicircum{}')
        except Exception:
            return string

    def xelatex_secondary_data(self, form, reference=True):
        """Return the Form's comments, speaker comments and a reference as a LaTeX
        itemized list.  Reference is 'x(yz)' where 'x' is the speaker's initials,
        'y' is the date elicited and 'z' is the id of the Form.  If reference is
        False, no reference to the Form is added.

        """

        result = [u'\t\\begin{itemize}']
        if form.comments:
            result.append(u'\n\t\t\\item %s' % self.esc_latex(h.storageToOutputTranslateOLOnly(
                form.comments)))
        if form.speakerComments:
            result.append(u'\n\t\t\\item %s' % self.esc_latex(h.storageToOutputTranslateOLOnly(
                form.speakerComments)))
        if reference:
            if form.speaker:
                speaker = u'%s%s ' % (self.esc_latex(form.speaker.firstName[0].upper()),
                    self.esc_latex(form.speaker.lastName[0].upper()))
            else:
                speaker = u''
            if form.dateElicited:
                dateElicited = self.esc_latex(form.dateElicited.strftime('%b %d, %Y; '))
            else:
                dateElicited = u''
            if form.speaker:
                result.append(u'\n\t\t\\item %s(%s%s)' % (
                    speaker, dateElicited, 'OLD ID: %s' % form.id))
            elif form.source:
                source = '%s (%s) ' % (self.esc_latex(form.source.authorLastName), form.source.year)
                result.append(u'\n\t\t\\item %s(%s)' % (source, 'OLD ID: %s' % form.id))
            else:
                result.append(u'\n\t\t\\item (%s%s)' % (
                    dateElicited, 'OLD ID: %s' % form.id))
        result.append(u'\n\t\\end{itemize}')
        if len(result) > 2:
            return u''.join(result)
        return u''

    def covington_form_formatter(self, form, **kwargs):
        """A XeLaTeX representation of a Form using the Covington package to put the
        words into IGT formatted examples.  Because non-ascii characters might occur
        in the Form, XeLaTeX (not just plain LaTeX) will be required to process the
        document.

        Note: I was originally using h.capsToLatexSmallCaps to convert uppercase
        glosses to LaTeX smallcaps (\textsc{}), but the Aboriginal Serif font was
        not rendering the smallcaps, so I removed the function.  If I can figure out
        how to use XeLaTeX with a font that will render NAPA symbols AND make
        smallcaps, then the function should be reinstated...

        """

        result = [u'\n\n\\begin{examples}\n']
        if not form:
            result.append(u'\t\\item WARNING: BAD FORM REFERENCE')
        else:
            # If the Form has a morphological analysis, use Covington for IGT
            if form.morphemeBreak and form.morphemeGloss:
                result.extend([
                    u'\t\\item'
                    u'\n\t\t\\glll %s%s' % (self.esc_latex(form.grammaticality),
                        self.esc_latex(h.storageToOutputTranslate(form.transcription))),
                    u'\n\t\t%s' % self.esc_latex(h.storageToOutputTranslate(form.morphemeBreak, True)),
                    u'\n\t\t%s' % self.esc_latex(form.morphemeGloss),
                    u'\n\t\t\\glt %s' % u'\\\\ \n\t\t'.join(
                        [u"%s`%s'" % (self.esc_latex(gloss.glossGrammaticality), self.esc_latex(gloss.gloss))
                        for gloss in form.glosses]),
                    u'\n\t\t\\glend'
                ])
            # If no morphological analysis, just put transcr and gloss(es) on separate lines
            else:
                result.extend([
                    u'\t\\item',
                    u'\n\t\t%s%s \\\\' % (self.esc_latex(form.grammaticality),
                        self.esc_latex(h.storageToOutputTranslate(form.transcription))),
                    u'\n\t\t%s' % ' \\\\\n\t\t'.join([u"%s`%s'" % (
                        self.esc_latex(gloss.glossGrammaticality), self.esc_latex(gloss.gloss))
                        for gloss in form.glosses])
                ])
            if kwargs.get('secondary_data', False):
                result.extend([
                    u'\n',
                    self.xelatex_secondary_data(form, kwargs.get('reference', False))
                ])
        result.append(u'\n\\end{examples}')
        return u''.join(result)

    def expex_trailing_citation(self, form):
        trailing_citation = [u'\\trailingcitation{(']
        if form.speaker:
            speaker = [u'%s%s' % (
                self.esc_latex(form.speaker.firstName[0].upper()),
                self.esc_latex(form.speaker.lastName[0].upper()))]
            if form.dateElicited:
                speaker.append(self.esc_latex(form.dateElicited.strftime(', %b %d, %Y')))
            trailing_citation.extend(speaker)
        elif form.source:
            trailing_citation.append(u'%s, %s' % (
                self.esc_latex(form.source.authorLastName), form.source.year))
        else:
            trailing_citation.append(u'OLD ID: %s' % form.id)
        trailing_citation.append(u')}')
        return u''.join(trailing_citation)

    def expex_form_formatter(self, form, **kwargs):
        """A XeLaTeX representation of a Form using the ExPex package to put the
        words into IGT formatted examples.  Because non-ascii characters might occur
        in the Form, XeLaTeX (not just plain LaTeX) will be required to process the
        document. 

        """

        result = [u'\n\n\\ex\n']
        if not form:
            result.append(u'\tWARNING: BAD FORM REFERENCE')
        else:
            trailing_citation = self.expex_trailing_citation(form)
            result.extend([
                u'\t\\begingl'
                u'\n\t\t\\gla %s%s//' % (self.esc_latex(form.grammaticality),
                    self.esc_latex(h.storageToOutputTranslate(form.transcription)))
            ])
            if form.narrowPhoneticTranscription:
                result.append(u'\n\t\t\\glb %s//' % self.esc_latex(form.narrowPhoneticTranscription))
            if form.phoneticTranscription:
                result.append(u'\n\t\t\\glb %s//' % self.esc_latex(form.phoneticTranscription))
            if form.morphemeBreak:
                result.append(u'\n\t\t\\glb %s//' % self.esc_latex(
                    h.storageToOutputTranslate(form.morphemeBreak, True)))
            if form.morphemeGloss:
                result.append(u'\n\t\t\\glb %s//' % self.esc_latex(form.morphemeGloss))
            result.extend([
                u'\n\t\t\\glft %s%s//' % (
                    '\\\\\n\t\t'.join(
                        u"%s`%s'" % (self.esc_latex(gloss.glossGrammaticality), self.esc_latex(gloss.gloss))
                        for gloss in form.glosses),
                    trailing_citation),
                u'\n\t\\endgl'
            ])
            if kwargs.get('secondary_data', False):
                result.extend([
                    u'\n',
                    self.xelatex_secondary_data(form, kwargs.get('reference', False))
                ])
        result.append(u'\n\\xe')
        return u''.join(result)


class FormListExporter(Exporter):
    """Creates exporter instances that return documents representing lists of OLD forms.
    """

    def __init__(self, **kwargs):
        self.extension = 'txt'
        self.input_types = self.is_form_list
        form_formatter = kwargs.pop('form_formatter', 'txt_tr_formatter')
        form_delimiter = kwargs.pop('form_delimiter', u'\n')
        header = kwargs.pop('header', None)
        self.exporter_function = self.get_exporter_function(
            form_formatter=form_formatter,
            form_delimiter=form_delimiter,
            header=header)
        super(FormListExporter, self).__init__(**kwargs)

    def get_exporter_function(self, **kwargs):
        form_formatter = getattr(self, kwargs.get('form_formatter', 'txt_tr_formatter'))
        form_delimiter = kwargs.get('form_delimiter', u'\n')
        header = kwargs.get('header', None)
        def exporter_function(input_):
            form_list = self.get_form_list(input_)
            forms = []
            if header:
                forms.append(header)
            forms.extend([form_formatter(form) for form in form_list])
            return form_delimiter.join(forms)
        return exporter_function


class XeLaTeXFormListExporter(Exporter):
    """Creates exporter objects that return XeLaTeX documents representing lists of forms.

    """

    def __init__(self, **kwargs):
        self.extension = 'tex'
        self.input_types = self.is_form_list
        form_formatter = kwargs.pop('form_formatter', 'covington_form_formatter')
        igt_package = kwargs.pop('igt_package', 'covington')
        secondary_data = kwargs.pop('secondary_data', False)
        reference = kwargs.pop('reference', False)
        self.exporter_function = self.get_exporter_function(
            form_formatter=form_formatter,
            igt_package=igt_package,
            secondary_data=secondary_data,
            reference=reference
        )
        super(XeLaTeXFormListExporter, self).__init__(**kwargs)

    def get_exporter_function(self, **kwargs):

        form_formatter = getattr(self, kwargs.get('form_formatter', 'covington_form_formatter'))
        igt_package = {
            'covington': h.covington_package,
            'expex': h.expex_package
        }.get(kwargs.get('igt_package', 'covington'))
        secondary_data = kwargs.get('secondary_data', False)
        reference = kwargs.get('reference', False)

        def exporter_function(input_):

            form_list = self.get_form_list(input_)
            result = [
                u'\\documentclass{article}\n\n%s\n%s' % (h.xelatex_preamble, igt_package),
                u'\n\n\\begin{document}\n\n\\title{OLD Export}',
                u'\n\\author{%s %s}\n\\maketitle\n\n' % (session['user_firstName'],
                    session['user_lastName']),
                u'\n\n'.join([
                    form_formatter(f, secondary_data=secondary_data, reference=reference)
                    for f in form_list]),
                u'\n\n\\end{document}'
            ]
            return u''.join(result)

        return exporter_function


class XeLaTeXCollectionExporter(Exporter):
    """Creates exporter instances that return XeLaTeX documents representing OLD collections.

    """

    def __init__(self, **kwargs):
        self.input_types = self.is_collection_content
        self.extension = 'tex'
        form_formatter = kwargs.pop('form_formatter', 'covington_form_formatter')
        igt_package = kwargs.pop('igt_package', 'covington')
        self.exporter_function = self.get_exporter_function(
            form_formatter=form_formatter, igt_package=igt_package)
        super(XeLaTeXCollectionExporter, self).__init__(**kwargs)

    def get_exporter_function(self, **kwargs):
        """Return an exporter function.

        :param function kwargs['form_formatter']: function that takes a form and returns
            a string representation of it.
        :param str kwargs['igt_package']: name of a LaTeX package for formatting linguistic
            examples ('covington' or 'expex').
        :returns: a function that takes as input a string identifying an object to export
            and returns a string constituting the content of the export file.

        """
        form_formatter = getattr(self, kwargs.get('form_formatter', 'covington_form_formatter'))
        igt_package = kwargs.get('igt_package', 'covington')

        def exporter_function(input_):

            def get_form_from_list_of_forms(form_list, match_obj):
                """Input is a list of Forms and a re Match object.  (The form_id will be
                recoverable as the first backreference of the Match object.)  The output
                is the Form in the list whose ID is the ID extracted from the match_obj

                """

                form_id = int(match_obj.group(1))
                form_dict = dict((form.id, form) for form in form_list)
                return form_dict.get(form_id, None)

            # Get the Collection's contents data
            collection = self.get_collection(input_)
            content = collection.contents

            # Convert to LaTeX (actually, a hacky XeLaTeX-processable document)
            content = h.rst2latex(content, igt_package=igt_package)

            # Insert a title into the (Xe)LaTeX string
            date_modified = collection.datetimeModified.strftime('%b %d, %Y')
            title = '\\title{%s}\n\\author{\\textit{entered by:} %s \\\\ \n \
                \\textit{exported by:} %s} \n\\date{%s}\n\\maketitle' % (
                    collection.title,
                    '%s %s' % (collection.enterer.firstName, collection.enterer.lastName),
                    '%s %s' % (session['user_firstName'], session['user_lastName']),
                    date_modified
                )
            content = content.replace('\\begin{document}', '\\begin{document}\n\n%s' % \
                                      title)

            # Replace Form references with Covington-styled IGT examples
            patt = re.compile('[Ff]orm\{\[\}([0-9]+)\{\]\}')
            return patt.sub(lambda x: form_formatter(
                get_form_from_list_of_forms(collection.forms, x)), content)

        return exporter_function


################################################################################
# Exporter Instances
################################################################################

# Form Transcription (.txt)
################################################################################

txt_forms_tr = FormListExporter(
    name = u'Transcription Only',
    description = (u'Plain text export.  Outputs a string of newline-delimited '
        u'form transcriptions (prefixed with grammaticalities).'),
)

# Form Transcription & Translation(s) (.txt)
################################################################################

txt_forms_tr_tl = FormListExporter(
    name = u'Transcription & Translation(s)',
    description = (u'Plain text export.  Each form is exported as its transcription '
        u'(with grammaticality), followed by a linebreak, followed by a linebreak-'
        u'separated list of its translations (with grammaticalities).  The form '
        u'representations are separated by two linebreaks.'),
    form_formatter = 'txt_tr_tl_formatter',
    form_delimiter = u'\n\n'
)

# Interlinear Gloss Text (.txt)
################################################################################

txt_forms_igt = FormListExporter(
    name = u'Interlinear Gloss Text',
    description = (u'Plain text export.  Outputs Forms as newline-separated '
        u'quadruples consisting of: (1) transcription, (2) morpheme break, (3) '
        u'morpheme gloss and (4) gloss(es).  These quadruples are separated by '
        u'double newlines.'),
    form_formatter = 'txt_igt_formatter',
    form_delimiter = u'\n\n'
)

# Interlinear Gloss Text + (.txt)
################################################################################

txt_forms_igt_plus = FormListExporter(
    name = u'Interlinear Gloss Text +',
    description = (u'Plain text export.  Outputs Forms as newline-separated '
        u'septuples consisting of: (1) transcription, (2) morpheme break, (3) morpheme '
        u'gloss, (4) gloss(es), (5) comments, (6) speaker comments (7) ID reference.  The '
        u'ID reference is the date elicited (if specified) followed by the Form ID.  These '
        u'septuples are separated by double newlines.'),
    form_delimiter = u'\n\n',
    form_formatter = 'txt_igt_secondary_formatter'
)

# Tab-delimited Everything (.txt)
################################################################################

txt_forms_tab_all = FormListExporter(
    name = u'Tab-delimited Everything',
    description = (u'Plain text export.  Each Form is output on its own line '
        u'with tabs delimiting each field.  This format can be opened by a spreadsheet '
        u'program like OpenOffice.org Calc or Microsoft Excel.'),
    header = u'\t'.join([
        'ID',
        'transcription',
        'narrow phonetic transcription',
        'broad phonetic transcription',
        'morpheme break',
        'morpheme gloss',
        'gloss(es)',
        'comments',
        'speaker comments',
        'date elicited',
        'date and time entered',
        'date and time modified',
        'category string',
        'elicitor',
        'enterer',
        'verifier',
        'speaker',
        'elicitation method',
        'category',
        'source',
        'keywords'
    ]),
    form_formatter = 'all_tab_delimited_formatter'
)

# XeLaTeX IGT (ExPex) (.tex)
################################################################################

xelatex_list_expex = XeLaTeXFormListExporter(
    name = u'XeLaTeX IGT (ExPex)',
    description = (u'XeLaTeX export.  Outputs Forms in IGT format using the '
        u'ExPex package to put the form\'s content into interlinear gloss '
        u'text format.'),
    form_formatter = 'expex_form_formatter',
    igt_package = 'expex'
)

# XeLaTeX IGT (ExPex) + (.tex)
################################################################################

xelatex_list_expex = XeLaTeXFormListExporter(
    name = u'XeLaTeX IGT (ExPex) +',
    description = (u"XeLaTeX export.  Same as 'XeLaTeX IGT (Expex)' except that "
        u'the comments and speaker comments fiels (if valued) are included as '
        u'items in a list beneath each form.'),
    form_formatter = 'expex_form_formatter',
    igt_package = 'expex',
    secondary_data = True
)

# XeLaTeX IGT (Covington) (.tex)
################################################################################

xelatex_list_covington = XeLaTeXFormListExporter(
    name = u'XeLaTeX IGT (Covington)',
    description = (u'XeLaTeX export.  Outputs Forms in IGT format using the '
        u'Covington package to put the form\'s content into interlinear gloss '
        u'text format.  The IGT representation contains the following '
        u'fields: (1) transcription, (2) morpheme break, (3) morpheme gloss and '
        u'(4) gloss(es).'),
)

# XeLaTeX IGT (Covington) + (.tex)
################################################################################

xelatex_list_covington_plus = XeLaTeXFormListExporter(
    name = u'XeLaTeX IGT (Covington) +',
    description = (u"XeLaTeX export.  Same as 'XeLaTeX IGT (Covington)' "
        u'except that the comments and speaker comments fields (if present) are '
        u'included as items of a list beneath each form.'),
    secondary_data = True
)

# XeLaTeX IGT (Covington) ++ (.tex)
################################################################################

xelatex_list_covington_plus_plus = XeLaTeXFormListExporter(
    name = u'XeLaTeX IGT (Covington) ++',
    description = (u"XeLaTeX export.  Same as 'XeLaTeX IGT (Covington) +' "
        u'except that beneath any comments or speaker comments items is a an item '
        u"containing a reference to the Form.  This reference is the speaker's initials "
        u"followed by the date elicited and the Form's ID.  If there is no speaker, but "
        u'there is a source, then a reference to the source takes the place of the '
        u"speaker's initials."),
    secondary_data = True,
    reference = True
)

# XeLaTeX Collection Report -- Covington
################################################################################

xelatex_collection_covington = XeLaTeXCollectionExporter(
    name=u'XeLaTeX Report (Covington)',
    description=(u'XeLaTeX export with interlinear gloss text examples formatted '
        u'using the Covington package.  Assumes the input is reStructuredText. '
        u'Uses docutils.core to convert the RST to LaTeX.')
)

# XeLaTeX Collection Report -- ExPex
################################################################################

xelatex_collection_expex = XeLaTeXCollectionExporter(
    name=u'XeLaTeX Report (ExPex)',
    description=(u'XeLaTeX export with interlinear gloss text examples formatted '
        u'using the ExPex package.  Assumes the input is reStructuredText. '
        u'Uses docutils.core to convert the RST to LaTeX.'),
    form_formatter='expex_form_formatter',
    igt_package='expex'
)

################################################################################
# Global exporters variable
################################################################################

exporters = [
    txt_forms_tr,
    txt_forms_tr_tl,
    txt_forms_igt,
    txt_forms_igt_plus,
    txt_forms_tab_all,
    xelatex_list_expex,
    xelatex_list_covington,
    xelatex_list_covington_plus,
    xelatex_list_covington_plus_plus,
    xelatex_collection_expex,
    xelatex_collection_covington
]

