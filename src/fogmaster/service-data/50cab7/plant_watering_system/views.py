from django.shortcuts import render
from django.http import HttpResponse
import requests
from . import logreg, np
import json
from django.views.decorators.csrf import csrf_exempt
# Create your views here.

def index(request):
	turl="https://api.thingspeak.com/channels/463394/fields/1.json?api_key=CJYZUN42TLU2MGAS&results=1"
	hurl="https://api.thingspeak.com/channels/463394/fields/2.json?api_key=CJYZUN42TLU2MGAS&results=1"
	murl="https://api.thingspeak.com/channels/463394/fields/3.json?api_key=CJYZUN42TLU2MGAS&results=1"
	iurl="https://api.thingspeak.com/channels/463394/fields/4.json?api_key=CJYZUN42TLU2MGAS&results=1"
	t=requests.get(turl)
	h=requests.get(hurl)
	m=requests.get(murl)
	i=requests.get(iurl)
	temperature=t.json()['feeds'][0]['field1']
	humidity=h.json()['feeds'][0]['field2']
	moisture=m.json()['feeds'][0]['field3']
	intensity=i.json()['feeds'][0]['field4']
	# To update a field 
	# https://api.thingspeak.com/update?api_key=M3LSF7N9VW12FQF3&field1=0
	return render(request,'index.html',{'temperature':temperature,'humidity':humidity,'moisture':moisture,'intensity':intensity})


@csrf_exempt
def update(request):
	body = request.body
	data = json.loads(body)
	temperature = float(data['temperature'])
	humidity = float(data['humidity'])
	soil_moisture = 0.7/400*float(humidity)
	light_intensity = float(data['light_intensity'])
	if light_intensity==1:
		return HttpResponse("0")
	else:
		variables = [soil_moisture, temperature, humidity]
		variables = np.array(variables).reshape(1,3)
		prediction = logreg.predict(variables)
		# print float(prediction[0])
	return HttpResponse("{}".format(prediction[0]))
