#!/usr/bin/env python

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
import utils

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
            
            d = {'rows': [], 'mtype': 'add'}
            d['rows'].append(item.toDict())
            jsonstr = json.dumps(d)

            for clientid in cm.clientids():
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
        message = json.loads(self.request.get('message'))

        countdown = 180

        cm = ClientManager()
        messageid = self.request.get('messageid')
        if not messageid:
            messageid = str(uuid.uuid4())
            cm.add_messageid(clientid, messageid)
            jsonstr = json.dumps(dict(message,
                messageid=messageid,
                clientid=clientid))
            channel.send_message(clientid, jsonstr)
            taskqueue.add(url='/workers/senditem', params={'clientid': clientid,
                'message': jsonstr,
                'messageid': messageid,
                'count': 1}, countdown=countdown)
        else:
            if cm.check_clientid(clientid) and cm.check_messageid(clientid, messageid):
                 count = self.request.get('count') + 1
                 if count <= 5:
                     logging.info("Resending message %s"%message)
                     jsonstr = json.dumps(dict(message,
                         messageid=messageid,
                         clientid=clientid))
                     channel.send_message(clientid, jsonstr)
                     taskqueue.add(url='/workers/senditem', params={'clientid': clientid,
                         'message': jsonstr,
                         'messageid': messageid,
                         'count': count}, countdown=countdown)
                 else:
                     # after trying 5 times, assume that the client has disconnected
                     cm.remove(clientid)

class RemoveMessageIdFromQueueHandler(webapp.RequestHandler):
    def post(self):
        clientid = self.request.get('clientid')
        messageid = self.request.get('messageid')
        
        if clientid and messageid:
            cm = ClientManager()
            cm.remove_messageid(clientid, messageid)

class RequestUpdateListHandler(webapp.RequestHandler):
    def post(self):
        clientid = self.request.cookies.get('uid')
        listdata = self.request.get('listdata')

        logging.info("Received Update List Request")
        #logging.info(listdata)

        l = json.loads(listdata)

        createdates = [utils.parse_isoformat(o['createdate']) for o in l]
        maxdate = max(createdates)

        query = Item().all().filter('createdate >', maxdate).order('-createdate')
        newitems = [o.toDict() for o in query]

        jsonstr = json.dumps({'mtype': 'updatelist', 'add': {'rows': newitems}})
	taskqueue.add(url='/workers/senditem',
            params={'clientid': clientid, 'message': jsonstr})


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                         ('/save', SaveHandler),
                                         ('/list', ListHandler),
                                         ('/gettoken', GetTokenHandler),
                                         ('/_ah/channel/disconnected/', ClientDisconnectHandler),
                                         ('/workers/senditem', SendItemWorkerHandler),
                                         ('/removemessageidfromqueue', RemoveMessageIdFromQueueHandler),
                                         ('/requestupdatelist', RequestUpdateListHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
