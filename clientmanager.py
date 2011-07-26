from google.appengine.ext import db
from google.appengine.ext import webapp
    
class ClientId(db.Model):
    clientid = db.StringProperty()
    status = db.StringProperty()
    createdate = db.DateTimeProperty(auto_now_add=True)
    
class ClientManager(object):
    """
    manager for client channel ids
    """
    
    def add(self, clientid):
        ct_k = db.Key.from_path('ClientId', clientid)
        if not db.get(ct_k):
            ct = ClientId(key_name=clientid, clientid=clientid, status='active')
            ct.put()
            
    def remove(self, clientid):
        ct_k = db.Key.from_path('ClientId', clientid)
        ct = db.get(ct_k)
        if ct:
            ct.delete()
            
    def clientids(self):
        ct = ClientId().all()
        return [o.clientid for o in ct]
        
class ClientDisconnectHandler(webapp.RequestHandler):
    def post(self):
        clientid = self.request.get('from')
        
        cm = ClientManager()
        cm.remove(clientid)