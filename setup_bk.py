# The only difference between this file and setup.py is that this file has
# very general dependency requirements whereas that one attempts to be 
# very specific about which modules are needed. I.e., compare the
# install_requires values.

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='onlinelinguisticdatabase',
    version='0.2.7',
    description='''A web application for structuring, processing and sharing
    linguistic fieldwork data.''',
    author='Joel Dunham',
    author_email='jrwdunham@gmail.com',
    url='http://www.onlinelinguisticdatabase.org',
    long_description="""
++++++++++++++++++++++++
OnlineLinguisticDatabase
++++++++++++++++++++++++

A web application for structuring, processing and sharing linguistic fieldwork
data.  The app is multi-user with authorization and authentication
functionality.  The intent is that groups of researchers studying a common
language will download the Online Linguistic Database (OLD), install it on their
own server and use it to create an online repository of linguistic data for
their language of study.  

Installation
============

First install Easy Install if you don't have it already by downloading
``ez_setup.py`` from http://peak.telecommunity.com/dist/ez_setup.py and
installing it like this::

    python ez_setup.py

Now install OnlineLinguisticDatabase like this::

    easy_install OnlineLinguisticDatabase
    paster make-config "OnlineLinguisticDatabase==0.2.4" production.ini

Configure the application by editing the ``production.ini`` config file just
created.

Alter database defaults using the format described at
http://www.sqlalchemy.org/docs/05/dbengine.html#dbengine_supported.

The default RDBMS is MySQL.  With no alterations to production.ini, the system
will expect a MySQL database named 'old' and a user (username: 'old', password:
'old') who has full permissions on the 'old' database.  If this database and
user do not exist, the default OLD set up will fail.  Best bet is to change the
production.ini file to suite your own (secure) MySQL configuration.

To use a SQLite database, comment out the MySQL option and uncomment the SQLite
option::

    # MySQL OPTION
    #sqlalchemy.url = mysql://old:old@localhost:3306/old
    #sqlalchemy.pool_recycle = 3600
    # SQLite OPTION
    sqlalchemy.url = sqlite:///%(here)s/old.db

This will create a SQLite database file called 'old.db' in the same directory as
your production.ini file.

Set up the OLD application and serve it::

    paster setup-app production.ini
    paster serve production.ini

The running application will now be available at http://localhost/

Files
=====""",
    install_requires=[
        "Pylons==0.9.7",
        "SQLAlchemy>=0.5,<=0.5.99",
        "Mako",
        "docutils>=0.7,<=0.7.99",
        "mysql-python>=1.2"
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
