from upstox_api.api import *
import csv
import pandas as pd
import xlwings as xw
api_key=open('D:\\Share\\Xavier\\upstox\\api_key.txt','r').read()
api_secret=open('D:\\Share\\Xavier\\upstox\\api_secret.txt','r').read()
code='jJfO1N'
url='https://upstox.com/developer'
s=Session(api_key)
s.set_redirect_uri(url)
s.set_api_secret(api_secret)
s.set_code(code)
access_token=s.retrieve_access_token()
access_token = pd.DataFrame(access_token)
with open('access_token.txt','w') as csvfile:
    wr=csv.writer(csvfile)
    wr.writerow([access_token['access_token'][0]])
with open('D:\\Share\\Xavier\\upstox\\access_token.txt','w') as csvfile:
    wr=csv.writer(csvfile)
    wr.writerow([access_token['access_token'][0]])
    print(access_token)
print(access_token['access_token'][0])
wb = xw.Book(
    'client_list.xlsx'

    )
sheet = wb.sheets['list']
sheet.range("E2").options(index=False).value = access_token['access_token'][0]