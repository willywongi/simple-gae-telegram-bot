#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
import json
import logging

import webapp2
from google.appengine.api.app_identity.app_identity import get_application_id, get_default_version_hostname
from google.appengine.api import urlfetch

# from telegram import Bot, Update

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
					level=logging.INFO)
logger = logging.getLogger()

TELEGRAM_BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
APIAI_TOKEN = os.environ['APIAI_TOKEN']
PROJECT_ID = get_application_id()
HOSTNAME = get_default_version_hostname()
BASE_URL = '/{0}'.format(TELEGRAM_BOT_TOKEN)
WEBHOOK_URL = 'https://{0}{1}'.format(HOSTNAME, BASE_URL)

TELEGRAM_API_URL = "https://api.telegram.org/bot{}".format(TELEGRAM_BOT_TOKEN)
API_AI = "https://api.api.ai/v1"


def telegram(method, **kwargs):
	result = urlfetch.fetch("{}/{}".format(TELEGRAM_API_URL, method), 
		method='POST',
		payload=json.dumps(kwargs),
		headers={'Content-Type': 'application/json'}
	)
	if result.status_code != 200:
		logger.warn("Richiesta %s fallita (%s): %s", method, result.status_code, result.content)
	return json.loads(result.content)


def apiai(chat_id, text):
	data = {
		'v': '20170111',
		'lang': 'it',
		'query': text,
		'sessionId': chat_id
	}
	headers = {
		'Authorization': 'Bearer {}'.format(APIAI_TOKEN),
		'Content-Type': 'application/json; charset=utf-8'
	}

	logger.debug('Querying api.ai with %s', data)
	r = urlfetch.fetch("{}/query".format(API_AI),
					method='POST',
					payload=json.dumps(data).encode('utf-8'),
					headers=headers)
	if r.status_code == 200:
		response = json.loads(r.content.decode('utf-8'))
		logger.debug('Response from api.ai: %s', response)
		return response
	else:
		logger.warn("Query to api.ai failed %s (%s: %s)", text, r.status_code, r.content)
		raise ValueError('Api.ai ERROR')


class MainHandler(webapp2.RequestHandler):
	def get(self):
		resp = telegram('setWebhook', url=WEBHOOK_URL)
		self.response.headers['Content-Type'] = 'text/plain'
		text = """
		TELEGRAM_BOT_TOKEN = {}
		PROJECT_ID = {}
		HOSTNAME = {}
		BASE_URL = {}
		WEBHOOK_URL = {}
		resp = {}
		"""
		self.response.write(text.format(TELEGRAM_BOT_TOKEN, PROJECT_ID, HOSTNAME, BASE_URL, WEBHOOK_URL, resp))

	def post(self):
		update = json.loads(self.request.body)
		logger.debug(update)
		chat_id = update['message']['chat']['id']
		message = update['message']['text']
		telegram('sendChatAction', chat_id=chat_id, action='typing')
		apiai_response = apiai(chat_id, message)
		r = apiai_response['result']

		response_text = r.get('speech')
		if not response_text:
			# api.ai non ha capito cosa dire
			response_text = 'Sono un bot, non sempre capisco.'

		telegram('sendMessage', chat_id=chat_id, text=response_text)
		

app = webapp2.WSGIApplication([
    (BASE_URL, MainHandler)
], debug=True)
