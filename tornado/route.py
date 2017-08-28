import logging
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import define, options

import application
import handlers
import settings

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
            (r"/",                               application.Home),
            ## Static handlers
            (r"/static/(home.html)",             tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r"/static/(dataBeacon.html)",       tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r"/static/(privacyPolicy.html)",    tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r"/static/(not_authorized.html)",   tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r"/static/(terms.html)",            tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r"/static/(.*)",                    handlers.SafeStaticFileHandler,             {"path": "static/"}),
            (r'/(favicon.ico)',                  tornado.web.StaticFileHandler,              {"path": "static/"}),
            (r"/javascript/(.*)",                tornado.web.StaticFileHandler,              {"path": "javascript/"}),
            (r"/release/(.*)",                   handlers.AuthorizedStaticNginxFileHanlder,  {"path": "/release-files/"}),
            ## Authentication
            ("/login",                           handlers.LoginHandler),
            ("/logout",                          handlers.LogoutHandler),
            ## API Methods
            ("/logEvent/(?P<sEvent>[^\/]+)",     application.LogEvent),
            ("/getUser",                         application.GetUser),
            ("/getDataset",                      application.GetDataset),
            ("/getApprovedUsers",                application.GetApprovedUsers),
            ("/approveUser/(?P<sEmail>[^\/]+)",  application.ApproveUser),
            ("/query",                           application.Query),
            ("/info",                            application.Info),
            ("/revokeUser/(?P<sEmail>[^\/]+)",   application.RevokeUser),
            ("/getOutstandingRequests",          application.GetOutstandingRequests),
            ("/requestAccess",                   application.RequestAccess),
            ("/country_list",                    application.CountryList),
            ("/dataset_logo/(?P<dataset>[^\/]+)", application.ServeLogo),
            ## Catch all
            (r'.*',                              application.Home),
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
