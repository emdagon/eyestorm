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

from eyestorm.objects import Entity, Collection


class Session(Entity):


    def __init__(self, handler):
        super(Session, self).__init__((handler.settings.get(
                                                'sessions_store_collection',
                                                "_eyestorm_sessions")))



class Sessions(Collection):


    def __init__(self):
        super(Sessions, self).__init__("sessions")
