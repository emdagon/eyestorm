
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options

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

define('web_root', default="", help="Application main Web path")

define('default_locale', default=False, type=str,
       help="http://www.tornadoweb.org/documentation/locale.html?highlight=get_closest_locale#tornado.locale.set_default_locale")
define('translations_path', default=False, type=str,
       help="http://www.tornadoweb.org/documentation/locale.html?highlight=load_gettext_translations#tornado.locale.load_gettext_translations")
define('translations_domain', default=False, type=str,
       help="See translations_path")

define('sessions', default=False, help="")
define('sessions_store_collection', default="sessions")
define('sessions_name', default="eyestorm_sid")
#days
define('sessions_expiration', default=1)
#minutes
define('sesssions_lifetime', default=5)

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
        register_periodic_callback(self.context, method, self.interval)


def get_periodic_callbacks(context):
    if not context:
        return
    callbacks = __ioloop_periodic_callbacks['all']
    if context in __ioloop_periodic_callbacks:
        callbacks += __ioloop_periodic_callbacks[context]
    return callbacks



from objects import singleton, Entity, Persistable, Collection, Entities

from web import routes

class Application(tornado.web.Application):


    def __init__(self, config_file=None):
        global options, routes

        if config_file:
            tornado.options.parse_config_file(config_file)

        tornado.options.parse_command_line()

        settings = {}
        for option in options:
            settings[option] = options[option].value()

        tornado.web.Application.__init__(self, routes, **settings)


    def start(self):
        global __looper, options

        if options.debug:
            print "Starting in debug mode."

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
            print "Starting %s\n" % options.app_title
            _looper.start()
        except KeyboardInterrupt:
            print "\nStoping %s" % options.app_title
            _looper.stop()
            _looper.close()

