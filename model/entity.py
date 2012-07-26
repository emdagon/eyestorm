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
from tornado.escape import json_encode

from eyestorm.objects import Persistable

from exceptions import InvalidAttribute, UnknownAttribute, MissingAttribute

from attributes import PrimaryKey, Reference, ReferenceOneToMany

from pprint import pprint


class Entity(Persistable):

    _collection = None
    _private_attributes = ['_db', '_values', '_callback', '_collection',
                           '_collection_name', '_error', '_exists', '_deleted',
                           'operate']

    _accepts_unknown_attributes = True
    _attributes = {}

    def __init__(self):
        super(Entity, self).__init__()
        self._values = {}
        for key, spec in self.__class__._attributes.iteritems():
            self._values[key] = spec.default
        self._collection = None
        self._callback = None
        self._error = None
        self._exists = False
        self._deleted = {}
        if self.__class__._collection:
            self._set_collection(self.__class__._collection)

    def __getattr__(self, name):
        if name in self.__class__._private_attributes:
            return self.__dict__[name]
        elif name in self._values:
            return self._values[name]
        return None

    def __setattr__(self, name, value):
        if name in self.__class__._private_attributes:
            self.__dict__[name] = value
        else:
            self.__set_attribute(name, value)

    def __delattr__(self, name):
        if name in self._values:
            self._deleted[name] = 1
            del self._values[name]

    def __eq__(self, comparison):
        if isinstance(comparison, Entity):
            return self._id == comparison._id
        return str(self._id) == comparison

    def __ne__(self, comparison):
        return not self.__eq__(comparison)

    def __set_attribute(self, name, value):
        if name in self.__class__._attributes:
            spec = self.__class__._attributes[name]
            if spec.validate(value):
                if isinstance(spec, Reference) \
                        and isinstance(spec.reference, PrimaryKey):
                    self._values[name] = str(value)
                else:
                    self._values[name] = spec.cast(value)
            else:
                raise InvalidAttribute(name, value)
        elif self.__class__._accepts_unknown_attributes:
            self._values[name] = value
        else:
            raise UnknownAttribute(name)

    def __check_values(self):
        for name, attribute in self.__class__._attributes.iteritems():
            if attribute.required and not name in self._values:
                raise MissingAttribute(self.__class__, name)

    def validate_reference(self, value):
        return True

    def _return(self):
        if callable(self._callback):
            self._callback(entity=self, error=self._error)

    # responses
    def response_dict(self):
        attributes = self._values.copy()
        if '_id' in attributes:
            attributes['_id'] = str(attributes['_id'])
        return attributes

    def response_json(self):
        return json_encode(self.response_dict())

    # attributes management
    def set_attributes(self, attributes, exists=False, force=False):
        if force:
            self._values = attributes
        else:
            self._exists = exists
            self._values = {}
            for name, value in attributes.iteritems():
                self.__set_attribute(name, value)

    def update_attributes(self, attributes, force=False):
        if force:
            self._values.update(attributes)
        else:
            for name, value in attributes.iteritems():
                self.__set_attribute(name, value)

    def get_attributes(self):
        return self._values

    # validation
    def exists(self):
        return (self._exists and '_id' in self._values)

    # reading
    def load(self, _id=None, attributes=None, callback=None, **kwargs):
        self._callback = callback
        if _id:
            self._id = ObjectId(_id)
            self.operate.set_criteria(self._id)
            self._collection.find_one({'_id': self._id},
                                      callback=self._on_load, **kwargs)
        elif isinstance(attributes, dict):
            if '_id' in attributes:
                attributes['_id'] = ObjectId(attributes['_id'])
            self.operate.set_criteria(attributes)
            self._collection.find_one(attributes,
                                      callback=self._on_load, **kwargs)

    def _on_load(self, result, error):
        if result:
            self._values = result
            self._exists = True
            self.operate.set_criteria(self._id)
        else:
            self._error = error
        self._return()

    # writing
    def save(self, callback=None, force_update=False):
        self._callback = callback
        if self.exists() or force_update:
            self._update()
        else:
            self._insert()

    def _insert(self):
        if not '_id' in self._values or not self._values['_id']:
            self.__set_attribute('_id', ObjectId())
        self.__check_values()
        self._collection.insert(self._values, callback=self._on_insert)

    def _on_insert(self, result, error):
        if result:
            self._exists = True

            def referenced(entity, error):
                print "referenced! =D"
                pprint(entity)

            for name, attribute in self.__class__._attributes.iteritems():
                if isinstance(attribute, ReferenceOneToMany):

                    def _append_to_stack(entity, error, stack=attribute.stack):
                        getattr(entity, stack).append(str(self._id))
                        entity.update(referenced)

                    attribute.model.find(_id=getattr(self, name),
                                         callback=_append_to_stack)


        self._error = error
        self._return()

    def _update(self):
        self.__check_values()
        self._collection.update({'_id': self._values['_id']},
                                self._values, callback=self._on_update)

    def _on_update(self, result, error):
        if result:
            self._exists = True
        self._error = error
        self._return()

    def update(self, callback):
        self.__check_values()
        if self.exists():
            document = self._values.copy()
            del document['_id']
            operations = {'$set': document}
            if self._deleted:
                operations['$unset'] = self._deleted
            self._collection.update({'_id': self._values['_id']},
                                    operations,
                                    callback=callback)
        else:
            self.save(callback)

    # deleting
    def delete(self, _id=None, criteria=None, callback=None):
        self._callback = callback
        if _id:
            self._collection.remove(ObjectId(_id), callback=self._on_delete)
        elif criteria:
            self._collection.remove(criteria, callback=self._on_delete)
        elif self.exists():
            self._collection.remove(self._values['_id'],
                                    callback=self._on_delete)
        else:
            return False

    def _on_delete(self, result, error):
        if not error:
            self._exists = False
        self._error = error
        self._return()

    @classmethod
    def create(cls, callback, **kwargs):
        entity = cls()
        entity.update_attributes(kwargs)
        entity.save(callback)

    @classmethod
    def fast_update(cls, _id, callback, **kwargs):
        def _callback(entity, error):
            if entity.exists():
                entity.update_attributes(kwargs)
                entity.update(callback)
            else:
                callback(entity, error)
        entity = cls()
        entity.load(_id=_id, callback=_callback)



    @classmethod
    def find(cls, callback, **kwargs):
        entity = cls()
        entity.load(callback=callback, attributes=kwargs)
