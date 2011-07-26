#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api import channel
from google.appengine.api import taskqueue

import os
from google.appengine.ext.webapp import template
from django.utils import simplejson as json

import uuid
import datetime
import Cookie
import logging

from model import *
from clientmanager import *

class BaseHandler(webapp.RequestHandler):
    #copied from runwithfriends application
    def set_cookie(self, name, value, expires=None):
        """Set a cookie"""
        if value is None:
            value = 'deleted'
            expires = datetime.timedelta(minutes=-50000)
        jar = Cookie.SimpleCookie()
        jar[name] = value
        jar[name]['path'] = u'/'
        if expires:
            if isinstance(expires, datetime.timedelta):
                expires = datetime.datetime.now() + expires
            if isinstance(expires, datetime.datetime):
                expires = expires.strftime('%a, %d %b %Y %H:%M:%S')
            jar[name]['expires'] = expires
        self.response.headers.add_header(*jar.output().split(u': ', 1))

class MainHandler(BaseHandler):
    def get(self):
        uniqueid = ''
        if self.request.cookies.get('uid'):
            uniqueid = self.request.cookies.get('uid')
        else:
            uniqueid = str(uuid.uuid4())
            self.set_cookie('uid', uniqueid)
        
        path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
        self.response.out.write(template.render(path, {}))

class SaveHandler(webapp.RequestHandler):
    def post(self):
        itemtitle = self.request.get('itemtitle')
        itemtext = self.request.get('itemtext')
        
        self.response.headers['Content-Type'] = 'text/json'
        
        cm = ClientManager()
        
        if itemtext and itemtitle:
            item = Item(title=itemtitle, bodytext=itemtext)
            item.put()
            
            d = {'rows': []}
            d['rows'].append(item.toDict())
            jsonstr = json.dumps(d)

            for clientid in cm.clientids():
                #channel.send_message(clientid, json.dumps(d))
                taskqueue.add(url='/workers/senditem', params={'clientid': clientid, 'message': jsonstr})
            
            self.response.out.write(json.dumps({'result': 'success'}))
        else:
            self.response.out.write(json.dumps({'result': 'failure'}))
            
class ListHandler(webapp.RequestHandler):
    def get(self):
        items = Item.all()
        items.order("-createdate")
        
        d = {'rows': []}
        for item in items.fetch(20):
            d['rows'].append(item.toDict())
                
        self.response.headers['Content-Type'] = 'text/json'
        self.response.out.write(json.dumps(d))

class GetTokenHandler(webapp.RequestHandler):
    def get(self):
        uniqueid = self.request.cookies.get('uid')
        token = channel.create_channel(uniqueid)
        
        cm = ClientManager()
        
        cm.add(uniqueid)
        
        self.response.headers['Content-Type'] = 'text/json'
        self.response.out.write(json.dumps(dict(token=token)))
        
class SendItemWorkerHandler(webapp.RequestHandler):
    def post(self):
        clientid = self.request.get('clientid')
        message = self.request.get('message')
        
        logging.info(message)
        channel.send_message(clientid, message)

def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                         ('/save', SaveHandler),
                                         ('/list', ListHandler),
                                         ('/gettoken', GetTokenHandler),
                                         ('/_ah/channel/disconnected/', ClientDisconnectHandler),
                                         ('/workers/senditem', SendItemWorkerHandler),],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
