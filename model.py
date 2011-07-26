from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from django.utils import simplejson as json

class Item(polymodel.PolyModel):
    title = db.StringProperty()
    bodytext = db.StringProperty(multiline=True)
    createdate = db.DateTimeProperty(auto_now_add=True)
    
    def toDict(self):
        key = self.key()
        attribkeys = [k for k in self.__class__.__dict__.keys() if k[0] != '_']
        d = {'key': '%s'%key}
        for k in attribkeys:
            o = self.__class__.__dict__.get(k)
            if isinstance(o, db.StringProperty) or isinstance(o, db.TextProperty):
                d[k] = getattr(self, k)
            elif isinstance(o, db.DateTimeProperty):
                d[k] = getattr(self, k).isoformat()
                
        return d
        
    def toJSON(self):
        return json.dumps(self.toDict())
        
    def put(self):
        if self.is_saved():
            polymodel.PolyModel.put(self)
            lr = ListRevision(parent=self, action='add', itemjson=self.toJSON())
            lr.put()
        else:
            polymodel.PolyModel.put(self)
            lr = ListRevision(parent=self, action='edit', itemjson=self.toJSON())
            lr.put()
    
class ListRevision(db.Model):
    action = db.StringProperty()
    timestamp = db.DateTimeProperty(auto_now_add=True)
    itemjson = db.TextProperty()