(function() {
    angular.module("App")
    .controller("datasetAdminController", ["$routeParams", "User", "Dataset", "DatasetUsers",
                                function($routeParams, User, Dataset, DatasetUsers) {
        var localThis = this;
        localThis.revokeUser = revokeUser;
        localThis.approveUser = approveUser;

        activate();

        function activate() {
            getUsers();

            User.getUser().then(function(data) {
                localThis.user = data.data;
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

        function getUsers() {
            DatasetUsers.getUsers( $routeParams.dataset )
                .then(function(data) {
                    localThis.users = data;
                }
            );
        }


        function revokeUser(userData) {
            DatasetUsers.revokeUser(
                    $routeParams.dataset, userData.email
                ).then(function() {
                    getUsers();
                }
            );
        }

        function approveUser(userData){
            DatasetUsers.approveUser(
                    $routeParams.dataset, userData.email
                ).then(function() {
                    getUsers();
                }
            );
        }
    }]);
})();
