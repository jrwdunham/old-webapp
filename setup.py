try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='onlinelinguisticdatabase',
    version='0.2.9',
    description='''Software for creating web applications for collaborative
    linguistic fieldwork.''',
    author='Joel Dunham',
    author_email='jrwdunham@gmail.com',
    url='http://www.onlinelinguisticdatabase.org',
    long_description="""
================================================================================
OnlineLinguisticDatabase
================================================================================

The Online Linguistic Database (OLD) is software for creating web applications
dedicated to multi-user, collaborative documention of natural (and usually
endangered or understudied) languages. An OLD web application helps contributors
to create a consistent, structured, and highly searchable web-based repository
of language data. These data consist of textual representations of linguistic
examples (words, morphemes, and sentences with analyses and annotations),
associated and embedded media files, and exportable representations of texts
(e.g., research papers, narratives, etc.)

See a demo OLD application at
`www.onlinelinguisticdatabase.org <http://www.onlinelinguisticdatabase.org>`_.


Features
--------------------------------------------------------------------------------

#. Multi-user, concurrent read/write access to a server-side language database.
#. Interlinear glossed text (IGT) representations of data with integrated
   feedback on lexical consistency or morphological analyses.
#. Powerful searches over the data set.
#. Authentication and authorization to control access to data.
#. Export to LaTeX, CSV, and plain text.
#. Media file support: many-to-many associations of audio, video, and/or image
   with content embedded in data representations.
#. IGT text creation.
#. Automatic orthography conversion.
#. Inventory-based transcription input validation.


Versions
--------------------------------------------------------------------------------

Note that there are currently two distinct versions of the OLD: 0.2.X and 1.0.

Version 0.2.X is a standard Pylons web application. Its source can be found on
GitHub at https://github.com/jrwdunham/old-webapp.

Version 1.0. includes functionality for creating morphological parsers,
provides improved search functionality, and implements a shift to a more
modular and reusable architecture (i.e., a RESTful HTTP/JSON web service with a
SPA GUI). However, there is currently no GUI for the OLD 1.0. Its source can be
found on GitHub at https://github.com/jrwdunham/old.

While version 0.2.X is still being maintained, primary development has moved to
version 1.0.


Get, Install & Serve
--------------------------------------------------------------------------------

When installing the OLD 0.2.X, it is recommended that you use an isolated Python
environment using
`virtualenv <http://www.virtualenv.org/en/latest/virtualenv.html>`_.
(Note that the OLD 0.2.X has been tested with Python 2.5 and 2.6, but not 2.7.
Depending on your system Python version, it may be necessary to install Python
2.5 or 2.6 using `pyenv <https://github.com/yyuu/pyenv>`_ or
`pythonbrew <https://github.com/utahta/pythonbrew>`_.) Once ``virtualenv`` is
installed, issue the following commands to create the isolated environment and
to make sure you are using its Python::

    virtualenv env
    source env/bin/activate

To install with ``easy_install``::

    easy_install "OnlineLinguisticDatabase==0.2.9"

With ``Pip``::

    pip install "OnlineLinguisticDatabase==0.2.9"

To create the config file, generate the default values, and serve the application::

    mkdir my_old_webapp
    cd my_old_webapp
    paster make-config onlinelinguisticdatabase production.ini
    paster setup-app production.ini
    paster serve production.ini


Using MySQL
--------------------------------------------------------------------------------

The default configuration (``.ini``) file  uses a local SQLite database, which
is probably fine for exploring the system initially. However, a deployed OLD
0.2.X application should use MySQL.

First login to MySQL using your root account and create a MySQL database and a
user with sufficient privileges.  Something like this (replacing ``dbname``,
``username``, and ``password`` with sensible values)::

    mysql> create database dbname default character set utf8;
    mysql> create user 'username'@'localhost' identified by 'password';
    mysql> grant select, insert, update, delete, create, drop on dbname.* to 'username'@'localhost';
    mysql> quit;

Then comment out the SQLite option in the OLD 0.2.X configuration file (e.g.,
``production.ini``) and uncomment the two MySQL lines, changing values as
appropriate::

    sqlalchemy.url = mysql://username:password@localhost:3306/dbname
    sqlalchemy.pool_recycle = 3600

Now the system is set up to use MySQL. Run the ``setup-app`` command again to
generate the default values in the MySQL db::

    paster setup-app production.ini

See `The Pylons Book <http://pylonsbook.com/>`_ for further details on serving
and configuring Pylons-based web applications.


Default Users
--------------------------------------------------------------------------------

Running ``paster setup-app`` creates three users with the following usernames
and passwords.

- username: ``admin``, password: ``admin``
- username: ``contributor``, password: ``contributor``
- username: ``viewer``, password: ``viewer``

Use the admin account to create a new administrator-level user and delete all
of the default users before deploying an OLD application.


Common Issues
--------------------------------------------------------------------------------

Note that if you are running Debian or Ubuntu and get an error like
``EnvironmentError: mysql_config not found`` after running
``python setup.py develop``, then you probably need to install
``libmysqlclient-dev``::

    sudo apt-get install libmysqlclient-dev

If you get an error page when using the browser-based interface, re-saving the
system settings should solve it. I.e., go to Settings > System Settings > Edit
System Settings and click the "Save Changes" button.


Files
--------""",
    install_requires=[
	"Beaker==1.5.3",
	"docutils==0.7",
	"FormEncode==1.2.2",
	"Mako==0.4.0",
	"MarkupSafe==0.12",
	"MySQL_python==1.2.3",
	"Paste==1.7.2",
	"PasteDeploy==1.3.3",
	"PasteScript==1.7.3",
	"Pygments==1.3.1",
	"Pylons==0.9.7",
	"PyYAML==3.10",
	"Routes==1.10.3",
	"simplejson==2.0.9",
	"SQLAlchemy==0.5.8",
	"Tempita==0.4",
	"WebError==0.10.2",
	"WebHelpers==0.6.4",
	"WebOb==0.9.8",
	"WebTest==1.2"

    ],
    setup_requires=["PasteScript>=1.6.3"],
    packages=find_packages(exclude=['ez_setup']),
    include_package_data=True,
    test_suite='nose.collector',
    package_data={'onlinelinguisticdatabase': ['i18n/*/LC_MESSAGES/*.mo']},
    #message_extractors={'onlinelinguisticdatabase': [
    #        ('**.py', 'python', None),
    #        ('templates/**.mako', 'mako', {'input_encoding': 'utf-8'}),
    #        ('public/**', 'ignore', None)]},
    zip_safe=False,
    paster_plugins=['PasteScript', 'Pylons'],
    entry_points="""
    [paste.app_factory]
    main = onlinelinguisticdatabase.config.middleware:make_app

    [paste.app_install]
    main = pylons.util:PylonsInstaller
    """
)
