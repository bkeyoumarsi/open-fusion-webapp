from mongoengine import *
from gsf.settings import MONGODB_NAME

import datetime

connect(MONGODB_NAME)

# The Data collection layout
class Data(Document):
   date_added  = DateTimeField(default=datetime.datetime.now)
   source      = StringField(required=True, max_length=50)
   timestamp   = DecimalField(required=True)
   location    = PointField(required=True)
   altitude    = DecimalField(precision=5)
   h_accuracy  = DecimalField(precision=5)
   v_accuracy  = DecimalField(precision=5)
   text        = StringField(max_length=1000)
   image       = StringField()
   noise_level = DecimalField(precision=5)
   temperature = DecimalField(precision=5)
   humidity    = DecimalField(precision=5)
   faces_detected  = IntField()
   people_detected = IntField()

   class Meta:
      ordering = ('date_added',)

class Tokens(Document):
   created = DateTimeField(default=datetime.datetime.now)
   token   = StringField(required=True, max_length=50, min_length=50)
   secret  = StringField(required=True, max_length=50, min_length=8)
   


