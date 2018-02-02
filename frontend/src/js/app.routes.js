(function() {
    ////////////////////////////////////////////////////////////////////////////
    // configure routes
    angular.module("App")
    .config(["$routeProvider", "$locationProvider", function($routeProvider, $locationProvider) {
        $routeProvider
            .when("/",                                           { templateUrl: "static/templates/ng-templates/home.html"             })
            .when("/login",                                      { templateUrl: "static/templates/ng-templates/login.html"            })
            .when("/profile",                                    { templateUrl: "static/templates/ng-templates/profile.html"          })
            .when("/dataset/:dataset",                           { templateUrl: "static/templates/ng-templates/dataset.html"          })
            .when("/dataset/:dataset/terms",                     { templateUrl: "static/templates/ng-templates/dataset-terms.html"    })
            .when("/dataset/:dataset/download",                  { templateUrl: "static/templates/ng-templates/dataset-download.html" })
            .when("/dataset/:dataset/beacon",                    { templateUrl: "static/templates/ng-templates/dataset-beacon.html"   })
            .when("/dataset/:dataset/admin",                     { templateUrl: "static/templates/ng-templates/dataset-admin.html"    })
            .when("/dataset/:dataset/version/:version",          { templateUrl: "static/templates/ng-templates/dataset.html"          })
            .when("/dataset/:dataset/version/:version/terms",    { templateUrl: "static/templates/ng-templates/dataset-terms.html"    })
            .when("/dataset/:dataset/version/:version/download", { templateUrl: "static/templates/ng-templates/dataset-download.html" })
            .when("/dataset/:dataset/version/:version/beacon",   { templateUrl: "static/templates/ng-templates/dataset-beacon.html"   })
            .otherwise(                                          { templateUrl: "static/templates/ng-templates/404.html"              });

        // Use the HTML5 History API
        $locationProvider.html5Mode(true);
    }]);
})();
