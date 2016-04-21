/* Main webview app, controllers, services */

var iwsApp = angular.module('iws-webview', []);

iwsApp.run()

iwsApp.factory('authService', ['$http', function ($http) {
	var authurl = '/featreq/auth/';
	var status = {
		logged_in: false,
		username: "",
		full_name: "",
		csrf_token: "",
	};
	var refresh = function () {
		$http.get(authurl).then(
			function (response) {
				// Update auth status
				newstatus = response.data;
				status.logged_in = newstatus.logged_in;
				status.username = newstatus.username;
				status.full_name = newstatus.full_name;
				status.csrf_token = newstatus.csrf_token;
				// Update default POST header
				$http.defaults.headers.post['X-CSRFToken'] = newstatus.csrf_token
			},
			function (reason) {
				// Show error message
			}
		);
	};
	var login = function (username, password) {};
	return {
		status: status,
		refresh: refresh,
		login: login
	}
}]);

iwsApp.factory('clientListService', ['authService', '$http', function (authService, $http) {
	var clienturl = '/featreq/client/'
	var getclients = function () {
		return $http.get(clienturl).then(function(response) {
			return response.data.client_list;
		});
	};
	return {
		getclients: getclients
	};
}]);

iwsApp.controller('ClientListController', ['$scope', 'clientListService',
	function ($scope, clientListService) {
		clientListService.getclients().then(function(client_list) {
			$scope.client_list = client_list;
		});
	}
]);

