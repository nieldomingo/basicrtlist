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
            
            messageid = str(uuid.uuid4())
                
            d = {'rows': [], 'mtype': 'add', 'messageid': messageid}
            d['rows'].append(item.toDict())
            jsonstr = json.dumps(d)
            
            taskqueue.add(url='/workers/sendmessages',
                          params={'message': jsonstr, 'messageid': messageid},
                          name="SendMessages-%s"%messageid)
            
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

class SendMessagesWorkerHandler(webapp.RequestHandler):
    def post(self):
        message = json.loads(self.request.get('message'))
        messageid = self.request.get('messageid')
        
        cm = ClientManager()
        
        for clientid in cm.clientids():
            try:
                jsonstr = json.dumps(dict(message,
                                          clientid=clientid))
                logging.info("Clientid: %s, Messageid: %s"%(clientid, messageid))
                taskqueue.add(url='/workers/senditem',
                              params={'clientid': clientid,
                                      'message': jsonstr,
                                      'count': 0,
                                      'messageid': messageid},
                              name="SendItem-%s-%s"%(messageid, clientid))
            except (taskqueue.TaskAlreadyExistsError,
                    taskqueue.TombstonedTaskError):
                pass
        
class SendItemWorkerHandler(webapp.RequestHandler):
    def post(self):
        clientid = self.request.get('clientid')
        message = self.request.get('message')
        messageid = self.request.get('messageid')
        
        countdown = 30 # number of seconds before resending message
        
        cm = ClientManager()
        count = int(self.request.get('count'))
        if count == 0: # first time the message is sent to the client
            try:
                taskqueue.add(url='/workers/senditem',
                              params={'clientid': clientid,
                                      'message': message,
                                      'messageid': messageid,
                                      'count': 1},
                              countdown=countdown,
                              name="SendItem-%s-%s-%s"%(clientid, messageid, 1))
                
                cm.add_messageid(clientid, messageid)
                channel.send_message(clientid, message)
            except (taskqueue.TaskAlreadyExistsError,
                    taskqueue.TombstonedTaskError):
                pass
        else:
            if cm.check_clientid(clientid) and cm.check_messageid(clientid, messageid):
                count = count + 1
                if count <= 5:
                    try:
                        taskqueue.add(url='/workers/senditem',
                                      params={'clientid': clientid,
                                              'message': message,
                                              'messageid': messageid,
                                              'count': count},
                                      countdown=countdown,
                                      name="SendItem-%s-%s-%s"%(clientid, messageid, count))
                        logging.info("Resending message %s"%message)
                        channel.send_message(clientid, message)
                    except (taskqueue.TaskAlreadyExistsError,
                            taskqueue.TombstonedTaskError):
                        pass
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

        messageid = str(uuid.uuid4())

        jsonstr = json.dumps({'mtype': 'updatelist', 'add': {'rows': newitems}, 'clientid': clientid, 'messageid': messageid})
        taskqueue.add(url='/workers/senditem',
                      params={'clientid': clientid, 'message': jsonstr, 'count': 0, 'messageid': messageid})


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                         ('/save', SaveHandler),
                                         ('/list', ListHandler),
                                         ('/gettoken', GetTokenHandler),
                                         ('/_ah/channel/disconnected/', ClientDisconnectHandler),
                                         ('/workers/senditem', SendItemWorkerHandler),
                                         ('/workers/sendmessages', SendMessagesWorkerHandler),
                                         ('/removemessageidfromqueue', RemoveMessageIdFromQueueHandler),
                                         ('/requestupdatelist', RequestUpdateListHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
