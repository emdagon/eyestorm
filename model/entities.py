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

from eyestorm.objects import Collection

from entity import Entity


class Entities(Collection):

    _entity = Entity

    def __getitem__(self, index):
        data = self._data[index]
        entity = getattr(self.__class__, '_entity')()
        entity._set_collection(self.get_collection_name())
        entity.set_attributes(data, True)
        return entity

    def response_dict(self):
        response = []
        for item in self:
            response.append(item.response_dict())
        return response

    @classmethod
    def find(cls, callback, **kwargs):
        entity = cls()
        entity.load(attributes=kwargs, callback=callback)

