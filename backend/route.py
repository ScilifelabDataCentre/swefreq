import logging
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options

import application
import handlers
import auth
import settings as swefreq_settings
import beacon
#import template


define("port", default=4000, help="run on the given port", type=int)
define("develop", default=False, help="Run in develop environment", type=bool)

# Setup the Tornado Application
tornado_settings = {"debug": False,
            "cookie_secret": swefreq_settings.cookie_secret,
            "login_url": "/login",
            "google_oauth": {
                "key": swefreq_settings.google_key,
                "secret": swefreq_settings.google_secret
            },
            "elixir_oauth": {
                "id": swefreq_settings.elixir["id"],
                "secret": swefreq_settings.elixir["secret"],
                "redirect_uri": swefreq_settings.elixir["redirectUri"],
            },
            "contact_person": 'mats.dahlberg@scilifelab.se',
            "redirect_uri": swefreq_settings.redirect_uri,
            "xsrf_cookies": True,
            "template_path": "templates/",
        }

class Application(tornado.web.Application):
    def __init__(self, settings):
        self.declared_handlers = [
            ## Static handlers
            (r"/static/(.*)",                                                        tornado.web.StaticFileHandler,
                                                                                         {"path": "static/"}),
            (r'/(favicon.ico)',                                                      tornado.web.StaticFileHandler,
                                                                                         {"path": "static/img/"}),
            (r"/release/(?P<dataset>[^\/]+)/(?P<hash>[^\/]+)/(?P<file>[^\/]+)",      handlers.TemporaryStaticNginxFileHandler,
                                                                                         {"path": "/release-files/"}),
            (r"/release/(?P<dataset>[^\/]+)/(?P<file>[^\/]+)",                       handlers.AuthorizedStaticNginxFileHandler,
                                                                                         {"path": "/release-files/"}),
            ## Authentication
            (r"/logout",                                                              auth.ElixirLogoutHandler),
            (r"/elixir/login",                                                        auth.ElixirLoginHandler),
            (r"/elixir/logout",                                                       auth.ElixirLogoutHandler),
            (r"/google/login",                                                        auth.GoogleLoginHandler),
            (r"/google/logout",                                                       auth.GoogleLogoutHandler),
            ## API Methods
            (r"/api/users/elixir_transfer",                                           auth.UpdateUserHandler),
            (r"/api/countries",                                                       application.CountryList),
            (r"/api/users/me",                                                        application.GetUser),
            (r"/api/users/datasets",                                                  application.UserDatasetAccess),
            ### Dataset Api
            (r"/api/datasets",                                                        application.ListDatasets),
            (r"/api/datasets/(?P<dataset>[^\/]+)",                                    application.GetDataset),
            (r"/api/datasets/(?P<dataset>[^\/]+)/log/(?P<event>[^\/]+)/(?P<target>[^\/]+)", application.LogEvent),
            (r"/api/datasets/(?P<dataset>[^\/]+)/logo",                               application.ServeLogo),
            (r"/api/datasets/(?P<dataset>[^\/]+)/files",                              application.DatasetFiles),
            (r"/api/datasets/(?P<dataset>[^\/]+)/collection",                         application.Collection),
            (r"/api/datasets/(?P<dataset>[^\/]+)/users_current",                      application.DatasetUsersCurrent),
            (r"/api/datasets/(?P<dataset>[^\/]+)/users_pending",                      application.DatasetUsersPending),
            (r"/api/datasets/(?P<dataset>[^\/]+)/temporary_link",                     application.GenerateTemporaryLink),
            (r"/api/datasets/(?P<dataset>[^\/]+)/users/[^\/]+/request",               application.RequestAccess),
            (r"/api/datasets/(?P<dataset>[^\/]+)/users/(?P<email>[^\/]+)/approve",    application.ApproveUser),
            (r"/api/datasets/(?P<dataset>[^\/]+)/users/(?P<email>[^\/]+)/revoke",     application.RevokeUser),
            (r"/api/datasets/(?P<dataset>[^\/]+)/versions",                           application.ListDatasetVersions),
            (r"/api/datasets/(?P<dataset>[^\/]+)/versions/(?P<version>[^\/]+)",       application.GetDataset),
            (r"/api/datasets/(?P<dataset>[^\/]+)/versions/(?P<version>[^\/]+)/files", application.DatasetFiles),
            (r"/api/datasets/(?P<dataset>[^\/]+)/versions/(?P<version>[^\/]+)/temporary_link", application.GenerateTemporaryLink),
            ### Beacon API
            (r"/api/beacon/query",                                                    beacon.Query),
            (r"/api/beacon/info",                                                     beacon.Info),
            # # # # # Legacy beacon URIs # # # # #
            (r"/query",                                                               beacon.Query),
            (r"/info",                                                                tornado.web.RedirectHandler,
                                                                                         {"url": "/api/beacon/info"}),
            ## Catch all
            (r"/api/.*",                                                              tornado.web.ErrorHandler,
                                                                                         {"status_code": 404} ),
            (r'().*',                                                                 tornado.web.StaticFileHandler,
                                                                                         {"path": "static/templates/",  "default_filename": "index.html"}),
        ]
        ## Adding developer login handler
        if settings.get('develop', False):
            self.declared_handlers.insert(-1, ("/developer/login", auth.DeveloperLoginHandler))

        # google oauth key
        self.oauth_key = tornado_settings["google_oauth"]["key"]

        # Setup the Tornado Application
        tornado.web.Application.__init__(self, self.declared_handlers, **settings)

if __name__ == '__main__':
    tornado.log.enable_pretty_logging()
    tornado.options.parse_command_line()

    if options.develop:
        tornado_settings['debug'] = True
        tornado_settings['develop'] = True
        logging.getLogger().setLevel(logging.DEBUG)

    # Instantiate Application
    application = Application(tornado_settings)
    application.listen(options.port)

    # Start HTTP Server
    http_server = tornado.httpserver.HTTPServer(application)

    # Get a handle to the instance of IOLoop
    ioloop = tornado.ioloop.IOLoop.instance()

    # Start the IOLoop
    ioloop.start()
