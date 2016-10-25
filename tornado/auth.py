import tornado.web
import tornado.auth
import tornado.template as template
import json
import requests
import applicationTemplate
import secrets
import logging
import secrets
import torndb as database

db = database.Connection(host = secrets.mysqlHost,
                         database = secrets.mysqlSchema,
                         user = secrets.mysqlUser,
                         password = secrets.mysqlPasswd)

def isAuthorized(email):
    tRes = db.query("""select username
    from swefreq.users where email = '%s'
    and full_user""" % (email))

    if len(tRes)>0:
        return True, tRes[0]
    else:
        return False, None

class BaseHandler(tornado.web.RequestHandler):
    """Base Handler. Handlers should not inherit from this
    class directly but from either SafeHandler or UnsafeHandler
    to make security status explicit.
    """
    def get(self):
        """ The GET method on this handler will be overwritten by all other handler.
        As it is the default handler used to match any request that is not mapped
        in the main app, a 404 error will be raised in that case (because the get method
        won't be overwritten in that case)
        """
        raise tornado.web.HTTPError(404, reason='Page not found')

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_current_email(self):
        return self.get_secure_cookie("email")

    def get_current_token(self):
        return self.get_secure_cookie("access_token")

    def get_current_user_name(self):
        # Fix ridiculous bug with quotation marks showing on the web
        user = self.get_current_user()
        if user:
            if (user[0] == '"') and (user[-1] == '"'):
                return user[1:-1]
            else:
                return user
        return user

    def is_admin(self):
        email = self.get_current_email()
        tRes = db.query("""select full_user from swefreq.users where
                              email='%s' and swefreq_admin""" % email)
        lAdmin = True if len(tRes) == 1 else False
        return lAdmin

    def is_authorized(self):
        email = self.get_current_email()
        tRes = db.query("""select full_user from swefreq.users where
                              email='%s' and full_user""" % email)
        lAdmin = True if len(tRes) == 1 else False
        return lAdmin

    def write_error(self, status_code, **kwargs):
        """ Overwrites write_error method to have custom error pages.
        http://tornado.readthedocs.org/en/latest/web.html#tornado.web.RequestHandler.write_error
        """
        reason = 'Page not found'
        logging.info("Error do something here again")


class GoogleUser(object):
    """Stores the information that google returns from a user throuhgh its secured API.
    """
    def __init__(self, user_token):
        self.user_token = user_token
        self._google_plus_api = "https://www.googleapis.com/plus/v1/people/me"
        self.authenticated = False
        #Fetch actual information from Google API

        params = {'access_token': self.user_token.get('access_token')}
        r = requests.get(self._google_plus_api, params=params)
        if not r.status_code == requests.status_codes.codes.OK:
            self.authenticated = False
        else:
            info = json.loads(r.text)
            if isAuthorized([email['value'] for email in info.get('emails')][0]):
                self.authenticated = True
            self.display_name = info.get('displayName', '')
            self.emails = [email['value'] for email in info.get('emails')]

    def is_authorized(self, user_view):
        """Checks that the user is actually authorised to use genomics-status.
        """
        authenticated = False
        for email in self.emails:
            if user_view[email]:
                self.valid_email = email
                authenticated = True
        return authenticated

class SafeHandler(BaseHandler):
    """ All handlers that need authentication and authorization should inherit
    from this class.
    """
    def prepare(self):
        """This method is called before any other method.
        Having the decorator @tornado.web.authenticated here implies that all
        the Handlers that inherit from this one are going to require
        authentication in all their methods.
        """
        if not self.current_user:
            self.redirect('/static/not_authorized.html')

class AuthorizedHandler(BaseHandler):
    def prepare(self):
        if not self.current_user:
            self.redirect('/static/not_authorized.html')
        if not self.is_authorized():
            self.redirect('/static/not_authorized.html')

class UnsafeHandler(BaseHandler):
    pass

class LoginHandler(tornado.web.RequestHandler, tornado.auth.GoogleOAuth2Mixin):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("code", False):
            user_token =  yield self.get_authenticated_user(
                redirect_uri=self.application.settings['redirect_uri'],
                code=self.get_argument('code')
                )
            user = GoogleUser(user_token)
            logging.info(user.display_name)
            (lAuthorized, saUser) = isAuthorized(user.emails[0])

            self.set_secure_cookie('user', user.display_name)
            self.set_secure_cookie('email', user.emails[0])

            if user.authenticated and lAuthorized:
                self.set_secure_cookie('access_token', user_token['access_token'])
                #It will have at least one email (otherwise she couldn't log in)
                url=self.get_secure_cookie("login_redirect")
                self.clear_cookie("login_redirect")
                if url is None:
                    url = '/'
            else:
                url = '/'
            self.redirect(url)

        else:
            self.set_secure_cookie('login_redirect', self.get_argument("next", '/'), 1)
            self.authorize_redirect(
                        redirect_uri=self.application.settings['redirect_uri'],
                        client_id=self.application.oauth_key,
                        scope=['profile', 'email'],
                        response_type='code',
                        extra_params={'approval_prompt': 'auto'})

class LogoutHandler(tornado.web.RequestHandler, tornado.auth.GoogleOAuth2Mixin):
    def get(self):
        def handle_request(response):
            if response.error:
                logging.info("Error, failed in logout")
                logging.info(response.error)
            else:
                logging.info("User logged out")

        sAccessToken = self.get_secure_cookie("access_token")
        sLogoutUrl = "https://accounts.google.com/o/oauth2/revoke?token=" + str(sAccessToken)
        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch(sLogoutUrl, handle_request)

        self.clear_cookie("access_token")
        self.clear_cookie("login_redirect")
        self.set_secure_cookie('login_redirect', self.get_argument("next", '/'), 1)
        self.clear_cookie("user")
        self.clear_cookie("email")
        self.redirect("/")

class UnAuthorizedHandler(UnsafeHandler):
    """ Serves a page with unauthorized notice and information about who to contact to get access. """
    def get(self):
        # The parameters email and name can contain anything,
        # be careful not to evaluate them as code
        email = self.get_argument("email", '')
        name = self.get_argument("name", '')
        contact = self.get_argument("contact", "contact@example.com")
        t = template.Template(applicationTemplate.notAuthorizedHtml)
        self.write(t.generate())

class MainHandler(UnsafeHandler):
    """ Serves the html front page upon request.
    """
    def get(self):
        self.set_header('Access-Control-Allow-Origin', '*')
        t = template.Template(applicationTemplate.indexHtml)
        self.write(t.generate())

        self.write("MainHandler")
        #t = self.application.loader.load("index.html")
        #self.write(t.generate(user=self.get_current_user_name()))


class SafeStaticFileHandler(tornado.web.StaticFileHandler, SafeHandler):
    """ Serve static files for logged in users
    """
    pass

class AuthorizedStaticFileHandler(tornado.web.StaticFileHandler, AuthorizedHandler):
    """ Serve static files for authenticated users
    """
    pass
