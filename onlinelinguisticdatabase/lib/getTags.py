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

import onlinelinguisticdatabase.model as model
import onlinelinguisticdatabase.model.meta as meta

from sqlalchemy.sql import desc

try:
    import json
except ImportError:
    import simplejson as json


def getTags(tagsList=None):
    """ Function gets speakers, users, sources, syntactic categories
    and elicitation methods options from their respective tables in 
    the database and returns them.

    tagsList is an optional list argument specifying which tags should
    be retrieved.  If None, all tags are retrieved.
    
    """

    # speakers = [(speaker.id, speaker.firstName + ' ' + speaker.lastName)
    #               for speaker in speakers]
    # Note: users query-filtered out those with role=viewer
    # users = [(user.id, user.firstName + ' ' + user.lastName) for user in users]
    # nonAdministrators = [(user.id, user.firstName + ' ' + user.lastName)
    #                        for user in users if user.role != u'administrator']
    # unrestrictedUsers = [(uu.id, uu.firstName + u' ' + uu.lastName)
    #                        for uu in unrestrictedUsers]
    # sources = [(source.id, source.authorLastName + ', ' +
    #                source.authorFirstName[0].upper() + '.  ' +
    #                unicode(source.year) + '.  ' +
    #                source.title[:10] + '...') for source in sources]
    # syncats = [(syncat.id, syncat.name) for syncat in syncats]
    # keywords = [(keyword.id, keyword.name) for keyword in keywords]
    # elicitationMethods = [(elicitationMethod.id, elicitationMethod.name)
    #                       for elicitationMethod in elicitationMethods_q.all()]

    # Speakers
    speakers = []
    if not tagsList or 'speakers' in tagsList:
        speakers = meta.Session.query(model.Speaker).order_by(
            model.Speaker.lastName).all()

    # Users
    users = []
    nonAdministrators = []
    if not tagsList or 'users' in tagsList:
        users = meta.Session.query(model.User).order_by(
            model.User.lastName).all()
        nonAdministrators = [user for user in users if
                             user.role != u'administrator']

    # Unrestricted Users
    unrestrictedUsers = []
    if not tagsList or 'unrestrictedUsers' in tagsList:
        appSet = meta.Session.query(
            model.ApplicationSettings).order_by(  
            desc(model.ApplicationSettings.id)).first()

        try:
            unrestrictedUserIDs = tuple([int(uu) for uu in json.loads(
                appSet.unrestrictedUsers)])
        except TypeError: # Error caused by json choking on None
            unrestrictedUserIDs = []
        unrestrictedUsers = meta.Session.query(model.User).filter(
            model.User.id.in_(unrestrictedUserIDs)).all()

    # Sources
    sources = []
    if not tagsList or 'sources' in tagsList:
        sources = meta.Session.query(model.Source).order_by(
            model.Source.authorLastName).order_by(
            model.Source.authorFirstName).order_by(
            desc(model.Source.year)).all()

    # Syntactic Categories
    syncats = []
    if not tagsList or 'syncats' in tagsList:
        syncats = meta.Session.query(model.SyntacticCategory).order_by(
            model.SyntacticCategory.name).all()

    # Keywords
    keywords = []
    if not tagsList or 'keywords' in tagsList:    
        keywords = meta.Session.query(model.Keyword).order_by(
            model.Keyword.name).all()

    # Elicitation Methods
    elicitationMethods = []
    if not tagsList or 'elicitationMethods' in tagsList:
        elicitationMethods_q = meta.Session.query(
            model.ElicitationMethod).order_by(
            model.ElicitationMethod.name).all()

    return {
        'speakers': speakers,
        'users': users,
        'nonAdministrators': nonAdministrators,
        'unrestrictedUsers': unrestrictedUsers,
        'sources': sources,
        'syncats': syncats,
        'keywords': keywords,
        'elicitationMethods': elicitationMethods
    }
