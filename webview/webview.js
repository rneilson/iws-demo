/* Main webview app, controllers, services */

var iwsApp = angular.module('iws-webview', []);

iwsApp.run()


/***************
    SERVICES
***************/

iwsApp.factory('authService', ['$http', '$q', '$rootScope', function ($http, $q, $rootScope) {
	var authurl = '/featreq/auth/';
	var status = {
		logged_in: false,
		username: "",
		full_name: "",
		csrf_token: "",
		session_expiry: null,
		err_msg: ""
	};

	$rootScope.$on('auth_expired', function (event, msg) {
		if (status.logged_in) {
			status.logged_in = false;
			status.err_msg = msg;
			console.log(msg);
			refresh();
		}
	});

	return {
		status: status,
		refresh: refresh,
		login: login,
		logout: logout
	};

	function refresh () {
		return $http.get(authurl)
		.then(update)
		.catch(failed);
	}

	function login (username, password) {
		// status.err_msg = '';
		return $http.post(authurl, {
			"action": "login",
			"username": username,
			"password": password
		})
		.then(update)
		.catch(failed);
	}

	function logout () {
		return $http.post(authurl, {
			"action": "logout",
			"username": status.username
		}).then(update)
		.catch(failed);
		// .catch(expired)
	}

	function update (response) {
		// Update auth status
		var newstatus = response.data;
		status.logged_in = newstatus.logged_in;
		status.username = newstatus.username;
		status.full_name = newstatus.full_name;
		status.csrf_token = newstatus.csrf_token;
		status.session_expiry = newstatus.session_expiry ? new Date(newstatus.session_expiry) : null;
		// Update default POST header
		$http.defaults.headers.post['X-CSRFToken'] = status.csrf_token;
		// Emit login/logout events
		if (status.logged_in) {
			status.err_msg = '';
			$rootScope.$broadcast('login_success', status);
		}
		else {
			$rootScope.$broadcast('logged_out', status);
		}
		return status;
	}

	function failed (reason) {
		// Now handled by interceptor
		// var msg = ((reason.data) && (reason.data.error)) ? reason.data : {status_code: reason.status, error: reason.statusText};

		status.err_msg = "Error: " + (reason.error || "Authentication failure");
		console.log("Authentication error: " + reason.error);

		return $q.reject(reason);
	}
}]);

iwsApp.factory('errorInterceptor', ['$q', '$rootScope', function ($q, $rootScope) {

	return {responseError: errorcheck};

	function errorcheck (reason) {

		var err;
		if (reason.headers('content-type') == 'application/json') {
			err = reason.data;
		}
		else {
			err = {status_code: reason.status, error: reason.statusText};
		}
		if (err.status_code === 403) {
			// If session expired, send auth expired event so authService can send logged_out event if req'd
			if ((err.error) && (err.error.search(/expired/i) != -1)) {
				$rootScope.$emit('auth_expired', err.error);
			}
		}
		if (err.status_code === -1) {
			err.error = 'Connection error';
		}
		// console.log(reason);
		// Pass along rejection regardless
		return $q.reject(err);
	}
}]);

iwsApp.config(['$httpProvider',function($httpProvider) {
	$httpProvider.interceptors.push('errorInterceptor');
}]);

iwsApp.factory('clientListService', ['$http', function ($http) {
	var clienturl = '/featreq/client/';
	var clients = iwsUtil.emptyobj();
	var clients_byid = null;
	clearclients();

	return {
		clients: clients,
		getclients: getclients,
		getclientbyid: getclientbyid,
		getclientname: getclientname,
		clearclients: clearclients
	};

	function getclients () {
		return $http.get(clienturl).then(function (response) {
			var client_list = response.data.client_list;
			if (client_list) {
				client_list.sort(
					function(a, b) {
						return a.name.localeCompare(b.name);
				});
			}
			clients.list = client_list;

			clients_byid = iwsUtil.emptyobj();
			var total_open = 0;
			var total_closed = 0;

			for (var i = 0, len = client_list.length; i < len; i++) {
				var cli = client_list[i];
				total_open += cli.open_count;
				total_closed += cli.closed_count;
				clients_byid[cli.id] = cli;
			}
			clients.open = total_open;
			clients.closed = total_closed;
			return client_list;
		});
	}

	function getclientbyid (client_id) {
		if (client_id in clients_byid) {
			return clients_byid[client_id];
		}
		else {
			return null;
		}
	}

	function getclientname (client_id) {
		var use_id = (client_id) ? client_id : clients.id;
		var use_cl = getclientbyid(use_id);
		if (use_cl) {
			return use_cl.name;
		}
		else {
			return '';
		}
	}

	function clearclients () {
		clients.list = [];
		clients.id = "";
		clients.open = 0;
		clients.closed = 0;
		clients_byid = iwsUtil.emptyobj();
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
		if ((client_id) && (client_id != '_all')) {
			return $http.get(baseurl + client_id).then(function (response) {
				var newclient = response.data.client;
				newclient.date_add = new Date(newclient.date_add);
				angular.copy(newclient, client)
				return client;
			});
		}
		else {
			var newclient = emptyclient(true);
			angular.copy(newclient, client);
			return $q.when(client);
		}
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
				.then(updatesuccess);
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
				.then(updatesuccess);
		}
	}

	function emptyclient (full) {
		var newcli = iwsUtil.emptyobj();
		if (full) {
			newcli.id = '';
		}
		for (var i = fields.length - 1; i >= 0; i--) {
			newcli[fields[i]] = '';
		}
		if (full) {
			newcli.date_add = null;
		}
		return newcli;
	}

	function updatesuccess (response) {
		angular.copy(response.data.client, client)
		return client;
	}

	function updateerror (reason) {
		// var msg = reason.data || {status_code: reason.status, error: reason.statusText};
		return $q.reject(reason.error);
	}
}]);

iwsApp.factory('reqListService', ['$http', '$q', function ($http, $q) {
	var baseurl = '/featreq/client/';
	var allurl = '/featreq/req';
	var reqfields = ['id', 'title', 'prod_area'];
	var openurl = '/open/?fields=' + reqfields.join(',');
	var closedurl = '/closed/?fields=' + reqfields.join(',');
	var allopenurl = allurl + openurl;
	var allclosedurl = allurl + closedurl;
	var client = {
		id: "",
		open_list: null,
		closed_list: null
	};
	return {
		client: client,
		getopen: getopen,
		refopen: refopen,
		getclosed: getclosed,
		refclosed: refclosed,
		updatereq: updatereq
	};

	function getopen (client_id) {
		if (client_id) {

			if ((client_id == client.id) && (client.open_list !== null)) {
				// Already have list, no forced refresh, return (resolved) promise
				return $q.when(client.open_list);
			}

			if (client_id != client.id) {
				// Set new client id
				client.id = client_id;
				// Clear closed list from old client
				client.closed_list = null;
			}

			return refopen();
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

	function refopen () {
		// Get (promise of) list from server
		// TODO: cache list?
		if (client.id == '_all') {
			return $http.get(allopenurl).then(function (response) {
				var req_list = response.data.req_list;
				var open_list = [];
				// We need to pull the openreqs from each req, and invert parentage
				for (var i = 0, len_i = req_list.length; i < len_i; i++) {
					var req = req_list[i];
					var oreq_list = req.open_list;
					delete req.open_list;
					// Now convert each openreq and add to the list
					for (var j = 0, len_j = oreq_list.length; j < len_j; j++) {
						var oreq = oreq_list[j];
						oreq.req = req;
						open_list.push(iwsUtil.oreqproc(oreq));
					}
				}
				if (open_list) {
					open_list.sort(sortopen);
				}
				client.open_list = open_list;
				return open_list;
			});
		}

		return $http.get(baseurl + client.id + openurl).then(function (response) {
			var open_list = response.data.client.open_list;
			if (open_list) {
				for (var i = open_list.length - 1; i >= 0; i--) {
					// Replace list entry
					open_list[i] = iwsUtil.oreqproc(open_list[i]);
				};
				open_list.sort(sortopen);
			}
			client.open_list = open_list;
			return open_list;
		});
	}

	function getclosed (client_id) {
		if (client_id) {

			if ((client_id == client.id) && (client.closed_list !== null)) {
				// Already have list, no forced refresh, return (resolved) promise
				return $q.when(client.closed_list);
			}

			if (client_id != client.id) {
				// Set new client id
				client.id = client_id;
				// Clear closed list from old client
				client.open_list = null;
			}

			return refclosed();
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

	function refclosed () {
		// Get (promise of) list from server
		// TODO: cache list?
		if (client.id == '_all') {
			return $http.get(allclosedurl).then(function (response) {
				var req_list = response.data.req_list;
				var closed_list = [];
				if (req_list) {
					// We need to pull the closedreqs from each req, and invert parentage
					for (var i = 0, len_i = req_list.length; i < len_i; i++) {
						var req = req_list[i];
						var creq_list = req.closed_list;
						delete req.closed_list;
						// Now convert each closedreq and add to the list
						for (var j = 0, len_j = creq_list.length; j < len_j; j++) {
							var creq = creq_list[j];
							creq.req = req;
							closed_list.push(iwsUtil.creqproc(creq));
						}
					}
				}
				if (closed_list) {
					closed_list.sort(sortclosed);
				}
				client.closed_list = closed_list;
				return closed_list;
			});
		}

		return $http.get(baseurl + client.id + closedurl).then(function (response) {
			var closed_list = response.data.client.closed_list;
			if (closed_list) {
				for (var i = closed_list.length - 1; i >= 0; i--) {
					// Replace list entry
					closed_list[i] = iwsUtil.creqproc(closed_list[i]);
				};
				closed_list.sort(sortclosed);
			}
			client.closed_list = closed_list;
			return closed_list;
		});
	}

	function updatereq (req) {
		// Assumes update to request in open list
		if (client.open_list) {
			for (var i = client.open_list.length - 1; i >= 0; i--) {
				var oreq = client.open_list[i];
				if (oreq.req.id == req.id) {
					// Have to create new outer object so watching controller(s) will pick it up
					var neworeq = angular.copy(oreq);
					for (var j = 0; j < reqfields.length; j++) {
						neworeq.req[reqfields[j]] = req[reqfields[j]];
					}
					client.open_list[i] = neworeq;
				}
			}
		}
	}

	function sortopen (a, b) {
		// Sort by priority, then target date, then open date
		// Request with priority always sorted higher than one without
		// Dates sorted earliest-first
		var comp = 0;

		// First sort by priorities
		if (a.priority) {
			if (b.priority) {
				comp = a.priority - b.priority;
			}
			else {
				comp = -1;
			}
		}
		else if (b.priority) {
			comp = 1;
		}
		if (comp != 0) {
			return comp;
		}

		// Next sort by target dates
		if (a.date_tgt) {
			if (b.date_tgt) {
				comp = a.date_tgt < b.date_tgt ? -1 : a.date_tgt > b.date_tgt ? 1 : 0;
			}
			else {
				comp = -1;
			}
		}
		else if (b.date_tgt) {
			comp = 1;
		}
		if (comp != 0) {
			return comp;
		}

		// Finally sort by open date/time
		return a.opened_at < b.opened_at ? -1 : a.opened_at > b.opened_at ? 1 : 0;
	}

	function sortclosed (a, b) {
		// Sort by closed date, latest-first
		return a.closed_at > b.closed_at ? -1 : a.closed_at < b.closed_at ? 1 : 0;
	}

}]);

iwsApp.factory('reqDetailService', ['$http', '$q', function ($http, $q) {
	var baseurl = '/featreq/req/';
	var exturl = '/all/';
	var fields = ['prod_area', 'ref_url', 'desc', 'title', 'id'];
	var upfields = ['prod_area', 'ref_url', 'title'];
	var extra = ['user_up', 'date_up', 'user_cr', 'date_cr'];
	var detail = {
		req: emptyreq(),
		open: [],
		closed: []
	};

	return {
		detail: detail,
		getdetails: getdetails,
		addreq: addreq,
		updatereq: updatereq,
		updateopen: updateopen,
		closereq: closereq,
		emptyreq: emptyreq,
		clearreq: clearreq
	};

	function getdetails (req_id) {
		if (req_id == detail.req.id) {
			return $q.when(detail);
		}
		var reqdetails = {
			req: $http.get(baseurl + req_id).then(procreq),
			lists: $http.get(baseurl + req_id + exturl).then(proclists)
		};
		return $q.all(reqdetails).then(function() {
			return detail;
		});
	}

	function addreq (req, oreq) {
		// Create request bodies
		var addreq = {action: 'create'};
		angular.extend(addreq, req);

		var openreq = {action: 'open'};
		angular.extend(openreq, oreq);

		var newdetail = iwsUtil.emptyobj();

		// First create featreq, then open for client
		return $http.post(baseurl, addreq)
			.then(function(response) {
				newdetail.req = response.data.req;
				return $http.post(baseurl + newdetail.req.id + exturl, openreq)
			})
			.then(function(response) {
				var req = response.data.req;
				newdetail.open = req.open_list;
				newdetail.closed = req.closed_list;
				return newdetail;
			})
			.then(function(newdetail) {
				detail.req = newdetail.req;
				detail.open = newdetail.open;
				detail.closed = newdetail.closed;
				return detail;
			});
	}

	function updatereq (update) {
		// Get changed fields
		var upreq = {action: 'update'};
		var changed = false;

		// Check/update normal fields
		for (var i = upfields.length - 1; i >= 0; i--) {
			var field = upfields[i];
			if ((iwsUtil.hasprop(update, field)) && (update[field] != detail.req[field])) {
				upreq[field] = update[field];
				changed = true;
			}
		}
		if (update.desc) {
			upreq.desc = update.desc;
			changed = true;
		}

		if (changed) {
			return $http.post(baseurl + detail.req.id, upreq)
				.then(reqsuccess);
		}
		else {
			// TODO: return req regardless?
			return $q.when(null);
		}
	}

	function updateopen (oreq) {
		var update = {action: 'update'};
		var changed = false;
		// Ensure client_id is present
		if (!oreq.client_id) {
			return $q.reject('Missing required client_id');
		}
		update.client_id = oreq.client_id;
		if ('priority' in oreq) {
			update.priority = oreq.priority;
			changed = true;
		}
		if ('date_tgt' in oreq) {
			update.date_tgt = oreq.date_tgt;
			changed = true;
		}

		if (changed) {
			return $http.post(baseurl + detail.req.id + exturl, update)
				.then(listsuccess);
		}
		else {
			// TODO: return details anyways?
			return $q.when(null);
		}
	}

	function closereq (oreq) {
		var update = {action: 'close'};
		// Ensure required arguments
		if ((!oreq.status) || (!oreq.reason)) {
			return $q.reject('Missing required fields');
		}
		// client_id is optional
		if (oreq.client_id) {
			update.client_id = oreq.client_id;
		}
		update.status = oreq.status;
		update.reason = oreq.reason;

		return $http.post(baseurl + detail.req.id + exturl, update)
			.then(listsuccess);
	}

	function emptyreq () {
		var newreq = iwsUtil.emptyobj();
		for (var i = fields.length - 1; i >= 0; i--) {
			newreq[fields[i]] = '';
		}
		return newreq;
	}

	function clearreq () {
		detail.req = emptyreq();
		detail.open = [];
		detail.closed = [];
	}

	function procreq (response) {
		var newreq = response.data.req;
		// Process dates
		newreq.date_cr = new Date(newreq.date_cr);
		newreq.date_up = new Date(newreq.date_up);
		detail.req = newreq;
		return newreq;
	}

	function proclists (response) {
		var open_list = response.data.req.open_list;
		if (open_list) {
			for (var i = open_list.length - 1; i >= 0; i--) {
				// Replace list entry
				open_list[i] = iwsUtil.oreqproc(open_list[i]);
			}
		}
		var closed_list = response.data.req.closed_list;
		if (closed_list) {
			for (var i = closed_list.length - 1; i >= 0; i--) {
				// Replace list entry
				closed_list[i] = iwsUtil.creqproc(closed_list[i]);
			}
		}
		detail.open = open_list;
		detail.closed = closed_list;
		return {
			open: open_list,
			closed: closed_list
		};
	}

	function reqsuccess (response) {
		detail.req = response.data.req;
		return detail;
	}

	function listsuccess (response) {
		var req = response.data.req;
		detail.open = req.open_list;
		detail.closed = req.closed_list;
		return detail;
	}

}]);


/******************
    CONTROLLERS
******************/

iwsApp.controller('HeaderController', ['$rootScope', 'authService', 
	function ($rootScope, authService) {
		var vm = this;
		vm.auth = authService.status;
		vm.logout = logout;
		// TODO: add refresh timer

		function logout () {
			authService.logout()
			.catch(function (reason) {
				console.log(reason);
			});
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

		$rootScope.$on('logged_out', function (event, auth) {
			logged_out();
		});

		$rootScope.$on('login_success', function (event, auth) {
			login_success(auth);
		});

		// Get initial auth status
		authService.refresh()
		.catch(logged_out);

		function login_success (auth) {
			vm.username = auth.username;
			vm.password = "";
			vm.login_form.$setPristine();
			vm.login_req = false;
			vm.login_msg = "Logged in";
		}

		function logged_out () {
			vm.password = "";
			vm.login_form.$setPristine();
			vm.login_req = true;
			vm.login_msg = "Please log in";
		}

		function login () {
			vm.login_req = false;
			vm.login_msg = "Logging in...";
			authService.login(vm.username, vm.password)
			.catch(logged_out);
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
			$scope.$broadcast('client_select', '');
		});

		$scope.$on('client_updated', function (event, client) {
			if (client) {
				clientListService.getclients();
				if (client.id != vm.clients.id) {
					selectclient(client.id);
				}
			}
		});

		$scope.$on('oreq_closed', function (event, client_id) {
			clientListService.getclients();
		});

		$scope.$on('req_created', function (event, client_id) {
			clientListService.getclients();
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
		vm.save = save;
		vm.close = close;

		$scope.$on('client_select', function (event, client_id) {
			// if (client_id) {
			// }
			close();
			clientDetailService.getdetails(client_id);
		});

		function edit (mode) {
			vm.edit_mode = mode;
			if (mode == 'update') {
				angular.copy(vm.client, vm.edit_cli);
			}
		}

		function save () {
			if (vm.edit_form.$dirty) {
				if (vm.edit_form.$valid) {
					if (vm.edit_mode == 'update') {
						vm.edit_msg = 'Updating...';
						vm.edit_err = '';
						clientDetailService.updateclient(vm.edit_cli)
						.then(function (client) {
							close();
							// Emit so client list can be updated
							// TODO: send to service instead?
							$scope.$emit('client_updated', client);
						})
						.catch(function (reason) {
								vm.edit_msg = '';
								vm.edit_err = reason.error || 'Update failed';
							}
						);
					}
					else if (vm.edit_mode == 'create') {
						vm.edit_msg = 'Creating...';
						vm.edit_err = '';
						clientDetailService.addclient(vm.edit_cli)
						.then(function (client) {
							close();
							// Emit so client list can be updated
							// TODO: send to service instead?
							$scope.$emit('client_updated', client);
						})
						.catch(function (reason) {
								vm.edit_msg = '';
								vm.edit_err = reason.error || 'Creation failed';
							}
						);
					}
				}
				else {
					vm.edit_err = 'Please correct above error(s)';
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

iwsApp.controller('ReqListController', ['$scope', 'reqListService', 'clientListService',
	function ($scope, reqListService, clientListService) {
		var vm = this;
		vm.tab = 'open';
		vm.req = {
			open: "",
			closed: ""
		};
		vm.client = reqListService.client;
		vm.getclientname = clientListService.getclientname;
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

		$scope.$on('oreq_updated', function(event, client_id) {
			// Update under the following conditions:
			//   - client_id matches or is _all
			//   - tab is open, or tab is closed and open list has already been fetched
			if (((vm.client.id == client_id) || (vm.client.id == '_all')) && 
				((vm.tab == 'open') || ((vm.tab == 'closed') && (vm.client.open_list !== null)))) {
				reqListService.refopen();
			}
		});

		$scope.$on('oreq_closed', function(event, client_id) {
			// We want to update both lists if fetched
			if ((vm.client.id == client_id) || (vm.client.id == '_all')) {
				if (vm.client.open !== null) {
					reqListService.refopen();
				}
				if (vm.client.closed !== null) {
					reqListService.refclosed();
				}
				// Deselect request on open tab, select on closed
				// Don't send req_select event -- we want to let
				// the just-closed req stay visible
				if (vm.tab == 'open') {
					vm.req.closed = vm.req.open;
					vm.req.open = "";
				}
			}
		});

		$scope.$on('req_created', function(event, client_id, req){
			if ((vm.client.id == client_id) || (vm.client.id == '_all')) {
				vm.req.open = req.id;
				if (vm.client.open !== null) {
					reqListService.refopen();
				}
				selecttab('open');
			}
		});

		$scope.$on('req_updated', function(event, req) {
			// Update if tab is open, or tab is closed and open list has already been fetched
			if ((vm.tab == 'open') || ((vm.tab == 'closed') && (vm.client.open_list !== null))) {
				reqListService.updatereq(req);
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

iwsApp.controller('ReqDetailController', ['$scope', 'reqDetailService', 'clientListService',
	function ($scope, reqDetailService, clientListService) {
		var vm = this;
		var fields = ['ref_url', 'prod_area', 'title']; // Description can only be appended to

		vm.areas = ['Policies', 'Billing', 'Claims', 'Reports'];
		vm.detail = reqDetailService.detail;
		vm.clients = clientListService.clients;
		vm.getclientname = clientListService.getclientname;

		vm.edit = edit;
		vm.save = save;
		vm.close = close;

		$scope.$on('client_select', function (event, client_id) {
			close();
			reqDetailService.clearreq();
		});

		$scope.$on('req_select', function (event, req_id) {
			close();
			if (!req_id) {
				reqDetailService.clearreq();
			}
			else {
				reqDetailService.getdetails(req_id);
			}
		});

		function edit (mode) {
			vm.edit_mode = mode;
			vm.edit_req = iwsUtil.emptyobj();

			if (mode == 'update') {
				var req = vm.detail.req;
				vm.edit_req.title = req.title;
				vm.edit_req.prod_area = req.prod_area;
				vm.edit_req.ref_url = req.ref_url;
				vm.edit_req.desc = ''; // Description can only be appended to
			}
			else if (mode == 'create') {
				vm.edit_req.title = '';
				vm.edit_req.prod_area = vm.areas[0];
				vm.edit_req.ref_url = '';
				vm.edit_req.desc = '';
				if (vm.clients.id == '_all') {
					vm.edit_oreq = {
						priority: null,
						date_tgt: null
					};
						// client_id: '',
				}
				else {
					vm.edit_oreq = {
						client_id: vm.clients.id,
						priority: null,
						date_tgt: null
					};
				}
				vm.today = new Date();
			}
		}

		function save () {
			if (vm.edit_form.$dirty) {
				if (vm.edit_form.$valid) {
					if (vm.edit_mode == 'update') {
						vm.edit_msg = 'Updating...';
						vm.edit_err = '';
						reqDetailService.updatereq(vm.edit_req)
						.then(function (detail) {
							close();
							if (detail.req) {
								// Emit so req list can be updated
								$scope.$emit('req_updated', detail.req);
							}
						})
						.catch(function (reason) {
							vm.edit_msg = '';
							vm.edit_err = reason.error || 'Update failed';
						});
					}
					else if (vm.edit_mode == 'create') {
						if (vm.open_form.$valid) {
							vm.edit_msg = 'Creating...';
							vm.edit_err = '';
							reqDetailService.addreq(vm.edit_req, vm.edit_oreq)
							.then(function (detail) {
								var client_id = vm.edit_oreq.client_id;
								close();
								// Emit so req list can be updated
								$scope.$emit('req_created', client_id, detail.req);
							})
							.catch(function (reason) {
								vm.edit_msg = '';
								vm.edit_err = reason.error || 'Creation failed';
							});
						}
						else {
							if (!vm.edit_oreq.client_id) {
								vm.open_form.client_id.$setDirty();
							}
							vm.edit_err = 'Please correct above error(s)';
						}
					}
				}
				else {
					vm.edit_err = 'Please correct above error(s)';
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
			vm.edit_req = iwsUtil.emptyobj();
		}
	}
]);

iwsApp.controller('OpenReqController', ['$scope', 'reqDetailService',
	function ($scope, reqDetailService) {
		var vm = this;
		vm.oreq = null;
		close();
		vm.status_list = ['Complete', 'Rejected', 'Deferred']
		vm.setup = setup;
		vm.edit = edit;
		vm.save = save;
		vm.close = close;

		function setup (oreq) {
			vm.oreq = oreq;
			vm.today = new Date();
		}

		function edit (mode) {
			vm.edit_mode = mode;
			vm.edit_oreq = {client_id: vm.oreq.client_id};
			if (mode == 'update') {
				vm.edit_oreq.priority = vm.oreq.priority;
				vm.edit_oreq.date_tgt = vm.oreq.date_tgt
			}
			else if (mode == 'close') {
				vm.edit_oreq.status = vm.status_list[0];
				vm.edit_oreq.reason = 'Request complete';
			}
		}

		function save () {
			if (vm.edit_mode == 'update') {
				if (vm.edit_form.$dirty) {
					// Have to check date_tgt specially -- leaving a past date intact is valid
					if ((vm.edit_form.priority.$valid) && 
						(vm.edit_form.date_tgt.$pristine || vm.edit_form.date_tgt.$valid)) {

						// Both priority and date_tgt can be null (or can be *changed* to null),
						// so for both we have to check if at least one of them is set on original
						// or edit copy AND if they differ (bit of extra work here, sadly)
						var update = {client_id: vm.edit_oreq.client_id};
						if ((vm.edit_oreq.priority || vm.oreq.priority) && 
							(vm.edit_oreq.priority != vm.oreq.priority)) {
							update.priority = vm.edit_oreq.priority;
						}
						if ((vm.edit_oreq.date_tgt || vm.oreq.date_tgt) && 
							(vm.edit_oreq.date_tgt != vm.oreq.date_tgt)) {
							update.date_tgt = vm.edit_oreq.date_tgt;
						}

						vm.edit_msg = 'Updating...';
						vm.edit_err = '';
						var client_id = vm.edit_oreq.client_id;
						reqDetailService.updateopen(update)
						.then(function (response) {
							if (response) {
								// Emit so req list can be updated
								$scope.$emit('oreq_updated', client_id);
							}
						})
						.catch(function (reason) {
							vm.edit_msg = '';
							vm.edit_err = reason.error || 'Update failed';
						});
					}
					else {
						vm.edit_err = 'Please correct above error(s)';
					}
				}
				else {
					close();
				}
			}
			else if (vm.edit_mode == 'close') {
				if (vm.edit_form.$valid) {
					// TODO: modal dialog for confirmation
					vm.edit_msg = 'Closing...';
					vm.edit_err = '';
					var client_id = vm.edit_oreq.client_id;
					reqDetailService.closereq(vm.edit_oreq)
					.then(function () {
						// Emit so client list can be updated
						$scope.$emit('oreq_closed', client_id);
					})
					.catch(function (reason) {
						vm.edit_msg = '';
						vm.edit_err = reason.error || 'Closing failed';
					});
				}
			}
		}

		function close () {
			vm.edit_mode = '';
			vm.edit_msg = '';
			vm.edit_err = '';
			vm.edit_oreq = iwsUtil.emptyobj();
		}
	}
]);


/* Utility functions */

// TODO: change to prototype instead?
var iwsUtil = {
	oreqproc: function oreqproc(oreq) {
		// Process received data into new object
		var newreq = Object.create(null);
		if (oreq.client_id) {
			newreq.client_id = oreq.client_id;
		}
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
		var newreq = Object.create(null);
		if (creq.client_id) {
			newreq.client_id = creq.client_id;
		}
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
