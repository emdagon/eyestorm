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


def has_one(model):
    return ReferenceHasOne(model)


class Attribute():

    def __init__(self, required=True, null=False, default=None,
                 min_length=None, max_length=None):
        self.null = null
        self.required = required
        self.default = default
        self.min_length = min_length
        self.max_length = max_length

    def __call__(self):
        return "fruta"

    def is_null(self, value):
        return not bool(value)

    def validate_length(self, value):
        if self.min_length and len(value) < self.min_length:
            return False
        if self.max_length and len(value) > self.max_length:
            return False
        return True

    def cast(self, value):
        return value

    def validate(self, value):
        if not self.null and self.is_null(value):
            return False
        return self.validate_length(value)


class PrimaryKey(Attribute):

    def __init__(self):
        self.required = True

    def cast(self, value):
        return ObjectId(value)

    def validate(self, value):
        return True


class ReferenceHasOne(Attribute):

    def __init__(self, reference):
        self.required = True
        self.reference = reference

    def validate(self, value):
        return True
        #return self.reference.validate_reference(value)


class String(Attribute):

    def cast(self, value):
        return str(value)


class Number(Attribute):

    def __init__(self, min_value=None, max_value=None, **kwargs):
        Attribute.__init__(self, **kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def validate_range(self, value):
        if self.min_value and value < self.min_value:
            return False
        if self.max_value and value > self.max_value:
            return False
        return True

    def validate(self, value):
        if Attribute.validate(self, value):
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

    def cast(self, value):
        return list(value)


class Object(Attribute):

    pass
