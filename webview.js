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

iwsApp.factory('clientOpenService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	var suffix = '/open/?fields=id,title,prod_area';
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
					title: oreq.req.title,
					prod_area: oreq.req.prod_area
				});
			};
			client.open_list = open_list;
			return client;
		});
	}
	var clearopen = function () {
		client.id = "";
		client.open_list = [];
	}
	return {
		client: client,
		getopen: getopen,
		clearopen: clearopen
	};
}]);

iwsApp.factory('reqDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/req/';
	var req = {};
	var getdetails = function (req_id) {
		return $http.get(baseurl + req_id).then(function (response) {
			newreq = response.data.req;
			req.id = newreq.id;
			req.title = newreq.title;
			req.desc = newreq.desc;
			req.ref_url = newreq.ref_url;
			req.prod_area = newreq.prod_area;
			req.date_cr = new Date(newreq.date_cr).toDateString();
			req.date_up = new Date(newreq.date_up).toDateString();
			req.user_cr = newreq.user_cr;
			req.user_up = newreq.user_up;
			return req;
		});
	};
	var clearreq = function () {
		req.id = "";
		req.title = "";
		req.desc = "";
		req.ref_url = "";
		req.prod_area = "";
		req.date_cr = "";
		req.date_up = "";
		req.user_cr = "";
		req.user_up = "";
	}
	clearreq();
	return {
		req: req,
		getdetails: getdetails,
		clearreq: clearreq
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

iwsApp.controller('ClientOpenController', ['$scope', 'clientOpenService', 'reqDetailService',
	function ($scope, clientOpenService, reqDetailService) {
		$scope.client = clientOpenService.client;
		$scope.$on('client_select', function (event, client_id) {
			if ($scope.tab == 'open') {
				clientOpenService.getopen(client_id);
			};
		});
		$scope.$on('tab_select', function (event, seltab) {
			if (seltab == 'open') {
				clientOpenService.getopen($scope.client_id);
			}
			else {
				clientOpenService.clearopen();
			}
		});
		this.selectreq = function (req_id) {
			$scope.req_id = req_id;
			reqDetailService.getdetails(req_id);
		};
	}
]);

iwsApp.controller('ReqDetailController', ['$scope', 'reqDetailService',
	function ($scope, reqDetailService) {
		$scope.req = reqDetailService.req;
		$scope.$on('client_select', function (event, client_id) {
			reqDetailService.clearreq();
		});
	}
]);

iwsApp.controller('TabController', ['$scope', 
	function ($scope) {
		$scope.tab = 'open';
		this.select = function (seltab) {
			$scope.tab = seltab;
			$scope.$broadcast('tab_select', seltab);
		};
	}
]);

