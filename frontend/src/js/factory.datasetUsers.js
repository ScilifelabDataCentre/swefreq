(function() {
    angular.module("App")
    .factory("DatasetUsers", ["$http", "$cookies", "$q", function($http, $cookies, $q) {
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        return {
            getUsers: getUsers,
            approveUser: approveUser,
            revokeUser: revokeUser,
            requestAccess: requestAccess,
        };

         function getUsers(dataset) {
            var defer = $q.defer();
            var users = {"pending": [], "current": []};
            $q.all([
                $http.get( "/api/datasets/" + dataset + "/users_pending" )
                    .then(function(data) {
                        users.pending = data.data.data;
                    }
                ),
                $http.get( "/api/datasets/" + dataset + "/users_current" )
                    .then(function(data) {
                        users.current = data.data.data;
                    }
                )
            ]).then(function() {
                defer.resolve(users);
            });
            return defer.promise;
        }

         function approveUser(dataset, email) {
            return $http.post(
                    "/api/datasets/" + dataset + "/users/" + email + "/approve",
                    $.param({"_xsrf": $cookies.get("_xsrf")})
                );
        }

         function revokeUser(dataset, email) {
            return $http.post(
                    "/api/datasets/" + dataset + "/users/" + email + "/revoke",
                    $.param({"_xsrf": $cookies.get("_xsrf")})
                );
        }

         function requestAccess(dataset, user) {
            return $http({url:"/api/datasets/" + dataset + "/users/" + user.email + "/request",
                   method:"POST",
                   data:$.param({
                           "email":       user.email,
                           "userName":    user.userName,
                           "affiliation": user.affiliation,
                           "country":     user.country["name"],
                           "_xsrf":       $cookies.get("_xsrf"),
                           "newsletter":  user.newsletter ? 1 : 0
                        })
                }
            );
        }
    }]);
})();
