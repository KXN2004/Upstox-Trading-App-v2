import json, upstox_client
from upstox_client.rest import ApiException
from pprint import pprint

# Configure OAuth2 access token for authorization: OAUTH2
configuration = upstox_client.Configuration()
with open('credentials.json') as file:
    configuration.access_token = json.load(file)['access_token']

# create an instance of the API class
api_instance = upstox_client.OrderApi(upstox_client.ApiClient(configuration))

try:
    # Get trades
    api_response = api_instance.get_trade_history(api_version='2.0')
    pprint(api_response)
except ApiException as e:
    print("Exception when calling OrderApi->get_trade_history: %s\n" % e)
