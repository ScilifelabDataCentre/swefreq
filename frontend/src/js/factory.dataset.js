(function() {
    angular.module("App")
    .factory("Dataset", ["$http", "$q", "$sce", function($http, $q, $sce) {
        return {
            getDataset: getDataset
        };

        function getDataset(dataset, version) {
            var state = {dataset: null};
            var defer = $q.defer();

            if (dataset === undefined) {
                return defer.reject("No dataset provided");
            }
            var datasetUri = "/api/datasets/" + dataset;
            if (version) {
                datasetUri += "/versions/" + version;
            }

            $q.all([
                $http.get(datasetUri).then(function(data){
                    var d = data.data;
                    d.version.description = $sce.trustAsHtml( d.version.description );
                    d.version.terms       = $sce.trustAsHtml( d.version.terms );
                    state.dataset = d;
                }),
                $http.get("/api/datasets/" + dataset + "/collection").then(function(data){
                    state.collections = data.data.collections;
                    state.study = data.data.study;

                    var contactName = state.study.contactName;
                    state.study.contactNameUc = contactName.charAt(0).toUpperCase() + contactName.slice(1);
                })
            ]).then(function() {
                    defer.resolve(state);
                },
                function() {
                    var errorMessage = "Can't find dataset " + dataset;
                    if (version) {
                        errorMessage += " version " + version;
                    }
                    defer.reject(errorMessage);
                }
            );

            return defer.promise;
        }
    }]);
})();
