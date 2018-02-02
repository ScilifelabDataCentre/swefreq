(function() {
    angular.module("App")
    .controller("navbarController", ["$routeParams", "Dataset", "DatasetVersions", function($routeParams, Dataset, DatasetVersions) {
        var localThis = this;
        localThis.isAdmin = false;
        localThis.createUrl = createUrl;

        activate();

        function activate() {
            Dataset.getDataset($routeParams.dataset, $routeParams.version)
                .then(function(data) {
                    localThis.isAdmin     = data.dataset.isAdmin;
                    localThis.dataset     = data.dataset.shortName;
                    localThis.browserUri  = data.dataset.browserUri;
                    localThis.urlBase     = "/dataset/" + localThis.dataset;
                    localThis.thisVersion = data.dataset.version.version;
                    if ($routeParams.version) {
                        localThis.urlBase += "/version/" + $routeParams.version;
                    }

                    DatasetVersions.getDatasetVersions(localThis.dataset)
                        .then(function(data) {
                            for (var i = 0; i < data.length; i++) {
                                if ( data[i].name === localThis.thisVersion ) {
                                    data[i].active = true;
                                    break;
                                }
                            }
                            localThis.versions = data;
                        }
                    );
                }
            );
        }

        function createUrl(subpage, version) {
            if (subpage === "admin") {
                return "/dataset/" + localThis.dataset + "/" + subpage;
            }
            if (subpage === "main") {
                subpage = "";
            }
            if (version) {
                return "/dataset/" + localThis.dataset + "/version/" + version + "/" + subpage;
            }
            return localThis.urlBase + "/" + subpage;
        }
    }]);
})();
