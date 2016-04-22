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
			client_list = response.data.client_list;
			if (client_list) {
				client_list.sort(
					function(a, b) {
						return a.name.localeCompare(b.name);
				});
			}
			return client_list;
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
			client.id = newclient.id;
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

iwsApp.factory('reqListService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	var openurl = '/open/?fields=id,title,prod_area';
	var closedurl = '/closed/?fields=id,title,prod_area';
	var getopen = function (client_id) {
		return $http.get(baseurl + client_id + openurl).then(function (response) {
			var open_list = response.data.client.open_list;
			if (open_list) {
				open_list.sort(
					function (a, b) {
						return a.priority - b.priority;
					}
				);
			}
			for (var i = 0; i < open_list.length; i++) {
				oreq = open_list[i];
				open_list[i] = {
					priority: oreq.priority,
					date_tgt: new Date(oreq.date_tgt).toDateString(),
					opened_at: new Date(oreq.opened_at).toDateString(),
					opened_by: oreq.opened_by,
					id: oreq.req.id,
					title: oreq.req.title,
					prod_area: oreq.req.prod_area
				};
			};
			return open_list;
		});
	}
	return {
		getopen: getopen,
	};
}]);

iwsApp.factory('reqDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/req/';
	var getdetails = function (req_id) {
		// TODO: Get open/closed as well
		return $http.get(baseurl + req_id).then(function (response) {
			req = response.data.req;
			req.date_cr = new Date(req.date_cr).toDateString();
			req.date_up = new Date(req.date_up).toDateString();
			return req;
		});
	};
	return {
		getdetails: getdetails,
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
			// $scope.client_id = client_list[0].id;
		});
		this.selectclient = function (client_id) {
			if (client_id != $scope.client_id) {
				$scope.client_id = client_id;
				$scope.$broadcast('client_select', client_id);
			}
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

iwsApp.controller('ReqListController', ['$scope', 'reqListService',
	function ($scope, reqListService) {
		$scope.client = {};
		$scope.tab = 'open';
		$scope.req_id = {
			open: "",
			closed: ""
		};
		$scope.$on('client_select', function (event, client_id) {
			if ($scope.tab == 'open') {
				reqListService.getopen(client_id).then(
					function (open_list) {
						$scope.client.open_list = open_list;
					}
				);
			}
			else if ($scope.tab == 'closed') {
				// TODO: closed list
			}
		});
		this.selecttab = function (seltab) {
			if ($scope.tab != seltab) {
				$scope.tab = seltab;
				if (seltab == 'open') {
					reqListService.getopen($scope.client_id);
				}
				else if ($scope.tab == 'closed') {
					// TODO: closed list
				}
				$scope.$broadcast('tab_select', seltab);
			}
		};
		this.selectreq = function (req_id) {
			if ($scope.req_id[$scope.tab] != req_id) {
				$scope.req_id[$scope.tab] = req_id;
				$scope.$broadcast('req_select', req_id);
			}
		};
	}
]);

iwsApp.controller('ReqDetailController', ['$scope', 'reqDetailService',
	function ($scope, reqDetailService) {
		$scope.req = {};
		$scope.$on('client_select', function (event, client_id) {
			$scope.req = {};
		});
		$scope.$on('req_select', function (event, req_id) {
			reqDetailService.getdetails(req_id).then(function(req) {
				$scope.req = req;
			});
		});
		$scope.$on('tab_select', function (event, seltab) {
			req_id = $scope.req_id[seltab];
			if (req_id) {
				reqDetailService.getdetails(req_id).then(function(req) {
					$scope.req = req;
				});
			}
			else {
				$scope.req = {};
			}
		});
	}
]);

