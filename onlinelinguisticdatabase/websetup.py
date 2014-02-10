# −*− coding: UTF−8 −*−
"""Setup the onlinelinguisticdatabase application"""
import logging
import hashlib
import codecs
import string
import datetime
import os

from pylons import config

from onlinelinguisticdatabase.config.environment import load_environment
from onlinelinguisticdatabase.model import meta
from onlinelinguisticdatabase import model
import onlinelinguisticdatabase.lib.helpers as h
import onlinelinguisticdatabase.lib.languages.iso_639_3 as iso_639_3

log = logging.getLogger(__name__)

def setup_app(command, conf, vars):
    """Place any commands to setup onlinelinguisticdatabase here"""
    load_environment(conf.global_conf, conf.local_conf)

    log.debug('environment loaded')
    
    # Create the tables if they don't already exist
    meta.metadata.create_all(bind=meta.engine)

    log.debug('tables created')

    # Create the files directory and the archived_files and researchers
    #  subdirectories
    try:
        os.mkdir('files')
    except OSError:
        pass
    
    try:
        os.mkdir(os.path.join('files', 'archived_files'))
    except OSError:
        pass

    try:
        os.mkdir(os.path.join('files', 'researchers'))
    except OSError:
        pass

    # Create the analysis directory and its phonology, morphotactics,
    #  morphophonology, probabilitycalculator subdirectories
    try:
        os.mkdir('analysis')
    except OSError:
        pass
    try:
        os.mkdir(os.path.join('analysis', 'phonology'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join('analysis', 'morphotactics'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join('analysis', 'morphophonology'))
    except OSError:
        pass
    try:
        os.mkdir(os.path.join('analysis', 'probabilitycalculator'))
    except OSError:
        pass

    # Add an administrator and some general language data

    # Administrator
    log.info("Creating a default administrator.")
    admin = model.User()
    admin.firstName = u'Admin'
    admin.lastName = u'Admin'
    admin.username = u'admin'
    admin.email = u'admin@example.com'
    admin.password = unicode(hashlib.sha224(u'admin').hexdigest())
    admin.role = {'0': u'administrator', '1': u'mirror'}[config['mirror']]
    admin.collectionViewType = u'long'
    admin.inputOrthography = None
    admin.outputOrthography = None
    admin.personalPageContent = u''
    h.createResearcherDirectory(admin)
    
    # Contributor
    log.info("Creating a default contributor.")
    contributor = model.User()
    contributor.firstName = u'Contributor'
    contributor.lastName = u'Contributor'
    contributor.username = u'contributor'
    contributor.email = u'contributor@example.com'
    contributor.password = unicode(hashlib.sha224(u'contributor').hexdigest())
    contributor.role = u'contributor'
    contributor.collectionViewType = u'long'
    contributor.inputOrthography = None
    contributor.outputOrthography = None
    contributor.personalPageContent = u''
    h.createResearcherDirectory(contributor)

    # Viewer
    log.info("Creating a default viewer.")
    viewer = model.User()
    viewer.firstName = u'Viewer'
    viewer.lastName = u'Viewer'
    viewer.username = u'viewer'
    viewer.email = u'viewer@example.com'
    viewer.password = unicode(hashlib.sha224(u'viewer').hexdigest())
    viewer.role = u'viewer'
    viewer.collectionViewType = u'long'
    viewer.inputOrthography = None
    viewer.outputOrthography = None
    viewer.personalPageContent = u''
    h.createResearcherDirectory(viewer)
    
    # Default Home Page
    homepage = model.Page()
    homepage.name = u'home'
    homepage.heading = u'Welcome to the OLD'
    homepage.content = u"""
The Online Linguistic Database is a web application that helps people to
document, study and learn a language.
        """
    homepage.markup = u'restructuredtext'

    # Default Help Page
    helppage = model.Page()
    helppage.name = u'help'
    helppage.heading = u'OLD Application Help'
    helppage.content = u"""
Welcome to the help page of this OLD application.

This page should contain content entered by your administrator.
        """
    helppage.markup = u'restructuredtext'

    # Enter ISO-639-3 Language data into the languages table
    log.info("Retrieving ISO-639-3 languages data.")
    languages = [getLanguageObject(language) for language in iso_639_3.languages]

    # Default Application Settings
    log.info("Generating default settings.")
    orthography = u', '.join(list(string.ascii_lowercase))
    applicationSettings = model.ApplicationSettings()
    applicationSettings.objectLanguageName = u'Anonymous'
    applicationSettings.storageOrthography = u'Orthography 1'
    applicationSettings.defaultInputOrthography = u'Orthography 1'
    applicationSettings.defaultOutputOrthography = u'Orthography 1'
    applicationSettings.objectLanguageOrthography1 = orthography
    applicationSettings.objectLanguageOrthography1Name = u'English alphabet'
    applicationSettings.metaLanguageName = u'Unknown'
    applicationSettings.metaLanguageOrthography = orthography
    applicationSettings.headerImageName = u''
    applicationSettings.colorsCSS = u'green.css'
    applicationSettings.OLO1Lowercase = u'1'
    applicationSettings.OLO1InitialGlottalStops = u'1'
    applicationSettings.OLO2Lowercase = u'1'
    applicationSettings.OLO2InitialGlottalStops = u'1'
    applicationSettings.OLO3Lowercase = u'1'
    applicationSettings.OLO3InitialGlottalStops = u'1'
    applicationSettings.OLO4Lowercase = u'1'
    applicationSettings.OLO4InitialGlottalStops = u'1'
    applicationSettings.OLO5Lowercase = u'1'
    applicationSettings.OLO5InitialGlottalStops = u'1'
    applicationSettings.morphemeBreakIsObjectLanguageString = u'no'
    applicationSettings.unrestrictedUsers = u'[]'
    applicationSettings.orthographicValidation = u'None'
    applicationSettings.narrPhonValidation = u'None'
    applicationSettings.broadPhonValidation = u'None'
    applicationSettings.morphPhonValidation = u'None'
    applicationSettings.morphDelimiters = u'-,='
    applicationSettings.punctuation = u""".,;:!?'"\u2018\u2019\u201C\u201D[]{}()-"""
    applicationSettings.grammaticalities = u'*,#,?'
    applicationSettings.narrPhonInventory = u''
    applicationSettings.broadPhonInventory = u''
    applicationSettings.morphPhonInventory = u''

    # Default Keywords
    restrictedKW = model.Keyword()
    restrictedKW.name = u'restricted'
    restrictedKW.description = u'''Forms tagged with the keyword 'restricted'
can only be viewed by administrators, unrestricted users and the users they were
entered by.'''

    foreignWordKW = model.Keyword()
    foreignWordKW.name = u'foreign word'
    foreignWordKW.description = u'''Use this tag for lexical entries that are
not from the object language. For example, it might be desirable to create a
form as lexical entry for a proper noun like "John".  Such a form should be
tagged as a "foreign word". This will allow forms containing "John" to have
gapless syntactic category string values. Additionally, the system ignores
foreign word transcriptions when validating user input against orthographic,
phonetic and phonemic inventories.'''


    # Initialize the database
    log.info("Adding defaults.")

    data = [admin, contributor, viewer, homepage, helppage, applicationSettings,
            restrictedKW, foreignWordKW]

    if config['addLanguageData'] != '0':
        data += languages

    if config['emptyDatabase'] == '0':
        meta.Session.add_all(data)
        meta.Session.commit()
        

    log.info("OLD successfully set up.")

def getLanguageObject(languageList):
    language = model.Language()
    language.Id = languageList[0]
    language.Part2B = languageList[1]
    language.Part2T = languageList[2]
    language.Part1 = languageList[3]     
    language.Scope = languageList[4]
    language.Type = languageList[5]
    language.Ref_Name = languageList[6]
    language.Comment = languageList[7]     
    return language