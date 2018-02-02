import logging
import handlers
from handlers import BaseHandler
import tornado.auth
import urllib.parse
import base64
import uuid
import db
import peewee

class DeveloperLoginHandler(BaseHandler):
    def get(self):
        if not self.get_argument("user", False):
            self.send_error(status_code=403)
        elif not self.get_argument("email", False):
            self.send_error(status_code=403)

        self.set_secure_cookie('user', self.get_argument("user"))
        self.set_secure_cookie('email', self.get_argument("email"))
        self.set_secure_cookie('identity', self.get_argument("email"))
        self.set_secure_cookie('identity_type', 'google')
        self.finish()


class DeveloperLogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()

        redirect = self.get_argument("next", '/')
        self.redirect(redirect)


class ElixirLoginHandler(BaseHandler, tornado.auth.OAuth2Mixin):
    _OAUTH_AUTHORIZE_URL     = "https://perun.elixir-czech.cz/oidc/authorize"
    _OAUTH_ACCESS_TOKEN_URL  = "https://perun.elixir-czech.cz/oidc/token"
    _OAUTH_USERINFO_ENDPOINT = "https://perun.elixir-czech.cz/oidc/userinfo"
    _OAUTH_SETTINGS_KEY      = 'elixir_oauth'

    def _generate_state(self):
        state = uuid.uuid4().hex
        self.set_secure_cookie('state', state)
        return state

    def _check_state(self, state):
        cookie_state = self.get_secure_cookie('state').decode('ascii')
        return state == cookie_state

    async def get(self):
        if self.get_argument("code", False):

            if not self._check_state(self.get_argument('state', 'N/A')):
                # TODO Redirect somewhere?
                logging.error("We're beeing MITM:ed or something ABORT!")
                return

            user_token = await self.get_user_token(self.get_argument('code'))
            user       = await self.get_user(user_token["access_token"])

            extra_login = None
            try: # check if the user is already logged in
                extra_login = self.get_secure_cookie('identity_type').decode('utf-8')

                # Store other login in separate cookies (elixir is main login)
                # This is hardcoded for google right now, as that is the only option
                if extra_login == 'google':
                    google_identity = self.get_secure_cookie('identity').decode('utf-8')
                    self.set_secure_cookie('google_identity', google_identity)

            except AttributeError: # if the user isn't logged in
                pass

            self.set_secure_cookie('access_token', user_token["access_token"])
            self.set_secure_cookie('user', user["name"])
            self.set_secure_cookie('email', user["email"])
            self.set_secure_cookie('identity', user["sub"])
            self.set_secure_cookie('identity_type', 'elixir')

            if extra_login:
                self.set_secure_cookie('identity_type', 'elixir_%s' % extra_login)

            redirect = self.get_secure_cookie("login_redirect")
            self.clear_cookie("login_redirect")
            if redirect is None:
                redirect = '/'
            self.redirect(redirect)

        elif self.get_argument("error", False):
            logging.error("Elixir error: {}".format( self.get_argument("error") ))
            logging.error(" Description: {}".format( self.get_argument("error_description") ))
            # TODO We should do some redirect here I guess

        else:
            self.set_secure_cookie('login_redirect', self.get_argument("next", '/'), 1)
            state = self._generate_state()
            self.authorize_redirect(
                    redirect_uri  = self.settings['elixir_oauth']['redirect_uri'],
                    client_id     = self.settings['elixir_oauth']['id'],
                    scope         = ['openid', 'profile', 'email', 'bona_fide_status'],
                    response_type = 'code',
                    extra_params  = {'state': state}
                )

    async def get_user(self, access_token):
        http = self.get_auth_http_client()

        response = await http.fetch(
                self._OAUTH_USERINFO_ENDPOINT,
                headers = {
                    'Content-Type':  'application/x-www-form-urlencoded',
                    'Authorization': "Bearer {}".format(access_token),
                }
            )

        if response.error:
            logging.error("get_user error: {}".format(response))
            return

        return tornado.escape.json_decode( response.body )

    async def get_user_token(self, code):
        redirect_uri = self.settings['elixir_oauth']['redirect_uri']
        http = self.get_auth_http_client()
        body = urllib.parse.urlencode({
                "redirect_uri": redirect_uri,
                "code": code,
                "grant_type": "authorization_code",
            })

        client_id = self.settings['elixir_oauth']['id']
        secret    = self.settings['elixir_oauth']['secret']

        authorization = base64.b64encode(
                bytes("{}:{}".format(client_id, secret),
                      'ascii' )
            ).decode('ascii')

        response = await http.fetch(
                self._OAUTH_ACCESS_TOKEN_URL,
                method  = "POST",
                body    = body,
                headers = {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Authorization': "Basic {}".format(authorization),
                },
            )

        if response.error:
            logging.error("get_user_token error: {}".format(response))
            return

        return tornado.escape.json_decode( response.body )


class ElixirLogoutHandler(BaseHandler):
    def get(self):
        self.clear_all_cookies()

        redirect = self.get_argument("next", '/')
        self.redirect(redirect)


class GoogleLoginHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
    """
    See http://www.tornadoweb.org/en/stable/auth.html#google for documentation
    on this. Here I have copied the example more or less verbatim.
    """
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument("code", False):
            logging.debug("Requesting user token")
            user_token = yield self.get_authenticated_user(
                redirect_uri=self.application.settings['redirect_uri'],
                code=self.get_argument('code'))

            logging.debug("Requesting user info")
            user = yield self.oauth2_request(
                    "https://www.googleapis.com/plus/v1/people/me",
                    access_token=user_token["access_token"])

            try:
                # Check if there is the user is already in the database.
                # This will generate an exception if the user does not exist, preventing login
                db.User.select().where(db.User.identity == self._get_google_email(user)).get()

                extra_login = None
                try: # check if the user is already logged in
                    extra_login = self.get_secure_cookie('identity_type').decode('utf-8')

                    # Store this login in separate cookies (elixir is main login)
                    # This is hardcoded for elixir right now, as that is the only option
                    if extra_login == 'elixir':
                        google_identity = self._get_google_email(user)
                        self.set_secure_cookie('google_identity', google_identity)

                    self.set_secure_cookie('identity_type', '%s_google' % extra_login)

                except AttributeError: # if the user isn't logged in
                    self.set_secure_cookie('user', user["displayName"])
                    self.set_secure_cookie('access_token', user_token["access_token"])
                    self.set_secure_cookie('email', self._get_google_email(user))
                    self.set_secure_cookie('identity', self._get_google_email(user))
                    self.set_secure_cookie('identity_type', 'google')

            except db.User.DoesNotExist:
                msg = "You have no user information logged in our database, so you may directly log in using elixir without updating."
                self.set_user_msg(msg, "success")

            url = self.get_secure_cookie("login_redirect")
            self.clear_cookie("login_redirect")
            if url is None:
                url = '/'
            self.redirect(url)

        else:
            logging.debug("Redirecting to google for login")
            self.set_secure_cookie('login_redirect', self.get_argument("next", '/'), 1)
            self.authorize_redirect(
                        redirect_uri=self.application.settings['redirect_uri'],
                        client_id=self.application.oauth_key,
                        scope=['profile', 'email'],
                        response_type='code',
                        extra_params={'approval_prompt': 'auto'})

    def _get_google_email(self, user):
        email = ''
        # There can be several emails registered for a user.
        for email in user["emails"]:
            if email.get('type', '') == 'account':
                return email['value']

        return user['emails'][0]['value']


class GoogleLogoutHandler(BaseHandler, tornado.auth.GoogleOAuth2Mixin):
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

        self.clear_all_cookies()

        redirect = self.get_argument("next", '/')
        self.redirect(redirect)


class UpdateUserHandler(handlers.SafeHandler):
    def post(self):
        """
        If a user is logged in to elixir, and also has google login cookies, the
        google users information in the database will be updated with the elixir
        users information.
        """
        # set redirect
        try:
            redirect = self.get_argument("next")
        except tornado.web.MissingArgumentError:
            redirect = self.get_cookie("login_redirect", '/')
            self.clear_cookie("login_redirect")

        try:
            # Double check so that the elixir user isn't already have any credentials
            # in the database.

            elixir_identity = self.get_secure_cookie('user')

            (db.User.select()
                    .join(db.DatasetAccess)
                    .where(
                           db.User.user == db.DatasetAccess.user,
                           db.User.identity == elixir_identity)
                    .get())
            msg = "This elixir account already has its own credentials. Sadly, you will have to contact us directly to merge your accounts."
            self.set_user_msg(msg, "error")
            self.finish({'redirect':'/login'})
            return
        except db.User.DoesNotExist:
            # This is what we want
            pass

        try:
            # Check if we have a google login, will throw an AttributeError
            # if the cookie isn't available
            google_identity = self.get_secure_cookie('google_identity').decode('utf-8')

            # Try to update the google user in the database with the elixir information
            # This throws a peewee.IntegrityError if the elixir account is already in
            # the database
            db.User.update( name = self.get_secure_cookie('user').decode('utf-8'),
                            email = self.get_secure_cookie('email').decode('utf-8'),
                            identity = self.get_secure_cookie('identity').decode('utf-8'),
                            identity_type = 'elixir'
                            ).where( db.User.identity == google_identity ).execute()

            self.set_secure_cookie('identity_type', 'updated')
        except AttributeError:
            # This will happen when we don't have a google cookie
            msg = "You need to log in to a google account to be able to transfer credentials"
            self.set_user_msg(msg, "info")

            self.finish({'redirect':'/login'})
            return
        except peewee.IntegrityError:
            # This will happen if the elixir account is already in the database
            msg = "This elixir account is already in our database, so it can't be used to update another google account."
            self.set_user_msg(msg, "error")
            self.finish({'redirect':'/login'})
            return

        msg = "Your account has been updated! You may now use the site as you used to, using your Elixir account."
        self.set_user_msg(msg, "success")

        self.finish({'redirect':redirect})
