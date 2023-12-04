from upstox_api.api import *
import csv
import pandas as pd
import xlwings as xw
api_key=open('D:\\Share\\Xavier\\upstox\\api_key - Xavier.txt','r').read()
api_secret=open('D:\\Share\\Xavier\\upstox\\api_secret - Xavier.txt','r').read()
code='5bfa7d2c7eb2f94a1d37abf9fffc4f31e8b4dd16'
url='https://upstox.com/developer'
s=Session(api_key)
s.set_redirect_uri(url)
s.set_api_secret(api_secret)
s.set_code(code)
access_token=s.retrieve_access_token()
access_token = pd.DataFrame(access_token)
with open('access_token - Xavier.txt','w') as csvfile:
    wr=csv.writer(csvfile)
    wr.writerow([access_token['access_token'][0]])
with open('D:\\Share\\Xavier\\upstox\\access_token - Xavier.txt','w') as csvfile:
    wr=csv.writer(csvfile)
    wr.writerow([access_token['access_token'][0]])
    print(access_token)
print(access_token['access_token'][0])
wb = xw.Book(
    'client_list.xlsx'
    )
sheet = wb.sheets['list']
sheet.range("E6").options(index=False).value = access_token['access_token'][0]
