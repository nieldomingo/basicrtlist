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

	var basicItemElements = function (o) {
		return {checksum: o['checksum'], key: o['key'], createdate: o['createdate']};
	};	

	$("#mainlist").evently({
		_init: {
			async: function (cb) {
				$.getJSON('/list',
					function (data) {
						cb(data);
					});
			},
			data: function (data) {
				$$(this).listdata = $.map(data['rows'], basicItemElements);
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
				
				$$(this).listdata = $$(this).listdata.concat($.map(data['rows'], basicItemElements));
	
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

	var connection_open_count = 0; // counter to count how many times the client has opened a connection		
	var setupChannel = function () {
		$("#statusmessage").text("opening connection");
		console.info("trying to open connection");
		$.ajax('/gettoken', {
			type: 'GET',
			dataType: 'json',
			success: function (data) {
				var channel = new goog.appengine.Channel(data['token']);
				var socket = channel.open();
				
				var messagemap = {};
				var defferedmessages = {};
				
				socket.onopen = function () {
					console.info("connection opened");
					$("#statusmessage").text("");
					if (connection_open_count > 0) {
						// if connection is not initial connection
						// then request from server an update list message
						$.post('/requestupdatelist',
							{'listdata': JSON.stringify($$("#mainlist").listdata)});
					}
					connection_open_count += 1;
				};
				
				socket.onclose = function () {
					console.info("connection closed");
				};
				
				socket.onerror = function () {
					console.info("connection error");
					$("#statusmessage").text("no connection...");
					setTimeout(setupChannel, INTERVAL_DELAY_OPEN_CONNECTION);
				};
				
				var processmessage = function (messageobj) {
					var messageid = messageobj['messageid'];
					
					if (! messagemap[messageid]) {
						if (messageobj.mtype == 'add') { 	
							$("#mainlist").trigger('prependitem', [messageobj]);
						}
						else if (messageobj.mtype == 'updatelist') {
							var addlist = messageobj['add'];
							if (addlist && addlist['rows'].length) {
								$("#mainlist").trigger('prependitem', [addlist]);
							}
						}
					}
					
					messagemap[messageid] = true;
					
				};
				
				var SequenceManager = {
					sequencecount: 0,
					deferredmessages: {},
					increment: function () {
						this.sequencecount += 1;
						this.process_defferedmessages();
					},
					reset: function () {
						this.sequencecount = 0;
						this.deferredmessages = {};
					},
					push_defferedmessage: function (m) {
						this.deferredmessages[m['sequence']] = m;
					},
					process_defferedmessages: function () {
						if (this.deferredmessages[this.sequencecount]) {
							processmessage(this.deferredmessages[this.sequencecount]);
							console.log(this.sequencecount);
							console.log(this.deferredmessages);
							delete this.deferredmessages[this.sequencecount];
							this.sequencecount += 1;
							this.process_defferedmessages();
						}
					}
				};
				
				socket.onmessage = function (message) {
					console.info("message received " + message.data);
					var d = $.parseJSON(message.data);
					
					var clientid = d['clientid'];
					var messageid = d['messageid'];
					var message_seq = d['sequence'];
					
					if (message_seq == SequenceManager.sequencecount) {
						processmessage(d);
						SequenceManager.increment();
					}
					else if (message_seq > SequenceManager.sequencecount){
						SequenceManager.push_defferedmessage(d);
					}
					$.post('/removemessageidfromqueue',
						{clientid: clientid, messageid: messageid});
				};
			},
			error: function () {
				$("#statusmessage").text("no connection...");
				setTimeout(setupChannel, INTERVAL_DELAY_OPEN_CONNECTION);
			}
		});
	};

	setupChannel();
		
});
