"""Pylons environment configuration"""
import os
import re

from mako.lookup import TemplateLookup
from pylons import config
from pylons.error import handle_mako_error
from sqlalchemy import engine_from_config
from sqlalchemy.interfaces import PoolListener

import onlinelinguisticdatabase.lib.app_globals as app_globals
import onlinelinguisticdatabase.lib.helpers
from onlinelinguisticdatabase.config.routing import make_map
from onlinelinguisticdatabase.model import init_model

from onlinelinguisticdatabase.lib.functions import applicationSettingsToAppGlobals, updateSecondaryObjectsInAppGlobals

def load_environment(global_conf, app_conf):
    """Configure the Pylons environment via the ``pylons.config`` object

    """

    # Pylons paths
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = dict(root=root,
                 controllers=os.path.join(root, 'controllers'),
                 static_files=os.path.join(root, 'public'),
                 templates=[os.path.join(root, 'templates')])

    # Initialize config with the basic options
    config.init_app(
        global_conf, app_conf, package='onlinelinguisticdatabase', paths=paths
    )

    config['routes.map'] = make_map()
    config['pylons.app_globals'] = app_globals.Globals()
    config['pylons.h'] = onlinelinguisticdatabase.lib.helpers

    # Create the Mako TemplateLookup, with the default auto-escaping
    config['pylons.app_globals'].mako_lookup = TemplateLookup(
        directories=paths['templates'],
        error_handler=handle_mako_error,
        module_directory=os.path.join(app_conf['cache_dir'], 'templates'),
        input_encoding='utf-8', default_filters=['escape'],
        imports=['from webhelpers.html import escape'])

    # Setup the SQLAlchemy database engine
    #  Modification: check if SQLite is RDBMS and, if so,
    #  give the engine a SQLiteSetup listener which
    #  provides the regexp function missing from the SQLite dbapi
    #  (cf. http://groups.google.com/group/pylons-discuss/browse_thread/thread/8c82699e6b6a400c/5c5237c86202e2b8)
    SQLAlchemyURL = config['sqlalchemy.url']
    rdbms = SQLAlchemyURL.split(':')[0]
    if rdbms == 'sqlite':
        engine = engine_from_config(
            config, 'sqlalchemy.', listeners=[SQLiteSetup()])
    else:
        engine = engine_from_config(config, 'sqlalchemy.')
    init_model(engine)

    # Put the application settings into the app_globals object
    #  This has the effect that when the app is restarted the globals like
    #  objectLanguageName, metalanguageName, etc. have the correct values
    #  Do the same for the variable app_globals attributes, e.g., sources list
    #  I HAD TO DISABLE THE FOLLOWING TWO COMMANDS BECAUSE IT WAS CAUSING
    #  setup-app TO CRASH BECAUSE application_settings WAS REQUESTED BEFORE THE
    #  TABLES EXISTED!  FIND ANOTHER WAY TO FIX THIS PROBLEM ...
    #applicationSettingsToAppGlobals(config['pylons.app_globals'])
    #updateSecondaryObjectsInAppGlobals(config['pylons.app_globals'])

    # CONFIGURATION OPTIONS HERE (note: all config options will override
    # any Pylons config options)
    config['pylons.strict_c'] = True

    # Unicode Patch TEST
    #  from "http://groups.google.com/group/pylons-discuss/browse_thread/thread/3bf6764beacaaaf3/162daf2fb028683e?lnk=gst&q=unicode#162daf2fb028683e"
    #tmpl_options = config['buffet.template_options'] 
    #tmpl_options['mako.input_encoding'] = 'utf-8' 
    #tmpl_options['mako.output_encoding'] = 'utf-8' 
    #tmpl_options['mako.default_filters'] = ['decode.utf8']


class SQLiteSetup(PoolListener):
    """A PoolListener used to provide the SQLite dbapi with a regexp function.
    """
    def connect(self, conn, conn_record):
        conn.create_function('regexp', 2, self.regexp)

    def regexp(self, expr, item):
        patt = re.compile(expr)
        return item and patt.match(item) is not None
