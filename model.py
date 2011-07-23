from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Item(polymodel.PolyModel):
    title = db.StringProperty()
    bodytext = db.StringProperty(multiline=True)
    createdate = db.DateTimeProperty(auto_now_add=True)