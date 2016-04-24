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

	return {
		status: status,
		refresh: refresh,
		login: login,
		logout: logout
	};

	function refresh () {
		return $http.get(authurl).then(update, failed);
	}

	function login (username, password) {
		return $http.post(authurl, {
			"action": "login",
			"username": username,
			"password": password
		}).then(update, failed);
	}

	function logout () {
		return $http.post(authurl, {
			"action": "logout",
			"username": status.username
		}).then(update, failed);
	}

	function update (response) {
		// TODO: emit login/logout events
		// Update auth status
		status.logged_in = response.data.logged_in;
		status.username = response.data.username;
		status.full_name = response.data.full_name;
		status.csrf_token = response.data.csrf_token;
		// Update default POST header
		$http.defaults.headers.post['X-CSRFToken'] = status.csrf_token;
		return status;
	}

	function failed (reason) {
		// console.log(reason)
		var msg = reason.data || {status_code: reason.status, error: reason.statusText};
		return $q.reject(msg);
	}
}]);

iwsApp.factory('clientListService', ['$http', function ($http) {
	var clienturl = '/featreq/client/';
	var client = {
		list: [],
		id: ""
	};

	return {
		client: client,
		getclients: getclients
	};

	function getclients () {
		return $http.get(clienturl).then(function (response) {
			client_list = response.data.client_list;
			if (client_list) {
				client_list.sort(
					function(a, b) {
						return a.name.localeCompare(b.name);
				});
			}
			client.list = client_list;
			return client_list;
		});
	}
}]);

iwsApp.factory('clientDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/client/';
	return {
		getdetails: getdetails
	};

	function getdetails (client_id) {
		return $http.get(baseurl + client_id).then(function (response) {
			var client = response.data.client;
			client.date_add = new Date(client.date_add);
			return client;
		});
	}
}]);

iwsApp.factory('reqListService', ['$http', '$q', function ($http, $q) {
	var baseurl = '/featreq/client/';
	var openurl = '/open/?fields=id,title,prod_area';
	var closedurl = '/closed/?fields=id,title,prod_area';
	var client = {
		id: "",
		open_list: null,
		closed_list: null
	};
	return {
		client: client,
		getopen: getopen,
		getclosed: getclosed
	};

	function getopen (client_id) {
		if (client_id) {

			if ((client_id == client.id) && (client.open_list !== null)) {
				// Already have list, return (resolved) promise
				return $q.when(client.open_list);
			}

			if (client_id != client.id) {
				// Set new client id
				client.id = client_id;
				// Clear closed list from old client
				client.closed_list = null;
			}

			// Get (promise of) list from server
			// TODO: cache list?
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
				client.open_list = open_list;
				return open_list;
			});
		}
		else {
			// Set new (empty) client id
			client.id = client_id;
			// Clear lists
			client.open_list = null;
			client.closed_list = null;
			// Return (resolved) promise of empty list
			return $q.when(client.open_list);
		}
	}

	function getclosed (client_id) {
		if (client_id) {

			if ((client_id == client.id) && (client.closed_list !== null)) {
				// Already have list, return (resolved) promise
				return $q.when(client.closed_list);
			}

			if (client_id != client.id) {
				// Set new client id
				client.id = client_id;
				// Clear closed list from old client
				client.open_list = null;
			}

			// Get (promise of) list from server
			// TODO: cache list?
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
				client.closed_list = closed_list;
				return closed_list;
			});
		}
		else {
			// Set new (empty) client id
			client.id = client_id;
			// Clear lists
			client.open_list = null;
			client.closed_list = null;
			// Return (resolved) promise of empty list
			return $q.when(client.closed_list);
		}
	}
}]);

iwsApp.factory('reqDetailService', ['$http', function ($http) {
	var baseurl = '/featreq/req/';
	return {
		getdetails: getdetails,
	};

	function getdetails (req_id) {
		// TODO: Get open/closed as well
		return $http.get(baseurl + req_id).then(function (response) {
			req = response.data.req;
			// Process dates
			req.date_cr = new Date(req.date_cr);
			req.date_up = new Date(req.date_up);
			return req;
		});
	}
}]);

iwsApp.controller('HeaderController', ['$rootScope', 'authService', 
	function ($rootScope, authService) {
		var vm = this;
		vm.auth = authService.status;
		vm.logout = logout;
		// TODO: add refresh timer

		function logout () {
			authService.logout().then(
				function (auth) {
					$rootScope.$broadcast('logged_out', auth);
				},
				function (reason) {
					console.log(reason);
				}
			);
		}
	}
]);

iwsApp.controller('LoginController', ['$rootScope', 'authService', 
	function ($rootScope, authService) {

		// Initial state
		var vm = this;
		vm.auth = authService.status;
		vm.login_req = false;
		vm.login_msg = "Retrieving login status...";
		vm.username = "";
		vm.password = "";
		vm.login = login;

		$rootScope.$on('logged_out', function (auth) {
			logged_out();
		});

		// Get initial auth status
		authService.refresh().then(function (auth) {
			if (auth.logged_in) {
				login_success(auth);
			}
			else {
				logged_out();
			}
		});

		function login_success (auth) {
			vm.login_msg = "Logged in";
			$rootScope.$broadcast('login_success', auth);
		}

		function logged_out () {
			vm.login_req = true;
			vm.login_msg = "Please log in";
		}

		function login () {
			vm.login_req = false;
			vm.login_msg = "Logging in...";
			authService.login(vm.username, vm.password).then(
				function (auth) {
					if (auth.logged_in) {
						vm.password = "";
						login_success(auth);
					}
					else {
						vm.password = "";
						vm.login_req = true;
						vm.login_msg = "Login failed";
					}
				},
				function (reason) {
					vm.password = "";
					vm.login_req = true;
					vm.login_msg = reason.error || reason || "Error logging in";
				}
			);
		}
	}
]);

iwsApp.controller('ClientListController', ['$scope', 'clientListService',
	function ($scope, clientListService) {

		var vm = this;
		vm.logged_in = false;
		vm.client = clientListService.client;
		vm.selectclient = selectclient;

		// $scope.client_id = "";

		$scope.$on('login_success', function(event, auth) {
			vm.logged_in = true;
			clientListService.getclients();
		});

		$scope.$on('logged_out', function (event, auth) {
			vm.logged_in = false;
			vm.client_list = [];
			$scope.client_id = "";
		});

		function selectclient (client_id) {
			if (client_id != vm.client.id) {
				vm.client.id = client_id;
				$scope.$broadcast('client_select', client_id);
			}
		}
	}
]);

iwsApp.controller('ClientDetailController', ['$scope', 'clientDetailService', 'clientListService',
	function ($scope, clientDetailService, clientListService) {
		var vm = this;
		vm.client = {};

		$scope.$on('client_select', function (event, client_id) {
			if (client_id) {
				clientDetailService.getdetails(client_id).then(function (client) {
					vm.client = client;
				});
			}
		});
	}
]);

iwsApp.controller('ReqListController', ['$scope', 'reqListService',
	function ($scope, reqListService) {
		var vm = this;
		vm.open_list = null;
		vm.closed_list = null;
		vm.tab = 'open';
		vm.req = {
			open: "",
			closed: ""
		};
		vm.client = reqListService.client;
		vm.selecttab = selecttab;
		vm.selectreq = selectreq;

		$scope.$on('client_select', function (event, client_id) {
			vm.req.open = "";
			vm.req.closed = "";
			if (vm.tab == 'open') {
				reqListService.getopen(client_id);
			}
			else if (vm.tab == 'closed') {
				reqListService.getclosed(client_id);
			}
		});

		function selecttab (seltab) {
			if (vm.tab != seltab) {
				vm.tab = seltab;
				if (vm.client.id) {
					if (seltab == 'open') {
						reqListService.getopen(vm.client.id);
					}
					else if (vm.tab == 'closed') {
						reqListService.getclosed(vm.client.id);
					}
					// Notify of new selection
					selectreq(vm.req[seltab]);
				}
			}
		}

		function selectreq (req_id) {
			if (vm.req[vm.tab] != req_id) {
				vm.req[vm.tab] = req_id;
			}
			$scope.$broadcast('req_select', req_id);
		}

	}
]);

iwsApp.controller('ReqDetailController', ['$scope', 'reqDetailService',
	function ($scope, reqDetailService) {
		var vm = this;
		vm.req = {};

		$scope.$on('client_select', function (event, client_id) {
			vm.req = {};
		});

		$scope.$on('req_select', function (event, req_id) {
			if (!req_id) {
				vm.req = {};
			}
			else if (req_id != vm.req.id) {
				reqDetailService.getdetails(req_id).then(function(req) {
					vm.req = req;
				});
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
		newreq.opened_at = new Date(oreq.opened_at);
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
		newreq.opened_at = new Date(creq.opened_at);
		newreq.opened_by = creq.opened_by;
		newreq.closed_at = new Date(creq.closed_at);
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
