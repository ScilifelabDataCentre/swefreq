import logging
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options

import application
import handlers
import settings
import beacon

define("port", default=4000, help="run on the given port", type=int)
define("develop", default=False, help="Run in develop environment", type=bool)

redirect_uri = settings.redirect_uri

# Setup the Tornado Application
settings = {"debug": False,
            "cookie_secret": settings.cookie_secret,
            "login_url": "/login",
            "google_oauth": {
                "key": settings.google_key,
                "secret": settings.google_secret
            },
            "contact_person": 'mats.dahlberg@scilifelab.se',
            "redirect_uri": redirect_uri
        }

class Application(tornado.web.Application):
    def __init__(self, settings):
        self.declared_handlers = [
            ## Static handlers
            (r"/static/(.*)",                         tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r'/(favicon.ico)',                       tornado.web.StaticFileHandler,              {"path": "static/img/"}),
            (r"/release/(.*)",                        handlers.AuthorizedStaticNginxFileHanlder,  {"path": "/release-files/"}),
            ## Authentication
            ("/login",                                handlers.LoginHandler),
            ("/logout",                               handlers.LogoutHandler),
            ## API Methods
            ("/api/logEvent/(?P<sEvent>[^\/]+)",      application.LogEvent),
            ("/api/getUser",                          application.GetUser),
            ("/api/getDataset",                       application.GetDataset),
            ("/api/requestAccess",                    application.RequestAccess),
            ("/api/country_list",                     application.CountryList),
            ("/api/dataset_logo/(?P<dataset>[^\/]+)", application.ServeLogo),
            ### Beacon API
            ("/api/query",                            beacon.Query),
            ("/api/info",                             beacon.Info),
            # # # # # Legacy beacon URIs # # # # #
            ("/query",                                beacon.Query),
            ("/info",                                 tornado.web.RedirectHandler, {"url": "/api/info"}),
            ### Admin API
            ("/api/getApprovedUsers",                 application.GetApprovedUsers),
            ("/api/approveUser/(?P<sEmail>[^\/]+)",   application.ApproveUser),
            ("/api/revokeUser/(?P<sEmail>[^\/]+)",    application.RevokeUser),
            ("/api/getOutstandingRequests",           application.GetOutstandingRequests),
            ## Catch all
            (r'.*',                                   application.Home),
        ]

        # google oauth key
        self.oauth_key = settings["google_oauth"]["key"]

        # Setup the Tornado Application
        tornado.web.Application.__init__(self, self.declared_handlers, **settings)

if __name__ == '__main__':
    tornado.log.enable_pretty_logging()
    tornado.options.parse_command_line()

    if options.develop:
        settings['debug'] = True
        settings['develop'] = True
        logging.getLogger().setLevel(logging.DEBUG)

    # Instantiate Application
    application = Application(settings)
    application.listen(options.port)

    # Start HTTP Server
    http_server = tornado.httpserver.HTTPServer(application)

    # Get a handle to the instance of IOLoop
    ioloop = tornado.ioloop.IOLoop.instance()

    # Start the IOLoop
    ioloop.start()
