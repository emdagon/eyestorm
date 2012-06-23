#!/bin/env python
#
# Copyright 2012 Emilio Daniel Gonzalez (@emdagon)
#
# This file is part of Eyestorm.
#
# Eyestorm is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Eyestorm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Eyestorm.  If not, see <http://www.gnu.org/licenses/>.

from bson import ObjectId
import logging

import tornado
import asyncmongo

from eyestorm import options


# Dev purposes (will be removed)
from pprint import pprint


def singleton(cls):
    instances = {}

    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance


@singleton
class Db(object):
    """System-wide (singleton) asyncmongo client instance"""

    def __init__(self):
        self._config = options.db
        self._connection = asyncmongo.Client(**self._config)
        logging.info("Mongo connection created")

    def get_config(self):
        return self._config

    def get_connection(self):
        return self._connection


class MongoHelper():

    def __init__(self, collection):
        self._collection = collection

    def set_criteria(self, criteria):
        if isinstance(criteria, ObjectId):
            self._criteria = {'_id': criteria}
        else:
            self._criteria = criteria

    def __getattr__(self, name):
        def method(field, value=None, callback=None):
            self._collection.update(spec=self._criteria,
                                    document={"$%s" % name: {field: value}},
                                    callback=callback)
        return method


class Persistable(object):
    """`Abstract` class that represent a mongo collection object.

    Provides the `db` attribute pointing to Db instance

    """

    def __init__(self):
        self._db = None

    @property
    def db(self):
        self._initialize_db()
        return self._db

    def _initialize_db(self):
        if self._db is None:
            self._db = Db().get_connection()

    def _set_collection(self, collection):
        self._initialize_db()
        self._collection_name = collection
        self._collection = getattr(self._db, collection)
        self.operate = MongoHelper(self._collection)

    def get_collection_name(self):
        return self._collection_name


class Collection(Persistable):

    def __init__(self):
        super(Collection, self).__init__()
        self._data = []
        self.attributes = None
        self._indexes = {}
        if self.__class__._collection:
            self._set_collection(self.__class__._collection)

    def __getitem__(self, index):
        return self._data[index]

    def __len__(self):
        return len(self._data)

    # reading
    def load(self, attributes=None, callback=None, **kwargs):
        self._callback = callback
        if not isinstance(attributes, dict):
            attributes = {}
        self.attributes = attributes
        self.operate.set_criteria(attributes)
        self._collection.find(attributes, callback=self._on_load, **kwargs)

    def _on_load(self, result, error):
        if not error:
            self._data = result
            self.operate.set_criteria(self.attributes)
        self._callback(collection=self, error=error)

    def count(self, attributes=None, callback=None, **kwargs):
        def _callback(collection=None, error=None):
            callback(len(self._data))
        if len(self._data) > 0:
            _callback()
            return
        self.load(attributes, callback=_callback, **kwargs)

    # writing
    def insert(self, items, callback=None):
        self._callback = callback
        self._items = items
        self._collection.insert(items, callback=self._on_insert)

    def _on_insert(self, result, error):
        if not error:
            self.set_items(self._items)
        del self._items
        self._callback(self, error)

    # deleting
    def remove(self, attributes=None, callback=None, **kwargs):
        self._callback = callback
        if not isinstance(attributes, dict):
            attributes = {}
        self.attributes = attributes
        self._collection.remove(attributes, callback=self._on_remove, **kwargs)

    def _on_remove(self, result, error):
        self._error = error
        self._callback(result[0], error)

    # items
    def set_items(self, items):
        self._data = items

    def get_items(self):
        return self._data

    # responses
    def response_dict(self):
        def stringfy(document):
            d = document.copy()
            d['_id'] = str(d['_id'])
            return d
        return map(stringfy, self._data)

    def get_attributes(self, attribute):
        return map(lambda d: d[attribute], self._data)

    # advance getters
    def get_indexes(self, attribute):
        if not attribute in self._indexes:
            self._indexes[attribute] = {}
            for document in self._data:
                if attribute in document:
                    if not document[attribute] in self._indexes[attribute]:
                        self._indexes[attribute][document[attribute]] = []
                    self._indexes[attribute][document[attribute]].append(
                                                                    document)
        return self._indexes[attribute]

    def get_by_attribute(self, **attributes):
        result = []
        for key, value in attributes.items():
            indexes = self.get_indexes(key)
            if value in indexes:
                result = result + (indexes[value])
        return result

    # validation
    def exists(self):
        return len(self._data) > 0
