(function() {
    angular.module("App")
    .factory("DatasetFiles", ["$http", function($http) {
        return {
            getFiles: getFiles,
        };

        function getFiles(dataset, version) {
            var fileUri = "/api/datasets/" + dataset + "/files";
            if ( version ) {
                fileUri = "/api/datasets/" + dataset + "/versions/" + version + "/files";
            }
            return $http.get(fileUri).then(function(data) {
                return data.data.files;
            });
        }
    }]);
})();
