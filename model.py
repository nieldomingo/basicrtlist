from google.appengine.ext import db
from google.appengine.ext.db import polymodel
from django.utils import simplejson as json

import hashlib

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

        d['checksum'] = hashlib.md5(self.title + self.bodytext).hexdigest();
        
        return d
        
    def toJSON(self):
        return json.dumps(self.toDict())
