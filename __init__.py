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

import logging

import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options


# Dev purposes (will be removed)
from pprint import pprint


define('address', default='127.0.0.1', help="Server address")
define('port', default=80, help="Server port")
define('context', default="all",
       help="Arbitrary, used for delimiting the server behavior; "\
            "For more information see periodic_callbacks")

define('db', default={'pool_id': "EyeStorm", 'host': "localhost",
                      'port': 27017, 'maxcached': 30, 'maxconnections': 60,
                      'dbname': "eyestorm"},
       help="asyncmongo.Client parameters")

define('debug', default=True,
       help="See http://www.tornadoweb.org/documentation/autoreload.html")

define('autoescape', default="xhtml_escape",
       help="See http://www.tornadoweb.org/documentation/template.html?highlight=autoescape")

define('app_title', default="EyeStorm app", help="Application title")

define('cookie_secret', default="...",
       help="http://www.tornadoweb.org/documentation/web.html?highlight=cookie#tornado.web.RequestHandler.set_secure_cookie")
# I use the following line to generate it:
# base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)

define('app_path', default="/", help="Application main folder path (Deprecated)")
define('template_path', default="templates", help="Templates folder")
define('static_path', default="static", help="Static folder")

define('login_url', default="/login",
       help="http://www.tornadoweb.org/documentation/_modules/tornado/web.html#authenticated")

define('web_root', default="/", help="Application main Web path")

define('default_locale', default=False, type=str,
       help="http://www.tornadoweb.org/documentation/locale.html?highlight=get_closest_locale#tornado.locale.set_default_locale")
define('translations_path', default=False, type=str,
       help="http://www.tornadoweb.org/documentation/locale.html?highlight=load_gettext_translations#tornado.locale.load_gettext_translations")
define('translations_domain', default=False, type=str,
       help="See translations_path")

define('sessions_store_collection', default="eyestorm_sessions")
define('sessions_name', default="eyestorm_sid")
#days
define('sessions_expiration', default=1)
#minutes
define('sesssions_lifetime', default=25)


_looper = tornado.ioloop.IOLoop.instance()

add_timeout = _looper.add_timeout
add_callback = _looper.add_callback
remove_timeout = _looper.remove_timeout

# Periodic Callbacks support
__ioloop_periodic_callbacks = {'all': []}


def register_periodic_callback(context, method, interval):
    global __ioloop_periodic_callbacks
    if context in __ioloop_periodic_callbacks:
        __ioloop_periodic_callbacks[context].append((method, interval))
    else:
        __ioloop_periodic_callbacks[context] = [(method, interval)]


class periodic_callback():

    def __init__(self, context="all", interval=60000):
        self.context = context
        self.interval = interval

    def __call__(self, method):
        logging.info("Periodic callback: '%s' in '%s', interval: %s" % \
                     (method.__name__, self.context, self.interval))
        register_periodic_callback(self.context, method, self.interval)


def get_periodic_callbacks(context):
    if not context:
        return
    callbacks = __ioloop_periodic_callbacks['all']
    if context in __ioloop_periodic_callbacks:
        callbacks += __ioloop_periodic_callbacks[context]
    return callbacks


from objects import singleton, Persistable, Collection

from model import Entity, Entities

from web import routes


class Application(tornado.web.Application):

    def __init__(self, config_file=None):
        global options

        if config_file:
            tornado.options.parse_config_file(config_file)

        tornado.options.parse_command_line()

        self.settings = {}
        for option in options:
            self.settings[option] = options[option].value()


    def start(self):
        global __looper, options, routes

        tornado.web.Application.__init__(self, routes, **self.settings)

        if options.debug:
            logging.info("Starting in debug mode.")

        if options.default_locale:
            tornado.locale.set_default_locale(options.default_locale)

        if options.translations_path and options.translations_domain:
            tornado.locale.load_gettext_translations(options.translations_path,
                                                   options.translations_domain)

        application = tornado.httpserver.HTTPServer(self)
        application.listen(options.port, address=options.address)

        periodic_callbacks = get_periodic_callbacks(options.context)
        if len(periodic_callbacks) > 0:
            for method, interval in periodic_callbacks:
                method()
                tornado.ioloop.PeriodicCallback(method, interval,
                                                io_loop=_looper).start()

        try:
            logging.info("Starting %s", options.app_title)
            _looper.start()
        except KeyboardInterrupt:
            logging.info("Stoping %s", options.app_title)
            _looper.stop()
            _looper.close()
