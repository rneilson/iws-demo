/* Main webview app, controllers, services */

var iwsApp = angular.module('iws-webview', []);

iwsApp.run()

iwsApp.factory('authService', ['$http', '$q', function ($http, $q) {
	var authurl = '/featreq/auth/';
	var status = {
		logged_in: false,
		username: "",
		full_name: "",
		csrf_token: "",
	};
	var update = function (response) {
		// Update auth status
		status.logged_in = response.data.logged_in;
		status.username = response.data.username;
		status.full_name = response.data.full_name;
		status.csrf_token = response.data.csrf_token;
		// Update default POST header
		$http.defaults.headers.post['X-CSRFToken'] = status.csrf_token;
		return status;
	}
	var failed = function (reason) {
		// TODO: show error message
		return reason.data;
	}
	var refresh = function () {
		return $http.get(authurl).then(update, failed);
	};
	var login = function (username, password) {
		return $http.post(authurl, {
			action: "login",
			username: username,
			password: password
		}).then(update, failed);
	};
	refresh();
	return {
		status: status,
		refresh: refresh,
		login: login
	};
}]);

iwsApp.factory('clientListService', ['authService', '$http', function (authService, $http) {
	var clienturl = '/featreq/client/';
	var getclients = function () {
		return $http.get(clienturl).then(function (response) {
			return response.data.client_list;
		});
	};
	return {
		getclients: getclients
	};
}]);

iwsApp.factory('clientDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	var client = {}
	var getdetails = function (client_id) {
		return $http.get(baseurl + client_id).then(function (response) {
			newclient = response.data.client;
			client.name = newclient.name;
			client.con_name = newclient.con_name;
			client.con_mail = newclient.con_mail;
			client.date_add = new Date(newclient.date_add).toDateString();
			return client;
		});
	};
	return {
		client: client,
		getdetails: getdetails
	};
}]);

iwsApp.factory('selectService', function () {
	return {
		client_id: "",
		req_id: ""
	};
});

iwsApp.controller('AuthController', ['$scope', 'authService', 
	function ($scope, authService) {
		// authService.refresh().then(function(status) {
			// $scope.username = status.username;
		// });
		$scope.status = authService.status;
		// TODO: add refresh timer, login func
	}
]);

iwsApp.controller('ClientListController', ['$scope', 'clientListService', 'clientDetailService',
	function ($scope, clientListService, clientDetailService) {
		clientListService.getclients().then(function (client_list) {
			$scope.client_list = client_list;
		});
		this.selectclient = function (client_id) {
			clientDetailService.getdetails(client_id);
		};
	}
]);

iwsApp.controller('ClientDetailController', ['$scope', 'clientDetailService',
	function ($scope, clientDetailService) {
		$scope.client = clientDetailService.client;
	}
]);
