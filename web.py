
import base64
import functools
import time
from bson import ObjectId

import eyestorm

import tornado.web
from tornado.web import asynchronous, HTTPError, urlparse, urllib

from models import Session, Sessions

from pprint import pprint

routes = []


class BaseHandler(tornado.web.RequestHandler):


    def __init__(self, application, request, **kwargs):
        self.__session_id = None
        self.session = False
        super(BaseHandler, self).__init__(application, request, **kwargs)


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
        print "setting cookie: %s" % value
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


    def write_cookie(self, name, value):
        value = base64.b64encode(tornado.escape.json_encode(value))
        self.set_cookie(name, value)

    def read_cookie(self, name, default=None):
        value = self.get_cookie(name)
        if value:
            return tornado.escape.json_decode(base64.b64decode(value))
        return default



class CleanHandler(BaseHandler):


    def get(self):
        self.clear_all_cookies()
        self.redirect("/")


def register_handler(route, handler, args=None):
    global routes
    if args:
        routes.append((route, handler, args))
    else:
        routes.append((route, handler))


def register_handlers(handlers):
    global routes
    routes += handlers


class route():

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


def using_session(method):
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
    timestamp = int(time.time())
    print "cleanning sessions... " + str(timestamp)
    def _callback(result, error):
        if result and result['n'] > 0:
            print "%i sessions cleaned up!" % result['n']
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


def base64_url_decode(input):
    input += '=' * (4 - (len(input) % 4))
    return base64.urlsafe_b64decode(input.encode('utf-8'))
