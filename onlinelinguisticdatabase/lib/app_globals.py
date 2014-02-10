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

"""The application's Globals object"""

import string

from pylons import session
from orthography import Orthography

class Globals(object):

    """Globals acts as a container for objects available throughout the
    life of the application

    """

    def __init__(self):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """

        # Options for searchTypes: these are used by the queryBuilder module.
        self.searchTypes = [
            'as a phrase', 
            'all of these', 
            'any of these', 
            'as a reg exp', 
            'exactly'
        ]

        # Options for dropdown menu between search expressions 1 and 2
        self.andOrNot = [
            ('and_', 'and'),
            ('or_', 'or'),
            ('not_', 'and not')
        ]

        # Search Locations - columns that can be searched in search expressions
        self.searchLocations = {
            'form': [
                ('transcription', 'orthographic transcription'),
                ('phoneticTranscription', 'broad phonetic transcription'),
                ('narrowPhoneticTranscription', 'narrow phonetic transcription'),
                ('gloss', 'gloss'),
                ('morphemeBreak', 'morpheme break'),
                ('morphemeGloss', 'morpheme gloss'),
                ('comments', 'general comments'),
                ('speakerComments', 'speaker comments'),
                ('syntacticCategoryString', 'syntactic category string'),
                ('id', 'ID')
            ],
            'file': [
                ('name', 'name'),
                ('description', 'description'),
                ('id', 'ID')
            ],
            'collection': [
                ('title', 'title'),
                ('type', 'type'),
                ('description', 'description'),
                ('contents', 'contents'),
                ('id', 'ID')
            ]
        }

        # Search Integer Filter Locations - columns that can be searched in
        #  integer filters
        self.searchIntegerFilterLocations = {
            'form': [
                ('id', 'ID')
            ],
            'file': [
                ('id', 'ID'),
                ('size', 'size')
            ],
            'collection': [
                ('id', 'ID')
            ]
        }


        # Grammaticalities: possible values in grammaticality and
        #  glossGrammaticality fields
        self.grammaticalities = [u'', u'*', u'?', u'#']


        # Export Options: correspond to defs in /templates/base/exporter.html
        self.exportOptions = [
            ('t', ' Plain text: transcription only'),
            ('t_g', ' Plain text: transcription & gloss'),
            ('t_mb_mg_g', """ Plain text: transcription, morpheme break,
                morpheme gloss & gloss"""),
            ('all', ' Plain text: all fields')
        ]

        # Number of Forms to display per page 
        self.form_items_per_page = 10

        # Number of Files to display per page 
        self.file_items_per_page = 10

        # Number of Collections to display per page 
        self.collection_items_per_page = 100

        # Number of previous (Form) searches that are remembered in the session
        self.maxNoPreviousSearches = 10

        # The roles that users of the OLD may have
        self.roles = ['administrator', 'contributor', 'viewer']

        # The ways in which the content of a Collection (Forms and textual
        #  commentary) can be displayed 
        self.collectionViewTypes = ['long', 'short', 'columns']

        # The MIME types of the Files that can be uploaded to the OLD
        #  Values are user-friendly names of the file types.
        #  Empty values indicate that key.split('/')[0] should be used.
        #  See http://en.wikipedia.org/wiki/Internet_media_type
        self.allowedFileTypes = {
            u'text/plain': u'plain text',
            u'application/x-latex': u'LaTeX document', 
            u'application/msword': u'MS Word document',
            u'application/vnd.ms-powerpoint': u'MS PowerPoint document',
            u'application/vnd.openxmlformats-officedocument.wordprocessingml.document': u'Open Document Format (.odt)',
            u'application/vnd.oasis.opendocument.text': u'Office Open XML (.docx)',
            u'application/pdf': u'PDF',
            u'image/gif': u'',
            u'image/jpeg': u'',
            u'image/png': u'',
            u'audio/mpeg': u'',
            u'audio/ogg': u'',
            u'audio/x-wav': u'',
            u'video/mpeg': u'',
            u'video/mp4': u'',
            u'video/ogg': u'',
            u'video/quicktime': u'',
            u'video/x-ms-wmv': u''
        }
            
        # Valid morpheme delimiters, i.e., characters that can occur between morphemes
        self.morphDelimiters = ['-', '=']

        # Valid punctuation.
        self.punctuation = list(u""".,;:!?'"\u2018\u2019\u201C\u201D[]{}()-""")


        # Collection types are the basic categories of Collections
        self.collectionTypes = [u'story', u'elicitation', u'paper',
                                u'discourse', u'other']
        self.collectionTypesPlurals = {
            u'elicitation': u'elicitations',
            u'story': u'stories',
            u'paper': u'papers',
            u'discourse': u'discourses',
            u'other': u'other'
        }

        # Collection view types: long, short or column
        self.collectionViewTypes = ['long', 'short', 'columns']

        self.topPrimaryMenuItems = [
            {
                'id': 'database',
                'name': 'Database', 
                'url': '/home', 
                'accesskey': 'h',
                'title': 'Database mode'
            },
            {
                'id': 'dictionary',
                'name': 'Dictionary', 
                'url': '/dictionary/browse', 
                'accesskey': 'd',
                'title': 'Dictionary mode'
            },
            {
                'id': 'help',
                'name': 'Help', 
                'url': '/help',
                'title': 'Help with using the OLD'
            },
            {
                'id': 'settings',
                'name': 'Settings',
                'url': '/settings',
                'title': 'View and edit system-wide settings'
            }
        ]
                    
        self.topSecondaryMenuItemChoices = {
            'database': [
                {
                    'id': 'people',
                    'name': 'People', 
                    'url': '/people', 
                    'accesskey': 'p',
                    'title': 'Info about Speakers and Researchers'
                },
                {
                    'id': 'tag',
                    'name': 'Tags', 
                    'url': '/tag', 
                    'title': 'Keywords, Categories and Elicitation Methods',
                    'accesskey':'t'
                },
                {
                    'id': 'source',            
                    'name': 'Sources',
                    'url': '/source',
                    'title': 'Info about Sources'
                },
                {
                    'id': 'memory',            
                    'name': 'Memory', 
                    'url': '/memory', 
                    'accesskey': 'm',
                    'title': 'Forms that you are currently interested in'
                }
            ],
            'dictionary': [
                {
                    'id': 'dictionarybrowse',
                    'name': 'Browse', 
                    'url': '/dictionary/browse', 
                    'title': 'Browse the dictionary'
                },
                {
                    'id': 'dictionarysearch',
                    'name': 'Search', 
                    'url':' /dictionary/search', 
                    'title':'Search the dictionary'
                }
            ],
            'help': [
                {
                    'id': 'helpolduserguide',
                    'name': 'OLD User Guide',
                    'url': '/help/olduserguide',
                    'title': 'View the OLD user guide'
                },
                {
                    'id': 'helpapplicationhelp',
                    'name': 'Help Page',
                    'url': '/help/applicationhelp',
                    'title': "View this OLD application's help page"
                }
            ]
        }
          
        self.sideMenuItems = {
            'form': [
                {
                    'id': 'formadd',
                    'name': 'Add', 
                    'url': '/form/add', 
                    'accesskey': 'a',
                    'title': 'Add a Form'
                },
                {
                    'id': 'formsearch',
                    'name': 'Search', 
                    'url': '/form/search', 
                    'accesskey': 's',
                    'title': 'Search for Forms'
                }
            ],
            'file': [
                {
                    'id': 'fileadd',
                    'name': 'Add', 
                    'url': '/file/add',
                    'accesskey': 'q',
                    'title': 'Create a new File'
                },
                {
                    'id': 'filesearch',            
                    'name': 'Search', 
                    'url': '/file/search',
                    'accesskey': 'w',
                    'title': 'Search for Files'
                }
            ],
            'collection': [    
                {
                    'id': 'collectionadd',
                    'name': 'Add', 
                    'url': '/collection/add',
                    'accesskey': 'z',                
                    'title': 'Add a new Collection'
                },
                {
                    'id': 'collectionsearch',
                    'name': 'Search', 
                    'url': '/collection/search',
                    'accesskey': 'x',
                    'title': 'Search for Collections'
                }
            ]
        }
        
        # MUTABLE APP GLOBALS
        #  these attributes are set with defaults at initialization but
        #  may be changed over the lifespan of the application

        # APPLICATION SETTINGS
        #  name of the object language, metalanguage, etc.
        defaultOrthography = ','.join(list(string.ascii_lowercase))
        self.objectLanguageName = u'Anonymous'
        self.objectLanguageId = u''
        self.metaLanguageName = u'Unknown'
        self.headerImageName = u''
        self.colorsCSS = 'green.css'
        self.morphemeBreakIsObjectLanguageString = u'no'
        self.metaLanguageOrthography = Orthography(defaultOrthography)
        self.OLOrthographies = {
            u'Orthography 1': (
                u'Unnamed',
                Orthography(
                    defaultOrthography, lowercase=1, initialGlottalStops=1
                )
            )
        }
        self.storageOrthography = self.OLOrthographies[
            u'Orthography 1']
        self.defaultInputOrthography = self.OLOrthographies[
            u'Orthography 1']
        self.defaultOutputOrthography = self.OLOrthographies[
            u'Orthography 1']
        self.inputToStorageTranslator = None
        self.storageToInputTranslator = None
        self.storageToOutputTranslator = None
        
        # formCount is the number of Forms in the OLD application.
        #  This variable is updated on the deletion and addition of Forms.
        #  THIS IS PROBABLY NOT A GOOD IDEA BECAUSE OF MULTI-THREADING.
        #  JUST DO A SQLALCHEMY COUNT(ID) QUERY!
        self.formCount = None

        # Secondary Object Lists
        #  These variables are set by the function
        #  updateSecondaryObjectsInAppGlobals() in lib/functions.py
        self.speakers = []
        self.users = []
        self.nonAdministrators = []
        self.unrestrictedUsers = []
        self.sources = []
        self.syncats = []
        self.keywords = []
        self.elicitationMethods = []

        
    def getActiveTopPrimaryMenuItem(self, url):
        """Given the url of the current page, return the appropriate active top
        primary menu item.  
        """
        result = ''
        controller = url.split('/')[1]
        controllerToPrimaryMenuItem = {
            'form': 'database',
            'file': 'database',
            'collection': 'database',
            'people': 'database',
            'tag': 'database',
            'source': 'database',
            'memory': 'database',
            'speaker': 'database',
            'researcher': 'database',
            'key': 'database',
            'category': 'database',
            'method': 'database',
            'home': 'database',
            'settings': 'settings',
            'dictionary': 'dictionary',
            'help': 'help'
        }
        try: 
            result = controllerToPrimaryMenuItem[controller]
        except KeyError:
            pass
        return result
    
    def getMenuItemsTurnedOnByController(self, url):
        """Certain controllers need to make certain menu items active; encode
        that here.
        """
        result = []
        controller = url.split('/')[1]
        controllerXTurnsOn = {
            'speaker': ['people'],
            'researcher': ['people'],
            'key': ['tag'],
            'category': ['tag'],
            'method': ['tag']
        }
        try:
            result = controllerXTurnsOn[controller]
        except KeyError:
            pass
        return result
    
    def getActiveMenuItems(self, url):
        """ Function returns the ID of each menu item that should be active
        given a particular URL.
        
        Partially logical, partially ad hoc specification.
        """
        activeMenuItems = [] 
        
        controller = url.split('/')[1]
        controllerAction = ''.join(url.split('/')[1:3])
        
        activeMenuItems.append(self.getActiveTopPrimaryMenuItem(url))
        activeMenuItems += self.getMenuItemsTurnedOnByController(url)
        activeMenuItems.append(controllerAction)
        activeMenuItems.append(controller)

        return activeMenuItems
    
    def authorizedMenuItem(self, menuItem):
        """Return True if menu item should be viewable by current user;
        else False.
        """
        if 'authorizationLevel' not in menuItem or (
            'user_role' in session and session['user_role'] in menuItem[
            'authorizationLevel']
        ) :
            return True
        else:
            return False    
                
                
    def getTopSecondaryMenuItems(self, url):
        """The menu items in the top secondary tier are determined by the active
        menu item in the top primary tier.  Return an empty list if the top
        secondary tier should be omitted. 
        """
        activeTopPrimaryMenuItem = self.getActiveTopPrimaryMenuItem(url)
        topSecondaryMenuItems = []
    
        try:
            temp = self.topSecondaryMenuItemChoices[activeTopPrimaryMenuItem]
            topSecondaryMenuItems = [x for x in temp
                                     if self.authorizedMenuItem(x)]
        except KeyError:
            pass
        return topSecondaryMenuItems
    
    
    def getTopPrimaryMenuItems(self):
        """Return top priamry menu items for which the current user is
        authorized.
        """
        return [x for x in self.topPrimaryMenuItems
                if self.authorizedMenuItem(x)]
