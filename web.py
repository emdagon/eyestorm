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

"""
Contains all Web related functionality such as cookies and session management,
and Tornado's handler helpers.
"""


import base64
import functools
import time
from bson import ObjectId
import logging

from tornado.web import RequestHandler, asynchronous, HTTPError, urlparse, \
                        urllib
from tornado.escape import json_encode, json_decode

import eyestorm

from models import Session, Sessions

# Dev purposes (will be removed)
from pprint import pprint


### Routes

routes = []


def register_handler(route, handler, args=None):
    """Register a route pointing to the handler.

    Used in `route` class decorator.

    Keyword arguments:
    route -- str or regex within the Web route to the handler
    handler -- A tornado.web.RequestHandler (at least) instance
    args -- dict within the handler constructor arguments

    """

    global routes

    if args:
        routes.append((route, handler, args))
    else:
        routes.append((route, handler))


def register_handlers(handlers):
    """Register a set of handlers at one time.

    Arguments:
    handlers -- a list of tuples of `register_handler` arguments

    """

    global routes

    routes += handlers


class route():
    """Handler class decorator, intended to maitain both class and route
    together (for best reading purposes).

    Arguments:
    route -- str or regex within the Web route to the handler
    args -- dict within the handler constructor arguments

    """

    def __init__(self, route, args=None):
        self.route = route
        self.args = args

    def __call__(self, handler):
        if isinstance(self.route, list):
            register_handlers([(route, handler, self.args) \
                                                    for route in self.route])
        else:
            register_handler(self.route, handler, self.args)
        return handler


### Sessions management

def using_session(method):
    """Handler method decorator, intended to provides session support.

    Once this decorator is used, the 'self.session' attribute will be setted
    to the handler instance containing an `eyestorm.objects.Entity`. It can be
    used freely and will be saved automaticly.

    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        _auto_finish = self._auto_finish

        def _update_expiration():
            if hasattr(self, '__session_updated'):
                return
            self.session.__expires = int(time.time()) + \
                self.application.settings.get('sesssions_lifetime', 30) * 60
            self.__session_updated = True

        def _callback(entity, error):
            self.session = entity
            _update_expiration()
            self._auto_finish = _auto_finish
            self._on_session_loaded()
            method(self, *args, **kwargs)

        if hasattr(self, 'session') and isinstance(self.session, Session):
            _update_expiration()
            method(self, *args, **kwargs)
        else:
            self._auto_finish = False
            session = Session(self)
            session_id = self._get_session_id()
            session.load(_id=ObjectId(session_id), callback=_callback)

    return wrapper


@eyestorm.periodic_callback('master', 60000)
def sessions_cleaner():
    """Sessions expiration maintainer"""
    timestamp = int(time.time())
    logging.debug("cleanning sessions... %i", timestamp)

    def _callback(result, error):
        if result and result['n'] > 0:
            logging.debug("%i sessions cleaned up!", result['n'])
    sessions = Sessions()
    sessions.remove(({'__expires': {'$lt': timestamp}}),
                    callback=_callback)


# Copied from tornado.web
# It's a workaround in order to decorate with @using_session
def authenticated(method):
    """Decorate methods with this to require that the user be logged in."""
    @using_session
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            if self.request.method in ("GET", "HEAD"):
                url = self.get_login_url()
                if "?" not in url:
                    if urlparse.urlsplit(url).scheme:
                        # if login url is absolute, make next absolute too
                        next_url = self.request.full_url()
                    else:
                        next_url = self.request.uri
                    url += "?" + urllib.urlencode(dict(next=next_url))
                self.redirect(url)
                return
            raise HTTPError(403)
        return method(self, *args, **kwargs)
    return wrapper


class BaseHandler(RequestHandler):
    """Eyestorm main handler, intended to be extended by the application
    handlers. It provides cookies and session management methods
    """

    def __init__(self, application, request, **kwargs):
        self.__session_id = None
        self.session = False
        super(BaseHandler, self).__init__(application, request, **kwargs)

    def write_cookie(self, name, value):
        value = base64.b64encode(json_encode(value))
        self.set_cookie(name, value)

    def read_cookie(self, name, default=None):
        value = self.get_cookie(name)
        if value:
            return json_decode(base64.b64decode(value))
        return default

    def _get_session_id(self):
        if not self.__session_id:
            self.__session_id = self.get_secure_cookie(
                                self.application.settings.get('sessions_name'),
                                None)
            if self.__session_id == None:
                self.__session_id = str(ObjectId())
                self._set_session_id(self.__session_id)
        return self.__session_id

    def _set_session_id(self, value):
        logging.debug("setting cookie: %s", value)
        self.set_secure_cookie(
                        self.application.settings.get('sessions_name'),
                        value,
                        self.application.settings.get('sessions_expiration'))

    def _on_session_loaded(self):
        """Override this method to perform actions just after the session
        is loaded.

        The session will be available on self.session
        """
        pass

    def _before_session_save(self):
        """Override this method to perform actions just before the session
        is saved.
        """
        pass

    def finish(self, chunk=None):
        if not self._finished and isinstance(self.session, Session):
            def _callback(entity, error):
                if error:
                    raise Exception("Warning: error saving the session! (%s)" \
                                    % error)
            self._before_session_save()
            self.session.update(callback=_callback)
        super(BaseHandler, self).finish(chunk)


class CleanHandler(BaseHandler):
    """Register a route pointing to this handler to clean all cookies."""
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.settings.get('web_root', "/"))
