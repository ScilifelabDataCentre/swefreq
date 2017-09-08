(function() {

    /////////////////////////////////////////////////////////////////////////////////////
    // create the module and name it App
    var App = angular.module('App', ['ngRoute', 'ngCookies'])
    var gData = {'userName':'',
                 'email':'',
                 'affiliation':'',
                 'trusted':false,
                 'admin':false}


    App.factory('User', function($http) {
        return {
            get: function() { return $http({url: '/api/users/me'}) }
        };
    });

    App.factory('Dataset', function($http, $q, $location, $sce) {
        var state = {
            state: null,
            get: get,
        };
        return state;
        function get() {
            if (state.state != null) {
                return $q(function(resolve, reject) {
                    resolve(state.state);
                });
            }
            else {
                return $q(function(resolve, reject) {
                    var fail = false;
                    var path = $location.path().split('/');
                    if ( path[1] != 'dataset' ) {
                        fail = true;
                        state.state = "Some strange error 2";
                        reject("Some strange error 1");
                    }
                    else {
                        $http.get('/api/datasets/' + path[2])
                            .then(function(data){
                                var d = data.data;
                                d.version.description = $sce.trustAsHtml( d.version.description );
                                d.version.terms       = $sce.trustAsHtml( d.version.terms );
                                state.state = d;
                                resolve(state.state);
                            },
                            function(data){reject(data)});
                    }
                });
            }
        }
    });

    /////////////////////////////////////////////////////////////////////////////////////
    App.directive('consent', function ($cookies) {
        return {
            scope: {},
            template:
                '<div style="position: relative; z-index: 1000">' +
                '<div style="background: #eee; position: fixed; bottom: 0; left: 0; right: 0; height: 20px" ng-hide="consent()">' +
                '<span style="margin-left: 5px;">This site uses cookies, please see our <a href="https://swefreq.nbis.se/#/privacyPolicy/">privacy policy</a>, ok, I <a href="" ng-click="consent(true)">agree.</a></span>' +
                '<span style="float: right;margin-right: 5px;"><a href="" ng-click="consent(true)">X</a></span>' +
                '</div>' +
                '</div>',
            controller: function ($scope) {
                var _consent = $cookies.get('consent');
                $scope.consent = function (consent) {
                    if (consent === undefined) {
                        return _consent;
                    } else if (consent) {
                        $cookies.put('consent', true);
                        _consent = true;
                    }
                };
            }
        };
    });

    App.directive('myDatasetHeader', function() {
        return {
            restrict: 'E',
            templateUrl: 'static/js/ng-templates/dataset-header.html',
            link: function(scope, element, attrs) {
                scope.name = function() {
                    return attrs.dataset;
                };
            },
        };
    });

    App.directive('myNavbar', ['Dataset', function(Dataset) {
        return {
            restrict: 'E',
            templateUrl: 'static/js/ng-templates/dataset-navbar.html',
            link: function(scope, element, attrs) {
                scope.createUrl = function(subpage) {
                    return '/dataset/' + scope.dataset + '/' + subpage;
                };
                scope.isActive = function(tab) {
                    if ( tab == attrs.tab ) {
                        return 'active';
                    }
                    else {
                        return '';
                    }
                };
                scope.is_admin = false;
                Dataset.get().then(function(data){
                        scope.is_admin    = data.is_admin;
                        scope.dataset     = data.short_name;
                        scope.browser_uri = data.browser_uri;
                    }
                );
            },
        };
    }]);


    App.controller('mainController', function($http, $scope) {
        var localThis = this;
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('homeController', function($http, $scope, $sce) {
        var localThis = this;
        localThis.datasets = [];
        localThis.getDatasets = function(){
            $http.get('/api/datasets').success(function(res){
                var len = res.data.length;
                for (var i = 0; i < len; i++) {
                    d = res.data[i];
                    d.version.description = $sce.trustAsHtml(d.version.description)

                    localThis.datasets.push(d);
                }
            });
        };
        localThis.getDatasets();
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('adminController', function($http, $scope) {
        var localThis = this;
        this.userName = '';
        this.email = '';
        localThis.data = gData;

        this.getUsers = function(){
            $http.get('/api/users/me').success(function(data){
                console.log(data);
                localThis.data.userName = data.user;
                localThis.data.email = data.email;
                localThis.data.trusted = data.trusted;
                localThis.data.has_requested_access = data.has_requested_access;
                localThis.data.admin = data.admin;
                if(data.admin == true){
                    // TODO: Change this to one call that is then filtered into
                    // the two different datasets? Or just filter in the view.
                    // This is currently broken.
                    $http.get('/api/datasets/swegen/users').success(function(data){
                        localThis.data.requests = data;
                    });
                    $http.get('/api/datasets/swegen/users').success(function(data){
                        localThis.data.approvedUsers = data;
                        localThis.data.emails = []
                        for (var idx in data) {
                            var user = data[idx];
                            if (user.newsletter == 1) {
                                localThis.data.emails.push(user['email']);
                            }
                        }
                    });
                };
            });
        };
        this.getUsers();

        this.revokeUser = function(userData){
            $http.get('/api/datasets/swegen/users/' + userData.email + '/revoke').success(function(data){
                localThis.getUsers();
            });
        };

        this.approvedUser = function(userData){
            $http.get('/api/datasets/swegen/users/' + userData.email + '/approve').success(function(data){
                $http.get('/api/datasets/swegen/users/').success(function(data){
                    localThis.getUsers();
                });
            });
        };
    });

     /////////////////////////////////////////////////////////////////////////////////////

    App.controller('dataBeaconController', function($http, $window) {
        var beacon = this;
        beacon.pattern = { 'chromosome': "\\d+" };
        beacon.beacon_info = {};
        $http.get('/api/info').success(function(data) {
            beacon.beacon_info = data;
            beacon.datasets = data['datasets'];
            beacon.dataset = data['datasets'][0]['id'];
            beacon.reference = data['datasets'][0]['reference'];
        });
        beacon.search = function() {
            beacon.color = 'black';
            beacon.response = "Searching...";
            $http.get('/api/query', { 'params': { 'chrom': beacon.chromosome, 'pos': beacon.position - 1, 'allele': beacon.allele, 'referenceAllele': beacon.referenceAllele, 'dataset': beacon.dataset, 'ref': beacon.reference}})
                .then(function (response){
                    if (response.data['response']['exists']) {
                        beacon.response = "Present";
                        beacon.color = 'green';
                    }
                    else {
                        beacon.response = "Absent";
                        beacon.color = "red";
                    }
                },
                function (response){
                    beacon.response="Error";
                    beacon.color = 'black';
                });
        }
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('datasetController', ['$http', '$routeParams', 'User', 'Dataset',
                                function($http, $routeParams, User, Dataset) {
        var localThis = this;
        var short_name = $routeParams["dataset"];

        User.get().then(function(data) {
            localThis.user = data;
        });

        Dataset.get().then(function(data){
            localThis.dataset = data;
        });

        $http.get('/api/datasets/' + short_name + '/sample_set').success(function(data){
            localThis.sample_set = data.sample_set;
            localThis.study = data.study;
        });
    }]);

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('datasetDownloadController', ['$http', '$scope', '$routeParams', '$location', 'User', 'Dataset',
                                function($http, $scope, $routeParams, $location, User, Dataset) {
        var localThis = this;
        var short_name = $routeParams["dataset"];
        localThis.authorization_level = 'loggedout';

        $http.get('/api/countries').success(function(data) {
            localThis.availableCountries = data['countries'];
        });

        User.get().then(function(data) {
            localThis.user = data;
            updateAuthorizationLevel();
        });

        Dataset.get().then(function(data){
            localThis.dataset = data;
            updateAuthorizationLevel();
        });

        $http.get('/api/datasets/' + short_name + '/files').success(function(data){
            localThis.files = data.files;
        });

        function updateAuthorizationLevel () {
            if (!localThis.hasOwnProperty('user') || localThis.user.user == null) {
                localThis.authorization_level = 'loggedout';
            }
            else if (localThis.hasOwnProperty('dataset')) {
                if (! localThis.dataset.has_requested_access)  {
                    localThis.authorization_level = 'need-access';
                }
                else if (! localThis.dataset.has_access) {
                    localThis.authorization_level = 'waits-for-access';
                }
                else if (localThis.dataset.has_access) {
                    localThis.authorization_level = 'has-access';
                }
            }
        };

        localThis.sendRequest = function(valid){
            if (!valid) {
                return;
            }
            $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
            $http({url:'/api/datasets/' + short_name + '/users/' + localThis.user.email + '/request',
                   method:'POST',
                   data:$.param({'email':localThis.user.email,
                                 'userName':localThis.user.userName,
                                 'affiliation':localThis.user.affiliation,
                                 'country': localThis.user.country['name'],
                                 'newsletter': localThis.user.newsletter ? 1 : 0
                        })
                })
                .success(function(data){
                    console.log(data);
                    $location.path("/addedRequest");
                });
        };

        has_already_logged = false;
        localThis.consented = function(){
            console.log("CLICK");
            if (!has_already_logged){
                has_already_logged = true;
                $http.post('/api/datasets/' + short_name + '/log/consent').success(function(data){});
            }
        };

        localThis.downloadData = function(){
            $http.post('/api/datasets/' + short_name + '/log/download').success(function(data){ });
        };
    }]);

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('datasetAdminController', ['$http', '$routeParams', 'User', 'Dataset',
                                function($http, $routeParams, User, Dataset) {
        var localThis = this;
        var short_name = $routeParams["dataset"];

        User.get().then(function(data) {
            localThis.user = data;
        });

        Dataset.get().then(function(data){
            localThis.dataset = data;
        });
    }]);

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('datasetBeaconController', ['$http', '$routeParams', 'User', 'Dataset',
                                function($http, $routeParams, User, Dataset) {
        var localThis = this;
        var short_name = $routeParams["dataset"];

        User.get().then(function(data) {
            localThis.user = data;
        });

        Dataset.get().then(function(data){
            localThis.dataset = data;
        });
    }]);

    ////////////////////////////////////////////////////////////////////////////
    // configure routes
    App.config(function($routeProvider, $locationProvider) {
        $routeProvider
            .when('/',                          { templateUrl: 'static/js/ng-templates/home.html'             })
            .when('/dataBeacon/',               { templateUrl: 'static/js/ng-templates/dataBeacon.html'       })
            .when('/dataset/:dataset',          { templateUrl: 'static/js/ng-templates/dataset.html'          })
            .when('/dataset/:dataset/terms',    { templateUrl: 'static/js/ng-templates/dataset-terms.html'    })
            .when('/dataset/:dataset/download', { templateUrl: 'static/js/ng-templates/dataset-download.html' })
            .when('/dataset/:dataset/beacon',   { templateUrl: 'static/js/ng-templates/dataset-beacon.html'   })
            .when('/dataset/:dataset/admin',    { templateUrl: 'static/js/ng-templates/dataset-admin.html'    })
            .otherwise(                         { templateUrl: 'static/js/ng-templates/404.html'              });

        // Use the HTML5 History API
        $locationProvider.html5Mode(true);
    });
})();
