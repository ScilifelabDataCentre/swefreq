(function() {
    angular.module("App")
    .controller("profileController", ["User", "Countries",
                                function(User, Countries) {
    var localThis = this;

    activate();

    function activate() {
        User.getUser().then(function(data) {
            localThis.user = data;
            setCountry();
        });

        Countries.getCountries().then(function(data) {
            localThis.availableCountries = data;
            setCountry();
        });

        User.getDatasets().then(function(data) {
            localThis.datasets = data;
        });
    }

    function setCountry() {
        if (localThis.user && localThis.availableCountries) {
            var country = localThis.user.country;
            localThis.user.country = { name: country, id: country };
        }
    }
    }]);
})();
