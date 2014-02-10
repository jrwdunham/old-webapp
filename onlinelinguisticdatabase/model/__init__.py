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

"""The application's model objects"""
import sqlalchemy as sa
from sqlalchemy import orm, schema, types

import datetime

from onlinelinguisticdatabase.model import meta
from onlinelinguisticdatabase.lib.oldCoreObjects import Form, FormBackup, File
from onlinelinguisticdatabase.lib.oldCoreObjects import Collection, CollectionBackup
from onlinelinguisticdatabase.lib.analysisObjects import Phonology

def init_model(engine):
    """Call me before using any of the tables or classes in the model"""
    ## Reflected tables must be defined and mapped here
    #global reflected_table
    #reflected_table = sa.Table("Reflected", meta.metadata, autoload=True,
    #                           autoload_with=engine)
    #orm.mapper(Reflected, reflected_table)
    #
    meta.Session.configure(bind=engine)
    meta.engine = engine


def now():
    return datetime.datetime.utcnow()

################
# PRIMARY TABLES
################

# form_table holds the data that constitute OLD Forms
form_table = schema.Table('form', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('form_seq_id', optional=True), primary_key=True),

    # Textual values
    # transcription -- orthographic, obligatory
    schema.Column('transcription', types.Unicode(255), nullable=False),
    # phonetic transcription -- broad, optional
    schema.Column('phoneticTranscription', types.Unicode(255)),
    # narrow phonetic transcription -- optional
    schema.Column('narrowPhoneticTranscription', types.Unicode(255)),
    schema.Column('morphemeBreak', types.Unicode(255)),
    schema.Column('morphemeGloss', types.Unicode(255)),
    schema.Column('comments', types.UnicodeText()),
    schema.Column('speakerComments', types.UnicodeText()), 

    # Forced choice textual values
    schema.Column('grammaticality', types.Unicode(255)),

    # Temporal values: only dateElicited is consciously enterable by the user
    schema.Column('dateElicited', types.Date()),
    schema.Column('datetimeEntered', types.DateTime()),    
    schema.Column('datetimeModified', types.DateTime(), default=now),

    # syntacticCategoryString: OLD-generated value 
    schema.Column('syntacticCategoryString', types.Unicode(255)),

    # morphemeBreakIDs and morphemeGlossIDs: OLD-generated values
    schema.Column('morphemeBreakIDs', types.Unicode(1023)),
    schema.Column('morphemeGlossIDs', types.Unicode(1023)),

    # breakGlossCategory: OLD-generated value, e.g., 'chien|dog|N-s|PL|NUM'
    schema.Column('breakGlossCategory', types.Unicode(1023)),

    # A Form can have only one each of elicitor, enterer and verifier, but each 
    # of these can have more than one form
    # Form-User = Many-to-One
    schema.Column('elicitor_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('enterer_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('verifier_id', types.Integer, schema.ForeignKey('user.id')),

    # A Form can have only one speaker, but a speaker can have more than one
    #  Form.  
    # Form-Speaker = Many-to-One
    schema.Column('speaker_id', types.Integer, schema.ForeignKey('speaker.id')),

    # A Form can have only one elicitationMethod, but an EM can have more than
    #  one Form.
    # Form-ElicitationMethod = Many-to-One
    schema.Column('elicitationmethod_id', types.Integer,
                  schema.ForeignKey('elicitationmethod.id')),

    # A Form can have only one SyntacticCategory, but a SC can have more than
    #  one Form.
    # Form-SyntacticCategory = Many-to-One
    schema.Column('syntacticcategory_id', types.Integer,
                  schema.ForeignKey('syntacticcategory.id')),

    # A Form can have only one Source, but a Source can have more than one Form.
    # Form-Source = Many-to-One
    schema.Column('source_id', types.Integer,
                  schema.ForeignKey('source.id'))

    # A Form can have many glosses (with a glossGrammaticality), but a gloss
    #  has only one Form.
    # Form-Gloss = One-to-Many
                            
    # Keywords - a Form can have many Keywords and a Keyword can have many
    #  Forms: Many-to-Many
    
    # Files - a Form can have many Files and a File can have many Forms:
    #  Many-to-Many
)

# gloss_table holds the glosses for OLD Forms
gloss_table = schema.Table('gloss', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('gloss_seq_id', optional=True), primary_key=True),
    schema.Column('gloss', types.UnicodeText(), nullable=False),
    schema.Column('glossGrammaticality', types.Unicode(255)),

    # A Gloss can have only one Form, but a Form can have many Glosses.
    # Gloss-Form = Many-to-One
    schema.Column('form_id', types.Integer, schema.ForeignKey('form.id')),
    
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

# file_table holds the info about OLD Files (i.e., images, audio, video, PDFs) 
file_table = schema.Table('file', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('file_seq_id', optional=True), primary_key=True),

    schema.Column('name', types.Unicode(255), unique=True),
    schema.Column('MIMEtype', types.Unicode(255)),
    schema.Column('size', types.Integer),
    schema.Column('enterer_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('description', types.UnicodeText()),

    schema.Column('dateElicited', types.Date()),
    schema.Column('datetimeEntered', types.DateTime()),    
    schema.Column('datetimeModified', types.DateTime(), default=now),

    # A File can have only one each of elicitor or speaker but each 
    # of these can have more than one File
    schema.Column('elicitor_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('speaker_id', types.Integer, schema.ForeignKey('speaker.id')),

    # Utterance type: object lang only, metalang only, mixed, none
    schema.Column('utteranceType', types.Unicode(255)),

    # Fields used if the File is located on another server and its content is
    #  embedded in OLD
    schema.Column('embeddedFileMarkup', types.UnicodeText()),
    schema.Column('embeddedFilePassword', types.Unicode(255))
)

# collection_table holds info about OLD Collections: stories, discourses,
#  elicitations, ...
collection_table = schema.Table('collection', meta.metadata, 
    schema.Column('id', types.Integer,
        schema.Sequence('collection_seq_id', optional=True), primary_key=True),

    schema.Column('title', types.Unicode(255)),
    schema.Column('type', types.Unicode(255)),
    schema.Column('url', types.Unicode(255)),

    # Foreign key columns
    schema.Column('speaker_id', types.Integer, schema.ForeignKey('speaker.id')),
    schema.Column('source_id', types.Integer, schema.ForeignKey('source.id')),
    schema.Column('elicitor_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('enterer_id', types.Integer, schema.ForeignKey('user.id')),

    schema.Column('dateElicited', types.Date()),
    schema.Column('datetimeEntered', types.DateTime()),
    schema.Column('datetimeModified', types.DateTime(), default=now),

    schema.Column('description', types.UnicodeText()),
    schema.Column('contents', types.UnicodeText())
)

# user_table holds info about registered users
user_table = schema.Table('user', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('user_seq_id', optional=True), primary_key=True),

    schema.Column('username', types.Unicode(255), unique=True),
    schema.Column('password', types.Unicode(255)),
    schema.Column('firstName', types.Unicode(255)),
    schema.Column('lastName', types.Unicode(255)),
    schema.Column('email', types.Unicode(255)),
    schema.Column('affiliation', types.Unicode(255)),
    schema.Column('role', types.Unicode(255)),
    schema.Column('personalPageContent', types.UnicodeText()),
    schema.Column('collectionViewType', types.Unicode(255), default=u'long'),
    schema.Column('inputOrthography', types.Unicode(255)),
    schema.Column('outputOrthography', types.Unicode(255)),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

speaker_table = schema.Table('speaker', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('speaker_seq_id', optional=True), primary_key=True),
    schema.Column('firstName', types.Unicode(255)),
    schema.Column('lastName', types.Unicode(255)),
    schema.Column('dialect', types.Unicode(255)),
    schema.Column('speakerPageContent', types.UnicodeText()),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

syntacticcategory_table = schema.Table('syntacticcategory', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('syntacticcategory_seq_id', optional=True),
        primary_key=True),
    schema.Column('name', types.Unicode(255)),
    schema.Column('description', types.UnicodeText()),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

keyword_table = schema.Table('keyword', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('keyword_seq_id', optional=True), primary_key=True),
    schema.Column('name', types.Unicode(255)),
    schema.Column('description', types.UnicodeText()),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

elicitationmethod_table = schema.Table('elicitationmethod', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('elicitationmethod_seq_id', optional=True),
        primary_key=True),
    schema.Column('name', types.Unicode(255)),
    schema.Column('description', types.UnicodeText()),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

source_table = schema.Table('source', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('source_seq_id', optional=True), primary_key=True),
    schema.Column('authorFirstName', types.Unicode(255)),
    schema.Column('authorLastName', types.Unicode(255)),
    schema.Column('title', types.Unicode(255)),
    schema.Column('year', types.Integer),
    schema.Column('fullReference', types.UnicodeText()),
    schema.Column('file_id', types.Integer, schema.ForeignKey('file.id')),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

# application_settings_table holds the info about the settings of the application
application_settings_table = schema.Table('application_settings', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('application_settings_seq_id', optional=True),
        primary_key=True
    ),
    
    schema.Column('objectLanguageName', types.Unicode(255)),
    schema.Column('objectLanguageId', types.Unicode(255)),

    schema.Column('metaLanguageName', types.Unicode(255)),
    schema.Column('metaLanguageId', types.Unicode(255)),
    schema.Column('metaLanguageOrthography', types.UnicodeText()),

    schema.Column('headerImageName', types.Unicode(255)),
    schema.Column('colorsCSS', types.Unicode(255)),

    schema.Column('storageOrthography', types.Unicode(255)),
    schema.Column('defaultInputOrthography', types.Unicode(255)),
    schema.Column('defaultOutputOrthography', types.Unicode(255)),

    schema.Column('objectLanguageOrthography1Name', types.Unicode(255)),
    schema.Column('objectLanguageOrthography1', types.UnicodeText()),
    schema.Column('OLO1Lowercase', types.Unicode(255)),
    schema.Column('OLO1InitialGlottalStops', types.Unicode(255)),
    
    schema.Column('objectLanguageOrthography2Name', types.Unicode(255)),
    schema.Column('objectLanguageOrthography2', types.UnicodeText()),
    schema.Column('OLO2Lowercase', types.Unicode(255)),
    schema.Column('OLO2InitialGlottalStops', types.Unicode(255)),

    schema.Column('objectLanguageOrthography3Name', types.Unicode(255)),
    schema.Column('objectLanguageOrthography3', types.UnicodeText()),
    schema.Column('OLO3Lowercase', types.Unicode(255)),
    schema.Column('OLO3InitialGlottalStops', types.Unicode(255)),

    schema.Column('objectLanguageOrthography4Name', types.Unicode(255)),
    schema.Column('objectLanguageOrthography4', types.UnicodeText()),
    schema.Column('OLO4Lowercase', types.Unicode(255)),
    schema.Column('OLO4InitialGlottalStops', types.Unicode(255)),

    schema.Column('objectLanguageOrthography5Name', types.Unicode(255)),
    schema.Column('objectLanguageOrthography5', types.UnicodeText()),
    schema.Column('OLO5Lowercase', types.Unicode(255)),
    schema.Column('OLO5InitialGlottalStops', types.Unicode(255)),

    schema.Column('morphemeBreakIsObjectLanguageString', types.Unicode(255)),
    schema.Column('datetimeModified', types.DateTime(), default=now),

    schema.Column('unrestrictedUsers', types.UnicodeText()),

    schema.Column('orthographicValidation', types.Unicode(8), default=u''),

    schema.Column('narrPhonInventory', types.UnicodeText(), default=u''),
    schema.Column('narrPhonValidation', types.Unicode(8), default=u''),

    schema.Column('broadPhonInventory', types.UnicodeText(), default=u''),
    schema.Column('broadPhonValidation', types.Unicode(8), default=u''),

    schema.Column('morphPhonInventory', types.UnicodeText(), default=u''),
    schema.Column('morphDelimiters', types.Unicode(255), default=u''),
    schema.Column('morphPhonValidation', types.Unicode(8), default=u''),

    schema.Column('punctuation', types.UnicodeText(), default=u''),
    schema.Column('grammaticalities', types.Unicode(255), default=u'')

)

# language_table holds ISO-639-3 data on the world's languages
#  - see http://www.sil.org/iso639-3/download.asp
#  - this table is populated from lib/languages/iso-639-3.tab
#    when "paster setup-app" is run
language_table = schema.Table('language', meta.metadata,
    schema.Column('Id', types.Unicode(3), primary_key=True),
    schema.Column('Part2B', types.Unicode(3)),
    schema.Column('Part2T', types.Unicode(3)),
    schema.Column('Part1', types.Unicode(2)),
    schema.Column('Scope', types.Unicode(1)),
    schema.Column('Type', types.Unicode(1)),
    schema.Column('Ref_Name', types.Unicode(150)),
    schema.Column('Comment', types.Unicode(150)),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

# page_table holds the text (markup) for user-generated pages 
page_table = schema.Table('page', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('page_seq_id', optional=True),
        primary_key=True
    ),
    schema.Column('name', types.Unicode(255)),
    schema.Column('content', types.UnicodeText()),
    schema.Column('heading', types.Unicode(255)),
    schema.Column('markup', types.Unicode(255)),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

# phonology_table holds the metadata for phonology FSTs
phonology_table = schema.Table('phonology', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('phonology_seq_id', optional=True),
        primary_key=True
    ),
    schema.Column('name', types.Unicode(255)),
    schema.Column('description', types.UnicodeText()),
    schema.Column('script', types.UnicodeText()),
    schema.Column('enterer_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('modifier_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('datetimeEntered', types.DateTime()),
    schema.Column('datetimeModified', types.DateTime(), default=now),
)

###################
# RELATIONAL TABLES
###################

"""formfile_table encodes the many-to-many relationship
between OLD Forms and OLD Files."""
formfile_table = schema.Table('formfile', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('formfile_seq_id', optional=True), primary_key=True),
    schema.Column('form_id', types.Integer, schema.ForeignKey('form.id')),
    schema.Column('file_id', types.Integer, schema.ForeignKey('file.id')),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

"""formkeyword_table encodes the many-to-many relationship
between OLD Forms and OLD Keywords."""
formkeyword_table = schema.Table('formkeyword', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('formfile_seq_id', optional=True), primary_key=True),
    schema.Column('form_id', types.Integer, schema.ForeignKey('form.id')),
    schema.Column('keyword_id', types.Integer, schema.ForeignKey('keyword.id')),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)


collectionform_table = schema.Table('collectionform', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('collectionform_seq_id', optional=True), primary_key=True),
    schema.Column('collection_id', types.Integer, schema.ForeignKey('collection.id')),
    schema.Column('form_id', types.Integer, schema.ForeignKey('form.id')),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

collectionfile_table = schema.Table('collectionfile', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('collectionfile_seq_id', optional=True), primary_key=True),
    schema.Column('collection_id', types.Integer, schema.ForeignKey('collection.id')),
    schema.Column('file_id', types.Integer, schema.ForeignKey('file.id')),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)

"""userform_table encodes the many-to-many relationship
between OLD Users and OLD Forms.  This is where the per-user
Memory is stored."""
userform_table = schema.Table('userform', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('formfile_seq_id', optional=True), primary_key=True),
    schema.Column('form_id', types.Integer, schema.ForeignKey('form.id')),
    schema.Column('user_id', types.Integer, schema.ForeignKey('user.id')),
    schema.Column('datetimeModified', types.DateTime(), default=now)
)



###############
# BACKUP TABLES
###############

# formbackup_table is used to save form_table data that has been updated
#  or deleted.  This is a non-relational table, because keeping a copy of 
#  every single change seemed more work than it's worth.
formbackup_table = schema.Table('formbackup', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('formbackup_seq_id', optional=True), primary_key=True),

    schema.Column('form_id', types.Integer),
    schema.Column('transcription', types.Unicode(255), nullable=False),
    schema.Column('phoneticTranscription', types.Unicode(255)),
    schema.Column('narrowPhoneticTranscription', types.Unicode(255)),
    schema.Column('morphemeBreak', types.Unicode(255)),
    schema.Column('morphemeGloss', types.Unicode(255)),
    schema.Column('comments', types.UnicodeText()),
    schema.Column('speakerComments', types.UnicodeText()), 

    # Forced choice textual values
    schema.Column('grammaticality', types.Unicode(255)),

    # Temporal values: only dateElicited is non-mediately user-generated
    schema.Column('dateElicited', types.Date()),
    schema.Column('datetimeEntered', types.DateTime()),
    schema.Column('datetimeModified', types.DateTime(), default=now),

    # syntacticCategoryString: OLD-generated value 
    schema.Column('syntacticCategoryString', types.Unicode(255)),

    # morphemeBreakIDs and morphemeGlossIDs: OLD-generated values
    schema.Column('morphemeBreakIDs', types.Unicode(1023)),
    schema.Column('morphemeGlossIDs', types.Unicode(1023)),

    # breakGlossCategory: OLD-generated value, e.g., 'chien|dog|N-s|PL|NUM'
    schema.Column('breakGlossCategory', types.Unicode(1023)),

    # Previously Many-to-One
    schema.Column('elicitor', types.Unicode(255)),
    schema.Column('enterer', types.Unicode(255)),
    schema.Column('verifier', types.Unicode(255)),
    schema.Column('speaker', types.Unicode(255)),
    schema.Column('elicitationMethod', types.Unicode(255)),
    schema.Column('syntacticCategory', types.Unicode(255)),
    schema.Column('source', types.UnicodeText()),

    # Previously One-to-Many
    schema.Column('glosses', types.UnicodeText()),
    
    # Previously Many-to-Many
    schema.Column('keywords', types.UnicodeText()),
    schema.Column('files', types.UnicodeText()), 

    schema.Column('backuper', types.Unicode(255))
)


# collectionbackup_table is used to save collection_table data that has been
#  updated or deleted.  Like formbackup_table, this table has no foreign keys.
collectionbackup_table = schema.Table('collectionbackup', meta.metadata,
    schema.Column('id', types.Integer,
        schema.Sequence('collectionbackup_seq_id', optional=True), primary_key=True),

    schema.Column('collection_id', types.Integer),
    schema.Column('title', types.Unicode(255)),
    schema.Column('type', types.Unicode(255)),
    schema.Column('url', types.Unicode(255)),
    schema.Column('description', types.UnicodeText()),
    schema.Column('contents', types.UnicodeText()),

    # Temporal values: only dateElicited is non-mediately user-generated
    schema.Column('dateElicited', types.Date()),
    schema.Column('datetimeEntered', types.DateTime()),
    schema.Column('datetimeModified', types.DateTime(), default=now),

    # Previously Many-to-One
    schema.Column('speaker', types.Unicode(255)),
    schema.Column('source', types.UnicodeText()),
    schema.Column('elicitor', types.Unicode(255)),
    schema.Column('enterer', types.Unicode(255)),

    schema.Column('backuper', types.Unicode(255)),
    schema.Column('files', types.UnicodeText())
)


#########
# CLASSES
#########

class Gloss(object):
    pass

class User(object):
    pass

class Speaker(object):
    pass

class ElicitationMethod(object):
    pass

class SyntacticCategory(object):
    pass

class Keyword(object):
    pass

class Source(object):
    pass

class ApplicationSettings(object):
    pass
    
class Language(object):
    pass

class Page(object):
    pass

class FormKeyword(object):
    pass

##########
# MAPPPERS
##########
  
orm.mapper(Form, form_table, properties={
    'speaker': orm.relation(Speaker),
    'elicitationMethod': orm.relation(ElicitationMethod),
    'syntacticCategory': orm.relation(SyntacticCategory),
    'elicitor': orm.relation(User, primaryjoin=(form_table.c.elicitor_id==user_table.c.id)),
    'enterer': orm.relation(User, primaryjoin=(form_table.c.enterer_id==user_table.c.id)),
    'verifier': orm.relation(User, primaryjoin=(form_table.c.verifier_id==user_table.c.id)),
    'source': orm.relation(Source),
    'glosses': orm.relation(Gloss, backref='form', cascade="all, delete, delete-orphan"),
    'files': orm.relation(File, secondary=formfile_table, backref='forms'),
    'collections': orm.relation(Collection, secondary=collectionform_table),
    'keywords': orm.relation(Keyword, secondary=formkeyword_table, backref='forms')
})
  
orm.mapper(Collection, collection_table, properties={
    'enterer': orm.relation(User, primaryjoin=(collection_table.c.enterer_id==user_table.c.id)),
    'elicitor': orm.relation(User, primaryjoin=(collection_table.c.elicitor_id==user_table.c.id)),
    'speaker': orm.relation(Speaker),
    'source': orm.relation(Source),
    'files':orm.relation(File, secondary=collectionfile_table),
    'forms':orm.relation(Form, secondary=collectionform_table)
})

orm.mapper(Gloss, gloss_table)

orm.mapper(File, file_table, properties={
    'enterer': orm.relation(User, primaryjoin=(file_table.c.enterer_id==user_table.c.id)),
    'elicitor': orm.relation(User, primaryjoin=(file_table.c.elicitor_id==user_table.c.id)),
    'speaker': orm.relation(Speaker)
})

orm.mapper(User, user_table, properties={
    'rememberedForms': orm.relation(Form, secondary=userform_table, backref='memorizers'),
})

orm.mapper(Speaker, speaker_table)

orm.mapper(SyntacticCategory, syntacticcategory_table)

orm.mapper(Keyword, keyword_table)

orm.mapper(ElicitationMethod, elicitationmethod_table)

orm.mapper(Source, source_table, properties={
    'file': orm.relation(File)
})

orm.mapper(FormBackup, formbackup_table)

orm.mapper(CollectionBackup, collectionbackup_table)

orm.mapper(ApplicationSettings, application_settings_table)

orm.mapper(Language, language_table)

orm.mapper(Page, page_table)

orm.mapper(FormKeyword, formkeyword_table)

orm.mapper(Phonology, phonology_table, properties={
    'enterer': orm.relation(
        User, primaryjoin=(phonology_table.c.enterer_id==user_table.c.id)),
    'modifier': orm.relation(
        User, primaryjoin=(phonology_table.c.modifier_id==user_table.c.id))
})