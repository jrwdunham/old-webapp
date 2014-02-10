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

from sqlalchemy.engine import create_engine
from sqlalchemy import MetaData, Table, orm
from sqlalchemy.ext.declarative import declarative_base
from pylons import config
from onlinelinguisticdatabase.model import meta
import onlinelinguisticdatabase.model as model

"""Functionality for taking the database of and OLD application and copying it
to a SQLite3 database.

"""


def getDBName():
    dbName = config['sqlalchemy.url']
    dbName = dbName.split('/')[-1]
    dbName = dbName.split('.')[0]
    return '%s_bk.db' % dbName


def quick_mapper(table):
    Base = declarative_base()
    class GenericMapper(Base):
        __table__ = table
    return GenericMapper


# Source objects
source = meta.Session
smeta = meta.metadata
tables = sorted(smeta.tables.keys())


# Destination objects
dbName = getDBName()
dengine = create_engine('sqlite:///%s' % dbName)
dsession = orm.sessionmaker(bind=dengine)
destination = dsession()


def createSQLiteDBCopy():
    for table_name in tables:
        print 'Processing', table_name
        table = Table(table_name, smeta, autoload=True)
        table.metadata.create_all(dengine)
        NewRecord = quick_mapper(table)
        columns = table.columns.keys()
        for record in source.query(table).all():
            data = dict(
                [(str(column), getattr(record, column)) for column in columns]
            )
            destination.merge(NewRecord(**data))
    print 'Committing changes'
    destination.commit()