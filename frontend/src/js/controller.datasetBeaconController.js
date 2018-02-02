(function() {
    angular.module("App")
    .controller("datasetBeaconController", ["$routeParams", "Beacon", "Dataset", "User",
                                function($routeParams, Beacon, Dataset, User) {
        var localThis = this;
        localThis.queryResponses = [];
        localThis.search = search;

        activate();


        function activate() {
            Beacon.getBeaconReferences($routeParams.dataset).then(
                    function(data) {
                        localThis.references = data;
                    }
                );

            User.getUser().then(function(data) {
                localThis.user = data;
            });

            Dataset.getDataset($routeParams.dataset, $routeParams.version)
                .then(function(data) {
                    localThis.dataset = data.dataset;
                },
                function(error) {
                    localThis.error = error;
                }
            );
        }

        function search() {
            Beacon.queryBeacon(localThis)
                .then(function(response) {
                    var d = response.data;
                    d.query.position += 1; // Beacon is 0-based
                    d.response.state = d.response.exists ? "Present" : "Absent";
                    localThis.queryResponses.push(d);
                },
                function() {
                    localThis.queryResponses.push({
                        "response": { "state": "Error" },
                        "query": {
                            "chromosome":      localThis.chromosome,
                            "position":        localThis.position,
                            "allele":          localThis.allele,
                            "referenceAllele": localThis.referenceAllele,
                            "reference":       localThis.reference
                        }
                    });
                }
            );
        }
    }]);
})();
