import json
import pyautogui
import webbrowser
import upstox_client
from time import sleep
from pyperclip import paste
from platform import system
from upstox_client.rest import ApiException

match system():
    case 'Windows':
        modifier_key = 'ctrl'
        submit_button = 'enter'
    case 'Darwin':
        modifier_key = 'command'
        submit_button = 'return'
    case 'Linux':
        modifier_key = 'ctrl'
        submit_button = 'enter'

with open('credentials.json', 'r') as file:
    credentials = json.load(file)

print("Opening the browser...")
webbrowser.get('chrome').open(f'https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={credentials["client_id"]}&redirect_uri={credentials["redirect_url"]}')

print("Entering the 6 digit pin...")
sleep(2)
pyautogui.typewrite(credentials['PIN'])
pyautogui.press(submit_button)

url = 'Generating the access token...'
print(url)
while not url.startswith(credentials['redirect_url'] + '?code='):
    sleep(2)
    pyautogui.hotkey(modifier_key, 'l')
    pyautogui.hotkey(modifier_key, 'c')
    url = paste()
    code = url.split('=')[-1]

api_instance = upstox_client.LoginApi()

try:
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
    print("Done!")
except ApiException as e:
    print("Exception when calling LoginApi->token: %s\n" % e)
