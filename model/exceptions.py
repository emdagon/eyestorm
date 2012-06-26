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


class InvalidAttribute(Exception):

    def __init__(self, name, value):
        self.name = str(name)
        self.value = repr(value)

    def __str__(self):
        return "Invalid value for '%s': %s" % (self.name, str(self.value))


class UnknownAttribute(Exception):

    def __init__(self, name):
        self.name = str(name)

    def __str__(self):
        return "Unknown '%s' Attribute" % self.name


class MissingAttribute(Exception):

    def __init__(self, model, name):
        self.model = repr(model)
        self.name = str(name)

    def __str__(self):
        return "Missing attribute '%s' for %s model" % (self.name, self.model)
