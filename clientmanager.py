from google.appengine.ext import db
from google.appengine.ext import webapp

import logging

class ClientId(db.Model):
    clientid = db.StringProperty()
    createdate = db.DateTimeProperty(auto_now_add=True)
    messagequeue = db.StringListProperty(default=[])
    
class ClientManager(object):
    """
    manager for client channel ids
    """
    
    def add(self, clientid):
        ct_k = db.Key.from_path('ClientId', clientid)
        if not db.get(ct_k):
            ct = ClientId(key_name=clientid, clientid=clientid)
            ct.put()
            
    def remove(self, clientid):
        ct_k = db.Key.from_path('ClientId', clientid)
        ct = db.get(ct_k)
        if ct:
            ct.delete()
            
    def clientids(self):
        ct = ClientId().all()
        return [o.clientid for o in ct]
        
    def check_clientid(self, clientid):
        ct_k = db.Key.from_path('ClientId', clientid)
        ct = db.get(ct_k)
        if ct:
            return True
        else:
            return False
        
    def add_messageid(self, clientid, messageid):
        ci_k = db.Key.from_path('ClientId', clientid)
        ci = db.get(ci_k)
        if ci and messageid not in ci.messagequeue:
            ci.messagequeue = ci.messagequeue + [messageid]
            ci.put()
            
    def remove_messageid(self, clientid, messageid):
        ci_k = db.Key.from_path('ClientId', clientid)
        ci = db.get(ci_k)
        if ci and messageid in ci.messagequeue:
            l = ci.messagequeue
            l.remove(messageid)
            ci.messagequeue = l
            ci.put()
            
    def check_messageid(self, clientid, messageid):
        ci_k = db.Key.from_path('ClientId', clientid)
        ci = db.get(ci_k)
        if messageid in ci.messagequeue:
            return True
        else:
            return False
        
class ClientDisconnectHandler(webapp.RequestHandler):
    def post(self):
        clientid = self.request.get('from')
        
        logging.info("Client %s disconnected"%clientid)
        
        cm = ClientManager()
        cm.remove(clientid)