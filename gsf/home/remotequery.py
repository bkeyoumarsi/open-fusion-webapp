import logging, datetime
from ogre import OGRe
from pygeocoder import Geocoder
from ogre.exceptions import OGReLimitError
from api.models import Features, OgreQueries
from localquery import query_cached_third_party
from twython import TwythonRateLimitError, TwythonError
from gsf.settings import TWITTER_CONSUMER_KEY, TWITTER_ACCESS_TOKEN

logger = logging.getLogger(__name__)

retriever = OGRe ({
   "Twitter": {
      "consumer_key": TWITTER_CONSUMER_KEY,
      "access_token": TWITTER_ACCESS_TOKEN,
   }
})
      
"""
   Passes user query to get third party data
"""
def query_third_party(
   sources,
   keyword, 
   options, 
   location,
   interval,
   query_limit
):
   
   results = []
   error = ""

   if query_limit is None:
      query_limit = 1
      
   quantity = query_limit*100
      
   outside_data = {}
   try:
      outside_data = retriever.fetch(sources,
                           media=options,
                           keyword=keyword,
                           quantity=quantity,
                           location=location,
                           interval=interval,
                           query_limit=query_limit)
   except (TwythonRateLimitError, OGReLimitError) as e:
      logger.debug(e)
      error = """Unfortunately our Twitter retriever has been rate
         limited. We cannot do anything but wait for Twitter's tyranny to end."""
   except TwythonError, e:
      logger.error(e)
   except Exception, e:
      logger.error(e)

   # Cache the data in db
   logger.debug(datetime.datetime.utcnow())
   """for data in outside_data.get("features", []):
      kwargs = {
               "geometry": data["geometry"],
               "properties__time": data["properties"]["time"],
               "properties__text": data["properties"]["text"],
               }
      if not Features.objects.filter(**kwargs):
         feature = Features(**data)
         try:
            feature.save()
         except Exception, e:
            logger.debug(e)"""
   logger.debug(datetime.datetime.utcnow())

   results.extend(outside_data.get("features", []))

   return (error, results)
   
"""
   Get epicenters from user inputed addresses using Google Maps API
"""
def create_epicenters_from_addresses(addresses):
   epicenters = []
   address_list = addresses.rstrip("\r\n").split("\n")
   for address in address_list:
      try:
         results = Geocoder.geocode(address)
         lat = float(results[0].coordinates[0])
         lon = float(results[0].coordinates[1])
         epicenter = {
            "type": "Feature",
            "geometry": {
               "type": "Point",
               "coordinates": [lon, lat]
            },
            "properties": {
               "text": address,
            }
         }
         epicenters.append(epicenter)
      except Exception, e:
         logger.debug(e)
   return epicenters
