import webbrowser, upstox_client
from upstox_client.rest import ApiException

# Launch the default web browser and ask the user to login
webbrowser.get('chrome').open('https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=d6cb7427-c883-456f-9e2a-5f01f944fd78&redirect_uri=https://account.upstox.com/contact-info/')

# Ask the user to enter the code
code = input('code: ')

# create an instance of the API class
api_instance = upstox_client.LoginApi()

try:
    # Get token API
    api_response = api_instance.token(
        api_version='2.0',
        code=code,
        client_id='d6cb7427-c883-456f-9e2a-5f01f944fd78',
        client_secret='tvcbzamd68',
        redirect_uri='https://account.upstox.com/contact-info/',
        grant_type='authorization_code'
    )
    with open('access_token', 'w') as file:
        file.write(api_response.access_token)
    print("generated access token succesfully!")
except ApiException as e:
    print("Exception when calling LoginApi->token: %s\n" % e)