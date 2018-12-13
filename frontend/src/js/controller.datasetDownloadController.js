(function() {
    angular.module("App")
    .controller("datasetDownloadController", ["$location", "$http", "$routeParams", "clipboard", "User", "Dataset", "DatasetUsers", "Log", "DatasetFiles", "TemporaryLink", "Countries",
                                function($location, $http, $routeParams, clipboard, User, Dataset, DatasetUsers, Log, DatasetFiles, TemporaryLink, Countries) {
        var localThis                 = this;
        var dataset                   = $routeParams.dataset;
        localThis.authorizationLevel  = "logged_out";
        localThis.sendRequest         = sendRequest;
        localThis.consented           = consented;
        localThis.createTemporaryLink = createTemporaryLink;
        localThis.copyLink            = copyLink;
        localThis.canCopy             = clipboard.supported;
        localThis.dataContactIsEmail  = dataContactIsEmail;

        localThis.host = $location.protocol() + "://" + $location.host();

        activate();

        function activate() {
            localThis.hasFiles = $routeParams.dataset != "ACpop"; // Fulhack
            Countries.getCountries().then(function(data) {
                localThis.availableCountries = data;
            });

            User.getUser().then(function(data) {
                localThis.user = data;
                updateAuthorizationLevel();
            });

            Dataset.getDataset($routeParams.dataset, $routeParams.version)
                .then(function(data) {
                    localThis.dataset = data.dataset;
                    updateAuthorizationLevel();
                },
                function(error) {
                    localThis.error = error;
                }
            );

            DatasetFiles.getFiles($routeParams.dataset, $routeParams.version)
                .then(function(data) {
                    localThis.files = data;
                }
            );
        }

        function updateAuthorizationLevel() {
            if (!localThis.hasOwnProperty("user") || localThis.user.user == null) {
                localThis.authorizationLevel = "logged_out";
            }
            else if (localThis.hasOwnProperty("dataset")) {
                localThis.authorizationLevel = localThis.dataset.authorizationLevel;
            }
        }

        function sendRequest(valid) {
            if (!valid) {
                return;
            }
            DatasetUsers.requestAccess(dataset, localThis.user)
                .then(function() {
                    localThis.authorizationLevel = "thank_you";
                }
            );
        }

        var hasAlreadyLogged = false;
        function consented() {
            if (!hasAlreadyLogged){
                hasAlreadyLogged = true;
                Log.consent(dataset, localThis.dataset.version.version);
            }
        }

        function createTemporaryLink() {
            TemporaryLink.getTemporary($routeParams.dataset, $routeParams.version).success(function(data) {
                localThis.temporaries = true;
                for (let file of localThis.files) {
                    file.tempUrl   = localThis.host
                                   + file["dirname"] + "/"
                                   + data.hash       + "/"
                                   + file["name"];
                    file.expiresOn = data.expiresOn;
                }
            });
        }

        function copyLink(link) {
            clipboard.copyText(link);
        }

        function dataContactIsEmail() {
            return localThis.hasOwnProperty("dataset") &&
                    localThis.dataset.version.dataContactLink.indexOf("@") > -1;
        }
    }]);
})();
