(function() {
    angular.module("App")
    .controller("loginController", ["$location", "$cookies", "User", function($location, $cookies, User) {
        var localThis = this;
        localThis.postTransferForm = postTransferForm;
        activate();

        function activate() {
            var next = $location.search()["next"] || "/";
            if (next != "/") { $cookies.put("login_redirect", next); }
        }

        function postTransferForm(valid) {
            if (!valid) {
                return;
            }
            User.transferAccount().then(function(data) {
                    window.location.replace( data.data.redirect );
                });
        }

    }]);
})();



