(function() {
    angular.module("App")
    .factory("Log", ["$http", "$cookies", function($http, $cookies) {
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        return {
            consent: consent,
        };

         function consent(dataset, version) {
            return $http.post(
                "/api/datasets/" + dataset + "/log/consent/" + version,
                $.param({"_xsrf": $cookies.get("_xsrf")})
            );
        }
    }]);
})();
