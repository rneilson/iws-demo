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
	var clients = {
		list: [],
		id: ""
	};

	return {
		clients: clients,
		getclients: getclients,
		clearclients: clearclients
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
			clients.list = client_list;
			return client_list;
		});
	}

	function clearclients () {
		clients.list = [];
		clients.id = "";
	}
}]);

iwsApp.factory('clientDetailService', ['$http', '$q', function ($http, $q) {
	var baseurl = '/featreq/client/';
	var fields = ['con_mail', 'con_name', 'name'];
	var client = iwsUtil.emptyobj();

	return {
		client: client,
		getdetails: getdetails,
		updateclient: updateclient,
		addclient: addclient,
		emptyclient: emptyclient
	};

	function getdetails (client_id) {
		return $http.get(baseurl + client_id).then(function (response) {
			var newclient = response.data.client;
			newclient.date_add = new Date(newclient.date_add);
			angular.copy(newclient, client)
			return client;
		});
	}

	function updateclient (update) {
		// Get changed fields
		var upcli = {action: 'update'};
		var changed = false;
		for (var i = fields.length - 1; i >= 0; i--) {
			var field = fields[i];
			if ((iwsUtil.hasprop(update, field)) && (update[field] != client[field])) {
				upcli[field] = update[field];
				changed = true;
			}
		}
		if (changed) {
			return $http.post(baseurl + client.id, upcli)
				.then(updatesuccess, updateerror);
		}
		else {
			// TODO: return client regardless?
			return $q.when(null);
		}
	}

	function addclient (newcli) {
		var addcli = {action: 'create'};
		for (var i = fields.length - 1; i >= 0; i--) {
			var field = fields[i];
			if ((iwsUtil.hasprop(newcli, field)) && newcli[field]) {
				addcli[field] = newcli[field];
			}
		}
		if (!addcli.name) {
			return $q.reject("Name required");
		}
		else {
			return $http.post(baseurl, addcli)
				.then(updatesuccess, updateerror);
		}
	}

	function emptyclient () {
		var newcli = iwsUtil.emptyobj();
		for (var i = fields.length - 1; i >= 0; i--) {
			newcli[fields[i]] = '';
		}
		return newcli;
	}

	function updatesuccess (response) {
		angular.copy(response.data.client, client)
		return client;
	}

	function updateerror (reason) {
		var msg = reason.data || {status_code: reason.status, error: reason.statusText};
		return $q.reject(msg);
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
		vm.clients = clientListService.clients;
		vm.selectclient = selectclient;

		$scope.$on('login_success', function(event, auth) {
			vm.logged_in = true;
			clientListService.getclients();
		});

		$scope.$on('logged_out', function (event, auth) {
			vm.logged_in = false;
			clientListService.clearclients();
		});

		$scope.$on('client_updated', function (event, client) {
			if (client) {
				clientListService.getclients();
				if (client.id != vm.clients.id) {
					selectclient(client.id);
				}
			}
		});

		function selectclient (client_id) {
			if (client_id != vm.clients.id) {
				vm.clients.id = client_id;
				$scope.$broadcast('client_select', client_id);
			}
		}
	}
]);

iwsApp.controller('ClientDetailController', ['$scope', 'clientDetailService',
	function ($scope, clientDetailService) {
		var vm = this;
		vm.client = clientDetailService.client;
		close(); // Shortcut to init edit* props
		vm.edit = edit;
		vm.update = update;
		vm.close = close;

		$scope.$on('client_select', function (event, client_id) {
			if (client_id) {
				close();
				clientDetailService.getdetails(client_id);
			}
		});

		function edit (mode) {
			vm.edit_mode = mode;
			if (mode == 'update') {
				angular.copy(vm.client, vm.edit_cli);
			}
		}

		function update () {
			if (vm.edit_form.$dirty) {
				if (vm.edit_form.$valid) {
					if (vm.edit_mode == 'update') {
						vm.edit_msg = 'Updating...';
						vm.edit_err = '';
						clientDetailService.updateclient(vm.edit_cli).then(
							function (client) {
								close();
								// Emit so client list can be updated
								// TODO: send to service instead?
								$scope.$emit('client_updated', client);
							},
							function (reason) {
								vm.edit_msg = '';
								vm.edit_err = reason.error || reason || 'Update failed';
							}
						);
					}
					else if (vm.edit_mode == 'create') {
						vm.edit_msg = 'Creating...';
						vm.edit_err = '';
						clientDetailService.addclient(vm.edit_cli).then(
							function (client) {
								close();
								// Emit so client list can be updated
								// TODO: send to service instead?
								$scope.$emit('client_updated', client);
							},
							function (reason) {
								vm.edit_msg = '';
								vm.edit_err = reason.error || reason || 'Creation failed';
							}
						);
					}
				}
				else {
					vm.edit_err = 'Please correct the error(s) above';
				}
			}
			else {
				close();
			}
		}

		function close () {
			vm.edit_mode = '';
			vm.edit_msg = '';
			vm.edit_err = '';
			vm.edit_cli = clientDetailService.emptyclient();
		}
	}
]);

iwsApp.controller('ReqListController', ['$scope', 'reqListService',
	function ($scope, reqListService) {
		var vm = this;
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
	},
	emptyobj: function emptyobj() {
		return Object.create(null);
	},
	hasprop: function hasprop(obj, propname) {
		return Object.prototype.hasOwnProperty.call(obj, propname);
	}
};
