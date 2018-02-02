(function() {
    angular.module("App")
    .factory("TemporaryLink", ["$http", "$cookies", function($http, $cookies) {
        return {
            getTemporary: getTemporary
        };

        function getTemporary(dataset, version) {
            var url = "/api/datasets/" + dataset;
            if (version) {
                url += "/versions/" + version;
            }
            url += "/temporary_link";
            return $http.post(
                    url,
                    $.param({"_xsrf": $cookies.get("_xsrf")})
                );
        }
    }]);
})();
