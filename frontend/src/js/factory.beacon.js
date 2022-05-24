(function() {
    angular.module("App")
    .factory("Beacon", ["$http", function($http) {
        return {
            getBeaconReferences: getBeaconReferences,
            queryBeacon: queryBeacon
        };

        function getBeaconReferences(name, version) {
            return $http.get("https://swefreq.nbis.se/api/beacon-elixir/").then(function(data) {
                let d = data.data.datasets;

		if (version) {
                    for (let i = 0; i < d.length; i++) {
			let dataset = d[i].id;
			if (dataset.indexOf(name) != -1 && dataset.indexOf(version) != -1) {
                            return {
                                "reference": dataset.split(":")[0].substring(0, 6),
                                "datasetId": dataset,
                            };
			}
                    }
		}
		else {
                    let references = [];
                    for (let i = 0; i < d.length; i++) {
			let dataset = d[i].id;
			if (dataset.indexOf(name) !== -1) {
                            references.push(dataset);
			}
                    }
                    let beaconId = "";
                    let highestVer = 0;
                    let reference = "";
                    for (let i = 0; i < references.length; i++) {
                        let ver = parseInt(references[i].split(":")[2]);
                        if (ver > highestVer) {
                            highestVer = ver;
                            reference = references[i].split(":")[0].substring(0, 6);
                            beaconId = references[i];
			}
                    }
                    return {
			"reference": reference,
			"datasetId": beaconId,
                    };
		}
            });
        }

        function queryBeacon(query) {
            return $http.get("https://swefreq.nbis.se/api/beacon-elixir/query", {
                    "params": {
                        "referenceName":   query.chromosome,
                        "start":           query.position - 1, // Beacon is 0-based
                        "alternateBases":  query.allele,
                        "referenceBases":  query.referenceAllele,
                        "datasetIds":      query.beaconInfo.datasetId,
                        "assemblyId":      query.beaconInfo.reference,
                    }
                }
            );
        }
    }]);
})();
