from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, \
                        HttpResponseServerError, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django import forms
from api.models import Features, Properties, APIKey, Coordinates
from gsf.settings import reCAPTCHA_KEY
from recaptcha.client import captcha
import json, logging, base64, hashlib, random

logger = logging.getLogger(__name__)

try:
   from decorators import *
except:
   logger.error("Failed to load the decorators module")   

"""
   API Key random generator
"""
def generate_key():
   key = base64.b64encode(hashlib.sha256( \
            str(random.getrandbits(256)) ).digest(), \
            random.choice(['rA','aZ','gQ','hH','hG','aR','DD'])).rstrip('==')
   return key

"""
 The Sign up form for the developers API key
"""
class SignupForm(forms.Form):
   developer_name = forms.CharField(required=True)
   organization = forms.CharField(required=False)
   application_name = forms.CharField(required=True)
   email = forms.EmailField(required=True)
   
"""
 Process developer request for an API key
"""
def dev_signup(request):
   invalid_captcha = False
   if request.method == 'POST':
      form = SignupForm(request.POST)

      # talk to the reCAPTCHA service  
      response = captcha.submit(  
            request.POST.get('recaptcha_challenge_field'),  
            request.POST.get('recaptcha_response_field'),  
            reCAPTCHA_KEY,  
            request.META['REMOTE_ADDR'],)

      if form.is_valid() and response.is_valid:
         dev_name = form.cleaned_data['developer_name']
         organization = form.cleaned_data['organization']
         app_name = form.cleaned_data['application_name']
         email = form.cleaned_data['email']

         # Generate API key
         key_req = APIKey(application=app_name)
         key_req.organization = organization
         key_req.full_name = dev_name
         key_req.email = email
         key_req.key = generate_key()

         key_req.save()

         # Prepare email
         sender = 'Wild Stallions'
         message = ("Thank you for signing up for an API Key.\n\nYour Key: %s" % key_req.key)
         subject = "Geotagged Sensor Fusion API Key"
         recipient = [email]

         # Send email
         from django.core.mail import send_mail
         send_mail(subject, message, sender, recipient)

         return HttpResponseRedirect('/')
      elif not response.is_valid:
         invalid_captcha = True
   else:
      form = SignupForm()

   return render(request, 'api/devsignup.html', 
      {'form': form, 'captcha_flag': invalid_captcha}
   )

"""
 Currently only accepts data from the iOS app 
 with the appropriate API key given with the request
"""
@csrf_exempt
@auth_required
def upload(request):
   if request.method == 'POST':
      try:
         json_data_top_level = json.loads(request.body)
      except Exception, e:
         logger.error(e)
         return HttpResponseBadRequest(
            "The request cannot be processed. We couldn't find json in the body.\n")
      
      try:
         if json_data_top_level['type'] != "FeatureCollection":
            logger.error("Failed to match type with FeaturedCollection")
            return HttpResponseBadRequest(
               "The request cannot be processed. Your geoJSON is malformed\n")
         features_list = json_data_top_level['features']
      except KeyError, e:
         logger.error(e)
         return HttpResponseBadRequest(
            "The request cannot be processed. Your geoJSON is malformed\n")
      for dictionary in features_list:
         try:
            # Set up variables to store proper data in the db
            #feature = Features().from_json(json.dumps(dictionary))
            feature = Features(**dictionary)
            feature.properties["source"] = "iPhone"
            try:
               feature.save()
            except Exception, e:
               logger.error(e)
               return HttpResponseBadRequest(
                  "The request cannot be processed due to bad data types.\n")
         except KeyError, e:
            logger.error(e)
            return HttpResponseBadRequest(
               "The request cannot be processed due malformed geoJSON.\n")
      return HttpResponse("Data was received\n", status=201)
   else:
      logger.error("GET req can't be processed")
      return HttpResponseBadRequest("You can only upload with POST you fool!\n")

"""
 Receives uri encoded querystring, converts to JSON and passes
 to mongoengine for processing. The returned data is converted to 
 JSON and sent back to the user
"""
@auth_required
def download(request):
   if request.method == 'GET':
      query_string = request.GET.get('query')
      if not query_string:
         logger.debug("Failed to pull the query from the url")
         return HttpResponseBadRequest("No query string provided\n")
      try:
         query = json.loads(query_string)
         data = Features.objects(__raw__=query).to_json(indent=4, separators=(",", ": "))
         return HttpResponse(data, content_type='application/json')
      except:
         logger.debug("Failed to run the query")
         return HttpResponseBadRequest("Bad query!\n")
   else:
      return HttpResponseBadRequest("Only GET requests are processed\n")

"""
   Return a set of coordinates to the iOS app for the field agents
"""
def coordinates(request):
   if request.method == "GET":
      doc_id = request.GET.get("id")
      if not doc_id:
         logger.debug("no id")
         return HttpResponseBadRequest("You didn't give us an id.\n")
      
      package = None      
      try:
         package = Coordinates.objects.all().as_pymongo()
         package = package(pk=doc_id).first()
      except Exception, e:
         logger.debug(e)
         return HttpResponseBadRequest("We couldn't find the coordinates you asked for.\n")

      if package:
         package.pop("_id", None)
         package.pop("date_added", None)
         return HttpResponse(json.dumps(package), content_type='application/json')
      else:
         logger.debug("Invalid coordinates id")
         return HttpResponseBadRequest("We couldn't find the coordinates you asked for.\n")
   else:
      return HttpResponseBadRequest("GET requests are only supported on this API call.\n")
      
