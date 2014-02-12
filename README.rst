The Online Linguistic Database (OLD) is software for creating web applications
dedicated to multi-user, collaborative documention of natural (and usually
endangered or understudied) languages. An OLD web application helps contributors
to create a consistent, structured, and highly searchable web-based repository
of language data. These data consist of textual representations of linguistic
examples (words, morphemes, and sentences with analyses and annotations),
associated and embedded media files, and exportable representations of texts
(e.g., research papers, narratives, etc.)


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

This is the OLD v. 0.2.X. It is being used in nine language-specific OLD web
applications (see www.onlinelinguisticdatabase.org) and is still being
maintained. However, primary development has moved to the
`OLD v. 1.0<https://github.com/jrwdunham/old>`_, which includes support for
creating morphological parsers, provides improved search functionality, and
implements a shift to a more modular and reusable architecture (i.e., a RESTful
HTTP/JSON web service with a SPA GUI). The applications running on the OLD v.
0.2.X will be migrated to the OLD v. 1.0 in the near future.


License
--------------------------------------------------------------------------------

The OLD 0.2.X is open source and is licensed under the
`GNU GENERAL PUBLIC LICENSE Version 3<https://gnu.org/licenses/gpl.html>`_.
(Note that the OLD 1.0 is also open source but is licensed under
`Apache 2.0 <http://www.apache.org/licenses/LICENSE-2.0.txt>`_.)


Technologies
--------------------------------------------------------------------------------

The OLD is written in Python, using the
`Pylons <http://www.pylonsproject.org/projects/pylons-framework/about>`_ web
framework and an `SQLAlchemy <http://www.sqlalchemy.org/>`_ abstraction over a
MySQL database.


Get & Install
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

From Source
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

To download the source code of the OLD v. 0.2.X, install its dependencies, and
serve it locally with the default configuration, run::

    git clone https://github.com/jrwdunham/old-webapp.git
    cd old-webapp
    python setup.py develop
    paster setup-app development.ini
    paster serve --reload development.ini


From PyPI
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

To install a stable release of the OLD 0.2.X from the
`Python Package Index <https://pypi.python.org/pypi/onlinelinguisticdatabase/0.2.8>`_,
use ``easy_install`` and run::

    easy_install "OnlineLinguisticDatabase==0.2.8"

or use ``Pip`` and run::

    pip install "OnlineLinguisticDatabase==0.2.8"

To create the config file, generate the default values, and serve the application::

    mkdir my_old_webapp
    cd my_old_webapp
    paster make-config onlinelinguisticdatabase production.ini
    paster setup-app production.ini
    paster serve production.ini


Using MySQL
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

The default configuration file (``development.ini``) uses a local SQLite
database named ``development.db``, which is probably fine for exploring the
system initially. However, a deployed OLD 0.2.X application should use MySQL.

First login to MySQL using your root account and create a MySQL database and a
user with sufficient privileges.  Something like this (replacing ``dbname``,
``username``, and ``password`` with sensible values)::

    mysql> create database dbname default character set utf8;
    mysql> create user 'username'@'localhost' identified by 'password';
    mysql> grant select, insert, update, delete, create, drop on dbname.* to 'username'@'localhost';
    mysql> quit;

Then comment out the SQLite option in the OLD 0.2.X configuration file (i.e.,
``development.ini`` or ``production.ini``) and uncomment the two MySQL lines, 
changing values as appropriate::

    sqlalchemy.url = mysql://username:password@localhost:3306/dbname
    sqlalchemy.pool_recycle = 3600

Now the system is set up to use MySQL. Run the ``setup-app`` command again to
generate the default values in the MySQL db::

    paster setup-app production.ini

or::

    paster setup-app development.ini

(You can ignore the ``data truncated`` warnings. This is a known issue.)

See `The Pylons Book <http://pylonsbook.com/>`_ for further details on serving
and configuring Pylons-based web applications.


Default Users
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Running ``paster setup-app`` creates three users with the following usernames
and passwords.

- username: ``admin``, password: ``admin``
- username: ``contributor``, password: ``contributor``
- username: ``viewer``, password: ``viewer``

Use the admin account to create a new administrator-level user and delete all
of the default users before deploying an OLD application.


Common Issues
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Note that if you are running Debian or Ubuntu and get an error like
``EnvironmentError: mysql_config not found`` after running
``python setup.py develop``, then you probably need to install
``libmysqlclient-dev``::

    sudo apt-get install libmysqlclient-dev

