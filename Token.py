import time, json, pyperclip, pyautogui, platform, webbrowser, upstox_client
from upstox_client.rest import ApiException

match platform.system():
    case 'Windows':
        modifier = 'ctrl'
    case 'Darwin':
        modifier = 'command'

with open('credentials.json', 'r') as file:
    credentials = json.load(file)

# Launch the default web browser and ask the user to login
webbrowser.get('chrome').open(f'https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={credentials["client_id"]}&redirect_uri={credentials["redirect_url"]}')

url = 'Waiting for authorization...'
print(url)
while not url.startswith(credentials['redirect_url'] + '?code='):
    time.sleep(5)
    pyautogui.hotkey(modifier, 'l')
    pyautogui.hotkey(modifier, 'c')
    url = pyperclip.paste()
    code = url.split('=')[-1]

# create an instance of the API class
api_instance = upstox_client.LoginApi()

try:
    # Get token API
    api_response = api_instance.token(
        api_version='2.0',
        code=code,
        client_id=credentials['client_id'],
        client_secret=credentials['client_secret'],
        redirect_uri=credentials['redirect_url'],
        grant_type='authorization_code'
    )
    credentials['access_token'] = api_response.access_token
    with open('credentials.json', 'w') as file:
        json.dump(credentials, file)
    print("Generated the access token succesfully!")
except ApiException as e:
    print("Exception when calling LoginApi->token: %s\n" % e)
