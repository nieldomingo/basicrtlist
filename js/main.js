$(function () {
	var INTERVAL_DELAY_OPEN_CONNECTION = 10000;

	$("#itemform").dialog({
		autoOpen: false,
		modal: true,
		width: 450,
		buttons: {
			"Save": function() {
				var itemtitle = $("#itemformmain input[name='itemtitle']").val();
				var itemtext = $("#itemformmain textarea[name='itemtext']").val();
				var that = this;
				$.post('/save',
				       {itemtitle: itemtitle, itemtext: itemtext},
				       function () {
				       	$(that).dialog("close");
				       }, 'json');
			}, 
			"Cancel": function() { 
				$(this).dialog("close"); 
			} 
		}
	});
	
	$("input[name='additem']").bind('click',
		function () {
			$("#itemform").dialog("open");
		}
	);
	
	$("#mainlist").evently({
		_init: {
			before: function () {
				// storage for messageids added to the list, this is kept to prevent duplicate entries
				$$(this).messages = {};
			},
			async: function (cb) {
				$.getJSON('/list',
					function (data) {
						cb(data);
					});
			},
			data: function (data) {
				return {
					items: data['rows']	
				};
			},
			mustache: '\
				{{#items}}\
				<div class="itementry">\
					<h2>{{title}}</h2>\
					<div>\
						{{bodytext}}\
					</div>\
				</div>\
				{{/items}}'
		},
		prependitem: {
			data: function (e, data) {
				var clientid = data['clientid'];
				var messageid = data['messageid'];
				
				$.post('/removemessageidfromqueue', {clientid: clientid, messageid: messageid});

				// add the messageid to the storage list to prevent duplicate entries
				$$(this).messages[messageid] = true;
				
				return {
					items: data['rows']	
				};
			},
			mustache: '\
				{{#items}}\
				<div class="itementry">\
					<h2>{{title}}</h2>\
					<div>\
						{{bodytext}}\
					</div>\
				</div>\
				{{/items}}',
			render: 'prepend'
		}
	});
		
	var setupChannel = function () {
		$("#statusmessage").text("opening connection");
		console.info("trying to open connection");
		$.getJSON('/gettoken', function (data) {
			var channel = new goog.appengine.Channel(data['token']);
			var socket = channel.open();
			
			socket.onopen = function () {
				console.info("connection opened");
				$("#statusmessage").text("");
			};
			
			socket.onclose = function () {
				console.info("connection closed");
			};
			
			socket.onerror = function () {
				console.info("connection error");
				$("#statusmessage").text("no connection...");
				setTimeout(setupChannel, INTERVAL_DELAY_OPEN_CONNECTION);
			};
			
			socket.onmessage = function (message) {
				console.info("message received " + message.data);
				var d = $.parseJSON(message.data);
				
				// check if the message is already added to the list
				if ($$("#mainlist").messages[d['messageid']]) {
					$.post('/removemessageidfromqueue', {clientid: clientid, messageid: messageid});
				}
				else {
					$("#mainlist").trigger('prependitem', [d]);
				}
			};
			
		});
	};
	
	$(document).ajaxError(function (event, request, settings) {
		if (settings.url == '/gettoken') {
			$("#statusmessage").text("no connection...");
			setTimeout(setupChannel, INTERVAL_DELAY_OPEN_CONNECTION);
		}
	});

	setupChannel();
	
});
