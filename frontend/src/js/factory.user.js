(function() {
    angular.module("App")
    .factory("User", ["$http", "$cookies", function($http, $cookies) {
        $http.defaults.headers.post["Content-Type"] = "application/x-www-form-urlencoded";
        return {
            getUser: getUser,
            getDatasets: getDatasets,
            transferAccount: transferAccount,
        };

        function getUser() {
            return $http.get("/api/users/me")
                .then(function(data) {
                    return data.data;
                }
            );
        }

        function getDatasets() {
            return $http.get("/api/users/datasets")
                .then(function(data) {
                    return data.data.data;
                }
            );
        }

        function transferAccount() {
            return $http.post("/api/users/elixir_transfer",
                    $.param({"_xsrf": $cookies.get("_xsrf")})
                );
        }
    }]);
})();
