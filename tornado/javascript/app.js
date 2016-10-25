(function() {

    /////////////////////////////////////////////////////////////////////////////////////
    // create the module and name it App
    var App = angular.module('App', ['ngRoute', 'ngCookies'])
    var gData = {'userName':'',
                 'email':'',
                 'affiliation':'',
                 'trusted':false,
                 'admin':false}

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


    App.controller('mainController', function($http, $scope) {
        var localThis = this;
        localThis.data = gData;

        this.getUsers = function(){
            $http.get('/getUser').success(function(data){
                console.log(data);
                localThis.data.userName = data.user;
                localThis.data.email = data.email;
                localThis.data.trusted = data.trusted;
                localThis.data.isInDatabase = data.isInDatabase;
                localThis.data.admin = data.admin;
            });
        };
        this.getUsers();
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('adminController', function($http, $scope) {
        var localThis = this;
        this.userName = '';
        this.email = '';
        localThis.data = gData;

        this.getUsers = function(){
            $http.get('/getUser').success(function(data){
                console.log(data);
                localThis.data.userName = data.user;
                localThis.data.email = data.email;
                localThis.data.trusted = data.trusted;
                localThis.data.isInDatabase = data.isInDatabase;
                localThis.data.admin = data.admin;
                if(data.admin == true){
                    $http.get('/getOutstandingRequests').success(function(data){
                        localThis.data.requests = data;
                    });
                    $http.get('/getApprovedUsers').success(function(data){
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

        this.denyUser = function(userData){
            $http.get('/denyUser/' + userData.email).success(function(data){
                localThis.getUsers();
            });
        };

        this.deleteUser = function(userData){
            $http.get('/deleteUser/' + userData.email).success(function(data){
                localThis.getUsers();
            });
        };

        this.approvedUser = function(userData){
            $http.get('/approveUser/' + userData.email).success(function(data){
                $http.get('/getOutstandingRequests').success(function(data){
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
        $http.get('/info').success(function(data) {
            beacon.beacon_info = data;
            beacon.datasets = data['datasets'];
            beacon.dataset = data['datasets'][0]['id'];
            beacon.reference = data['datasets'][0]['reference'];
        });
        beacon.search = function() {
            beacon.color = 'black';
            beacon.response = "Searching...";
            $http.get('query', { 'params': { 'chrom': beacon.chromosome, 'pos': beacon.position, 'allele': beacon.allele, 'dataset': beacon.dataset, 'ref': beacon.reference}})
                .then(function (response){
                    if (response.data['response']['exists']) {
                        beacon.response = "Yes";
                        beacon.color = 'green';
                    }
                    else {
                        beacon.response = "No";
                        beacon.color = "red";
                    }
                },
                function (response){
                    beacon.response="ERROR";
                });
        }
    });

     /////////////////////////////////////////////////////////////////////////////////////

    App.controller('downloadDataController', function($http, $scope) {
        this.lChecked = true;
        var localThis = this;
        localThis.data = gData;
        this.isChecked = function(){
            if(localThis.lChecked){
                $http.get('/logEvent/consent').success(function(data){
                    console.log('Consented');
                });
            }
            localThis.lChecked = false;
            localThis.checked = true;
        };

        this.downloadData = function(){
            $http.get('/logEvent/download').success(function(data){
                console.log("Downloading")
            });
        };
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('exacBrowserController', function($http, $scope) {
        var localThis = this;
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('requestController', function($http, $scope, $location) {
        var localThis = this;
        localThis.data = gData;
        localThis.data.newsletter = true;
        $http.get('/country_list').success(function(data) {
            localThis.data['availableCountries'] = data['countries'];
        });

        this.sendRequest = function(valid){
            if (!valid) {
                return;
            }
            $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
            $http({url:'/requestAccess',
                   method:'POST',
                   data:$.param({'email':localThis.data.email,
                                 'userName':localThis.data.userName,
                                 'affiliation':localThis.data.affiliation,
                                 'country': localThis.data.country['name'],
                                 'newsletter': localThis.data.newsletter ? 1 : 0
                        })
                })
                .success(function(data){
                    console.log(data);
                    $location.path("/addedRequest");
                });
        };
    });

    /////////////////////////////////////////////////////////////////////////////////////

    App.controller('addedRequestController', function($http, $scope) {
        var localThis = this;
    });

    ////////////////////////////////////////////////////////////////////////////
    // configure routes
    App.config(function($routeProvider) {
        $routeProvider
        // Read only view
            .when('/', {
                templateUrl : 'static/home.html'
            })
        // Data beacon
            .when('/dataBeacon/', {
                templateUrl : 'static/dataBeacon.html'
            })
        // Data Download
            .when('/downloadData/', {
                templateUrl : 'static/downloadData.html'
            })
        // Request Access
            .when('/requestAccess/', {
                templateUrl : 'static/requestAccess.html'
            })
        // Request Access Sent
            .when('/addedRequest/', {
                templateUrl : 'static/addedRequest.html'
            })
        // ExAC Browser
            .when('/exacBrowser/', {
                templateUrl : 'static/exacBrowser.html'
            })
        // Privacy Policy
            .when('/privacyPolicy/', {
                templateUrl : 'static/privacyPolicy.html'
            })
        // Admin interface
            .when('/admin/', {
                templateUrl : 'static/admin.html'
            })
        // About
            .when('/about/', {
                templateUrl : 'static/about.html'
            })
        // Terms
            .when('/terms/', {
                templateUrl : 'static/terms.html'
            })
    });
})();

