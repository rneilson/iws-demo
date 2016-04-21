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
			return response.data.client_list.sort(
				function(a, b) {
					return a.name.localeCompare(b.name);
			});
		});
	};
	return {
		getclients: getclients
	};
}]);

iwsApp.factory('clientDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	var client = {};
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

iwsApp.factory('clientOpenService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	var suffix = '/open/?fields=id,title';
	var client = {}
	var getopen = function (client_id) {
		return $http.get(baseurl + client_id + suffix).then(function (response) {
			newclient = response.data.client;
			client.id = newclient.id;
			var newlist = newclient.open_list.sort(
				function (a, b) {
					return a.priority - b.priority;
				});
			open_list = []
			for (var i = 0; i < newlist.length; i++) {
				oreq = newlist[i];
				open_list.push({
					priority: oreq.priority,
					date_tgt: new Date(oreq.date_tgt).toDateString(),
					opened_at: new Date(oreq.opened_at).toDateString(),
					opened_by: oreq.opened_by,
					id: oreq.req.id,
					title: oreq.req.title
				});
			};
			client.open_list = open_list;
			return client;
		});
	}
	return {
		client: client,
		getopen: getopen
	};
}]);

iwsApp.controller('AuthController', ['$scope', 'authService', 
	function ($scope, authService) {
		// authService.refresh().then(function(status) {
			// $scope.username = status.username;
		// });
		$scope.status = authService.status;
		// TODO: add refresh timer, login func
	}
]);

iwsApp.controller('ClientListController', ['$scope', 'clientListService',
	function ($scope, clientListService) {
		$scope.client_id = "";
		clientListService.getclients().then(function (client_list) {
			$scope.client_list = client_list;
		});
		this.selectclient = function (client_id) {
			$scope.client_id = client_id;
			$scope.$broadcast('client_select', client_id);
		};
	}
]);

iwsApp.controller('ClientDetailController', ['$scope', 'clientDetailService',
	function ($scope, clientDetailService) {
		$scope.client = clientDetailService.client;
		$scope.$on('client_select', function (event, client_id) {
			clientDetailService.getdetails(client_id);
		});
	}
]);

iwsApp.controller('ClientOpenController', ['$scope', 'clientOpenService',
	function ($scope, clientOpenService) {
		$scope.client = clientOpenService.client;
		$scope.$on('client_select', function (event, client_id) {
			clientOpenService.getopen(client_id);
		});
	}
]);
