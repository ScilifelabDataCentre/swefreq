(function() {
    angular.module("App")
    .factory("Beacon", ["$http", function($http) {
        return {
            getBeaconReferences: getBeaconReferences,
            queryBeacon: queryBeacon
        };

        function getBeaconReferences(name) {
            return $http.get("/api/beacon/info").then(function(data) {
                var references = [];
                var d = data.data.datasets;

                for (var i = 0; i < d.length; i++) {
                    var dataset = d[i];
                    if (dataset.id === name) {
                        references.push(dataset.reference);
                    }
                }
                return references;
            });
        }

        function queryBeacon(query) {
            return $http.get("/api/beacon/query", {
                    "params": {
                        "chrom":           query.chromosome,
                        "pos":             query.position - 1, // Beacon is 0-based
                        "allele":          query.allele,
                        "referenceAllele": query.referenceAllele,
                        "dataset":         query.dataset.shortName,
                        "ref":             query.reference
                    }
                }
            );
        }
    }]);
})();
