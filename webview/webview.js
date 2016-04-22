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
	var getdetails = function (client_id) {
		return $http.get(baseurl + client_id).then(function (response) {
			var client = response.data.client;
			client.date_add = new Date(client.date_add);
			client.date_add_str = client.date_add.toDateString();
			return client;
		});
	};
	return {
		getdetails: getdetails
	};
}]);

iwsApp.factory('reqListService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	var openurl = '/open/?fields=id,title,prod_area';
	var closedurl = '/closed/?fields=id,title,prod_area';
	var getopen = function (client_id) {
		// TODO: cache list
		return $http.get(baseurl + client_id + openurl).then(function (response) {
			var open_list = response.data.client.open_list;
			if (open_list) {
				for (var i = open_list.length - 1; i >= 0; i--) {
					// Replace list entry
					open_list[i] = iwsUtil.oreqproc(open_list[i]);
				};
				open_list.sort(
					function (a, b) {
						// Sort by priority if both present, open date (descending) if neither
						// Request with priority always sorted higher than one without
						if (a.priority) {
							if (b.priority) {
								return a.priority - b.priority;
							}
							else {return 1;}
						}
						else {
							if (b.priority) {return -1;}
							else {
								return a.opened_at > b.opened_at ? -1 : a.opened_at < b.opened_at ? 1 : 0;
							}
						}
					}
				);
			}
			return open_list;
		});
	}
	var getclosed = function (client_id) {
		// TODO: cache list
		return $http.get(baseurl + client_id + closedurl).then(function (response) {
			var closed_list = response.data.client.closed_list;
			if (closed_list) {
				for (var i = closed_list.length - 1; i >= 0; i--) {
					// Replace list entry
					closed_list[i] = iwsUtil.creqproc(closed_list[i]);
				};
				closed_list.sort(
					function (a, b) {
						// Sort by closed date, descending
						return a.closed_at > b.closed_at ? -1 : a.closed_at < b.closed_at ? 1 : 0;
					}
				);
			}
			return closed_list;
		});
	}
	return {
		getopen: getopen,
		getclosed: getclosed
	};
}]);

iwsApp.factory('reqDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/req/';
	var getdetails = function (req_id) {
		// TODO: Get open/closed as well
		return $http.get(baseurl + req_id).then(function (response) {
			req = response.data.req;
			// Process dates
			req.date_cr = new Date(req.date_cr);
			req.date_cr_str = req.date_cr.toDateString();
			req.date_up = new Date(req.date_up);
			req.date_up_str = req.date_up.toDateString();
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
		$scope.$on('client_select', function (event, client_id) {
			clientDetailService.getdetails(client_id).then(function (client) {
				$scope.client = client;
			});
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
		var getopen = function (client_id) {
			reqListService.getopen(client_id).then(
				function (open_list) {
					$scope.client.open_list = open_list;
				}
			);
		};
		var getclosed = function (client_id) {
			reqListService.getclosed(client_id).then(
				function (closed_list) {
					$scope.client.closed_list = closed_list;
				}
			);
		};
		$scope.$on('client_select', function (event, client_id) {
			$scope.req_id = {
				open: "",
				closed: ""
			};
			if ($scope.tab == 'open') {
				getopen(client_id);
			}
			else if ($scope.tab == 'closed') {
				getclosed(client_id);
			}
		});
		this.selecttab = function (seltab) {
			if ($scope.tab != seltab) {
				$scope.tab = seltab;
				if ($scope.client_id) {
					if (seltab == 'open') {
						// TODO: cache
						getopen($scope.client_id);
					}
					else if ($scope.tab == 'closed') {
						// TODO: cache
						getclosed($scope.client_id);
					}
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

/* Utility functions */

// TODO: change to prototype instead?
var iwsUtil = {
	oreqproc: function oreqproc(oreq) {
		// Process received data into new object
		newreq = {};
		newreq.priority = oreq.priority;
		newreq.date_tgt = oreq.date_tgt ? new Date(oreq.date_tgt) : null;
		newreq.date_tgt_str = newreq.date_tgt ? newreq.date_tgt.toDateString() : "";
		newreq.opened_at = new Date(oreq.opened_at);
		newreq.opened_at_str = newreq.opened_at ? newreq.opened_at.toDateString() : "";
		newreq.opened_by = oreq.opened_by;
		if (oreq.req) {
			// TODO: add request processing?
			newreq.req = oreq.req;
		}
		return newreq;
	},
	creqproc: function creqproc(creq) {
		// Process received data into new object
		newreq = {};
		newreq.priority = creq.priority;
		newreq.date_tgt = creq.date_tgt ? new Date(creq.date_tgt) : null;
		newreq.date_tgt_str = newreq.date_tgt ? newreq.date_tgt.toDateString() : "";
		newreq.opened_at = new Date(creq.opened_at);
		newreq.opened_at_str = newreq.opened_at ? newreq.opened_at.toDateString() : "";
		newreq.opened_by = creq.opened_by;
		newreq.closed_at = new Date(creq.closed_at);
		newreq.closed_at_str = newreq.closed_at ? newreq.closed_at.toDateString() : "";
		newreq.closed_by = creq.closed_by;
		newreq.status = creq.status;
		newreq.reason = creq.reason;
		if (creq.req) {
			// TODO: add request processing?
			newreq.req = creq.req;
		}
		return newreq;
	}
};
