$(function () {
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
		$.getJSON('/gettoken', function (data) {
			var channel = new goog.appengine.Channel(data['token']);
			var socket = channel.open();
			
			socket.onopen = function () {
				console.info("connection opened");
			};
			
			socket.onclose = function () {
				setupChannel();
			};
			
			socket.onmessage = function (message) {
				console.info("data: %s"%message.data);
				$("#mainlist").trigger('prependitem', [$.parseJSON(message.data)]);
			};
			
		});
	};
	
	setTimeout(setupChannel, 100);
	
});