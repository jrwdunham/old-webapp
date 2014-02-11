The Online Linguistic Database (OLD) is software for creating web
applications dedicated to multi-user, collaborative documention of
natural (and usually endangered or understudied) languages. An OLD
web application helps contributors to create a consistent,
structured, and highly searchable web-based repository of language
data. These data consist of textual representations of linguistic
examples (words, morphemes, and sentences with analyses and
annotations), associated and embedded media files, and exportable
representations of texts (e.g., research papers, narratives, etc.)

# Features

1.  Multi-user, concurrent read/write access to a server-side
    language database.
2.  Interlinear glossed text (IGT) representations of data with
    integrated feedback on lexical consistency or morphological
    analyses.
3.  Powerful searches over the data set.
4.  Authentication and authorization to control access to data.
5.  Export to LaTeX, CSV, and plain text.
6.  Media file support: many-to-many associations of audio, video,
    and/or image with content embedded in data representations.
7.  IGT text creation.
8.  Automatic orthography conversion.
9.  Inventory-based transcription input validation.

# Versions

This is the OLD v. 0.2.X. It is being used in nine
language-specific OLD web applications (see
www.onlinelinguisticdatabase.org) and is still being maintained.
However, primary development has moved to the
[OLD v. 1.0](https://github.com/jrwdunham/old), which includes
support for creating morphological parsers, provides improved
search functionality, and implements a shift to a more modular and
reusable architecture (i.e., a RESTful HTTP/JSON web service with a
SPA GUI). The applications running on the OLD v. 0.2.X will be
migrated to the OLD v. 1.0 in the near future.

# License

The OLD 0.2.X is open source and is licensed under the
[GNU GENERAL PUBLIC LICENSE Version 3](https://gnu.org/licenses/gpl.html).
(Note that the OLD 1.0 is also open source but is licensed under
[Apache 2.0](http://www.apache.org/licenses/LICENSE-2.0.txt).

# Technologies

The OLD is written in Python, using the
[Pylons](http://www.pylonsproject.org/projects/pylons-framework/about)
web framework and an [SQLAlchemy](http://www.sqlalchemy.org/)
abstraction over a MySQL database.

# Get & Install

To install the OLD 0.2.X locally for or testing purposes, it is
recommended that you use an isolated Python environment, which can
be created using
[virtualenv](http://www.virtualenv.org/en/latest/virtualenv.html).
(Note that the OLD 0.2.X has been tested with Python 2.5 and 2.6,
but not 2.7. Depending on your system Python version, it may be
necessary to install Python 2.5 or 2.6 using
[pyenv](https://github.com/yyuu/pyenv) or
[pythonbrew](https://github.com/utahta/pythonbrew).)

Run the following commands to get, install, and configure the OLD
v. 0.2.X. (Note that the first two lines are relevant only if you
are using a virtual environment.):

    virtualenv --no-site-packages env
    source env/bin/activate
    git clone https://github.com/jrwdunham/old-webapp.git
    cd old-webapp
    python setup.py develop
    paster setup-app development.ini
    paster serve --reload development.ini

The default configuration file (`development.ini`) uses a local
SQLite database named `development.db`, which is probably fine for
exploring the system. A deployed OLD 0.2.X application should use
MySQL. After creating a MySQL database and a user with sufficient
privileges, comment out the SQLite option in the OLD 0.2.X
configuration file and uncomment the two MySQL lines.:

    sqlalchemy.url = mysql://username:password@localhost:3306/dbname
    sqlalchemy.pool_recycle = 3600

See [The Pylons Book](http://pylonsbook.com/) for further details
on serving and configuring Pylons-based web applications.



