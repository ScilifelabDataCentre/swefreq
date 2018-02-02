(function() {
    angular.module("App")
    .factory("Countries", ["$http", function($http) {
        return {
            getCountries: getCountries,
        };

        function getCountries() {
            return $http.get("/api/countries").then(function(data) {
                return data.data.countries;
            });
        }
    }]);
})();
