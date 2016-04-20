/* Main webview app, controllers, services */

var iwsApp = angular.module('iws-webview', []);

iwsApp.controller('ClientListController', ['$scope', 'clientListService',
	function ($scope, clientListService) {
	// body...
}]);

iwsApp.factory('clientListService', function () {
	var client_list = [];
	var update_list = function () {
		// TODO: $http
	};

	return {
		client_list: client_list,
		update_list: update_list
	};
});
