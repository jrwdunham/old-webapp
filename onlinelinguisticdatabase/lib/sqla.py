from sqlalchemy.engine import create_engine
from sqlalchemy import MetaData, Table, orm
from sqlalchemy.ext.declarative import declarative_base
from pylons import config
from onlinelinguisticdatabase.model import meta
import onlinelinguisticdatabase.model as model


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


def createSQLiteCopy():
    for table_name in tables:
        print 'Processing', table_name
        print 'Pulling schema from source server'
        table = Table(table_name, smeta, autoload=True)
        print 'Creating table on destination server'
        table.metadata.create_all(dengine)
        NewRecord = quick_mapper(table)
        columns = table.columns.keys()
        print 'Transferring records'
        for record in source.query(table).all():
            data = dict(
                [(str(column), getattr(record, column)) for column in columns]
            )
            destination.merge(NewRecord(**data))
    print 'Committing changes'
    destination.commit()