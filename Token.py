import json, getpass, webbrowser, upstox_client
from upstox_client.rest import ApiException

# Launch the default web browser and ask the user to login
webbrowser.get('chrome').open('https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=d6cb7427-c883-456f-9e2a-5f01f944fd78&redirect_uri=https://account.upstox.com/contact-info/')

# Ask the user to enter the code
code = getpass.getpass("Enter the code: ")

# create an instance of the API class
api_instance = upstox_client.LoginApi()

try:
    # Get token API
    # TODO: Use one single JSON file to store the client_id, client_secret, redirect_uri and grant_type
    with open('credentials.json') as file:
        credentials = json.load(file)
        api_response = api_instance.token(
            api_version='2.0',
            code=code,
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            redirect_uri='https://account.upstox.com/contact-info/',
            grant_type='authorization_code'
        )
        with open('credentials.json', 'w') as file:
            credentials['access_token'] = api_response.access_token
            json.dump(credentials, file)
    print("Generated the access token succesfully!")
except ApiException as e:
    print("Exception when calling LoginApi->token: %s\n" % e)