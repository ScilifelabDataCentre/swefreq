(function() {
    angular.module("App")
    .factory("DatasetList", ["$http", "$sce", function($http, $sce) {
        return {
            getDatasetList: getDatasetList,
        };

        function getDatasetList() {
            return $http.get("/api/datasets").then(function(data) {
                data = data.data.data;
                var len = data.length;
                var datasets = [];

                for (var i = 0; i < len; i++) {
                    var d = data[i];
                    d.version.description = $sce.trustAsHtml(d.version.description);
                    if (d.future) {
                        d.urlbase = "/dataset/" + d.shortName + "/version/" + d.version.version;
                    }
                    else {
                        d.urlbase = "/dataset/" + d.shortName;
                    }

                    datasets.push(d);
                }
                return datasets;
            });
        }
    }]);
})();
