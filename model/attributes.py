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

from pprint import pprint

## Basic attribute types

class Attribute(object):

    def __init__(self, required=True, null=False, default=None,
                 min_length=None, max_length=None):
        self.null = null
        self.required = required
        self.default = default
        self.min_length = min_length
        self.max_length = max_length

    def is_null(self, value):
        return (value is None)

    def validate_length(self, value):
        if self.min_length and len(value) < self.min_length:
            return False
        if self.max_length and len(value) > self.max_length:
            return False
        return True

    def cast(self, value):
        return value or self.default

    def validate(self, value):
        if not self.null and self.is_null(value):
            return False
        return self.validate_length(value)


class String(Attribute):

    def cast(self, value):
        return str(value)


class Number(Attribute):

    def __init__(self, min_value=None, max_value=None, **kwargs):
        super(Number, self).__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def validate_range(self, value):
        if self.min_value and value < self.min_value:
            return False
        if self.max_value and value > self.max_value:
            return False
        return True

    def validate(self, value):
        if super(Number, self).validate(value):
            return self.validate_range(value)
        return False


class Integer(Number):

    def cast(self, value):
        return int(value)


class Float(Number):

    def cast(self, value):
        return float(value)


class Boolean(Attribute):

    def cast(self, value):
        return bool(value)


class Array(Attribute):

    def __init__(self, items_type=None, **kwargs):
        super(Array, self).__init__(**kwargs)
        self.items_type = items_type

    def validate_item(self, item):
        return ((isinstance(self.items_type, Attribute)
                    and self.items_type.validate(item))
                or isinstance(item, self.items_type))

    def validate_items(self, items):
        if self.items_type:
            for item in items:
                if self.validate_item(item):
                    continue
                return False
        return True

    def validate(self, value):
        if super(Array, self).validate(value):
            return self.validate_items(value)
        return False

    def cast(self, value):
        return list(value)


class Object(Attribute):

    def validate(self, value):
        if super(Object, self).validate(value):
            return isinstance(value, dict)
        return False


class PrimaryKey(Attribute):

    def __init__(self):
        super(PrimaryKey, self).__init__()
        self.required = True

    def cast(self, value):
        return ObjectId(value)

    def validate(self, value):
        try:
            ObjectId(value)
            return True
        except:
            return False


# References

from eyestorm.model import _models


class Reference(Attribute):

    def __init__(self, model, attribute):
        super(Reference, self).__init__()
        self.model_name = model
        self.attribute = attribute
        self.required = True

    @property
    def model(self):
        return _models[self.model_name]

    @property
    def reference(self):
        return _models[self.model_name]._attributes[self.attribute]


class ReferenceOneToOne(Reference):

    def validate(self, value):
        return self.reference.validate(value)


class ReferenceOneToMany(Reference):

    def __init__(self, model, stack):
        super(ReferenceOneToMany, self).__init__(model, '_id')
        self.stack = stack

    def validate(self, value):
        return self.reference.validate(value)
        # if isinstance(self.reference, ReferenceManyToOne):
        #     return self.reference.validate_item(value)
        # return False


class ReferenceManyToOne(Reference, Array):

    def __init__(self, model, attribute):
        super(ReferenceManyToOne, self).__init__(model, attribute)
        self.items_type = PrimaryKey
        self.required = False
        self.default = []


def is_a(model):
    return ReferenceOneToOne(model, '_id')

def as_in(model, stack):
    return ReferenceOneToMany(model, stack)

def has_many(model, attribute='_id'):
    return ReferenceManyToOne(model, attribute)
