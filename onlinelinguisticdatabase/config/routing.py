"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False

    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE

    map.connect('export_create', '/export/create/{input}/{option}', controller='export', action='create')
    map.connect('retrieve', '/file/retrieve/*path', controller='file', action='retrieve') 
    map.connect('gettree', '/form/gettree/*id', controller='form', action='gettree') 
    map.connect('retrieve_temp', '/file/retrieve_temp/{path}', controller='file', action='retrieve_temp')
    map.connect('disassociate', '/disassociate/{controller}/{id}/file/{otherID}', action='disassociate') 
    map.connect('/{controller}/{action}')
    map.connect('/{controller}/{action}/{id}')
    # Added a right brace to option in the following connect object...
    map.connect('/{controller}/{action}/{id}/{option}')
    map.connect('/{controller}', action='index')
    map.connect('keyword', controller='key')
    map.connect('/', controller='home', action='index')
    map.connect('/*URL', controller='collection', action='redirectfromurl')
    return map
