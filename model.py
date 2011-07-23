from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Item(polymodel.PolyModel):
    title = db.StringProperty()
    bodytext = db.StringProperty(multiline=True)
    createdate = db.DateTimeProperty(auto_now_add=True)
    
class ClientToken(db.Model):
    token = db.StringProperty()
    status = db.StringProperty()
    
class ClientManager(object):
    """
    manager for client tokens
    """
    
    def add(self, token):
        ct_k = db.Key.from_path('ClientToken', token)
        if not db.get(ct_k):
            ct = ClientToken(key_name=token, token=token, status='active')
            ct.put()
            
    def remove(self, token):
        ct_k = db.Key.from_path('ClientToken', token)
        ct = db.get(ct_k)
        if ct:
            ct.delete()
            
    def tokens(self):
        ct = ClientToken().all()
        return [o.token for o in ct]