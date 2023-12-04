# Option selling CE & PE to earn on Theta decay, delta added
from typing import DefaultDict
from py_lets_be_rational.erf_cody import P
from upstox_api.api import *
import pandas as pd
from datetime import datetime, time, timedelta
import dateutil.relativedelta
from dateutil.relativedelta import relativedelta, TH
import xlwings as xw
from time import sleep
import schedule
import numpy as np
from talib import RSI, EMA
import pandas_ta as ta
from py_vollib.black_scholes.implied_volatility import *
from py_lets_be_rational.exceptions import BelowIntrinsicException
from scipy.stats import norm
# from apscheduler.schedulers.blocking import BlockingScheduler
# import talib
# print (talib.get_functions())

pd.set_option('mode.chained_assignment', None)

client = pd.read_excel ('client_list.xlsx', sheet_name='list', header=0)

for i in range(len(client)):
    if client['optionwrite'][i] == 0:
        client = client.drop(i)
print(client)

api_key = open('D:/Share/Xavier/upstox/api_key.txt', 'r').read()
access_token = open(
    'D:/Share/Xavier/upstox/access_token.txt', 'r'
    ).read().strip()
s = Upstox(api_key, access_token)
s.get_master_contract('NSE_FO')  # get contracts for NSE FO
s.get_master_contract('NSE_INDEX')  # get contracts for NSE INDEX

wb = xw.Book(
    'Optionpair.xlsx'
    )
sheet = wb.sheets['Trade']
# straddle = wb.sheets['straddle']
bankstrad = wb.sheets['bankstrad']
flags = wb.sheets['flag']
position = wb.sheets['Position']
orders = wb.sheets['Orders']
trade = wb.sheets['TradeBook']
charts = wb.sheets['Chart']

u = []
order = []
trade_table_display = []
tradebook_display = []
orderbook_display = []
positionbook_display = []
chart_display = []
premium = 0.0
exchange = 'NSE_FO'
shortweek = 0
trade_book = [None] * len(client)
position_book = [None] * len(client)
order_book = [None] * len(client)
balance = [None] * len(client)

columns = [
    'profit', 'max_profit', 'max_loss', 'prev_profit', 'close',
    'expiry_nifty','expiry_bank', 'expiry_bank_last_leg_ce', 'expiry_bank_last_leg_pe',
    'supertrend_pe', 'supertrend_ce', 'rsi_pe', 'rsi_ce',
    'ema_ce', 'ema_pe', 'rsi', 'closing_profit', 'double_put', 'double_call',
    'call_delta', 'put_delta', 'scall_delta', 'sput_delta', 'ironfly_shift', 'ironfly_close', 'strad_strike',
    '5min', '15min', '60min', '1day'
    # 'lg_bank_shift_ce', 'lg_bank_shift_pe', 'lg_bank_shift_strike'
    ]

flag = flag1 = pd.DataFrame(data=np.array([[0.0] * len(columns)] * len(client)).reshape(len(client), len(columns)), columns=columns)
print(flag)
trade_table = [pd.DataFrame(columns=[
        'time', 'strategy', 'exchange', 'symbol', 'product', 'rank', 'strike',
        'days_left', 'iv', 'delta', 'qty', 'trade_type', 'Entry_price', 'Entry_status', 
        'order_placed', 'SL_qty', 'SL_price', 'SL_D_price', 'SL_status', 'Tgt1_price',
        'Tgt1_status', 'prem', '3pm_tgt', '3pm_tgt_qty',
        'LTP', 'Profit', 'R.Profit', 'Tgt1', '3pm', 'SL', 'order_rej', 'order_id',
        'order_id_Sft', 'order_id_Tgt1', 'SL_id', 'order_id_3pm'
    ])] * len(client)

Chart_table = [pd.DataFrame(columns=[
        'price', 'current', 'final' 
    ])] * len(client)

for x in range(len(client)):
    u.append(Upstox(client['api_key'].iloc[x], client['access_token'].iloc[x]))
    u[x].get_master_contract('NSE_FO')  # get contracts for NSE FO
    u[x].get_master_contract('NSE_INDEX')  # get contracts for NSE INDEX
    trade_table_display.append(x + 2*x + 2)
    tradebook_display.append(x + 2*x + 2)
    orderbook_display.append(x + 2*x + 2)
    positionbook_display.append(x + 2*x + 2)
    chart_display.append(x + 2*x + 2)

white_space = np.array([['']*36]*2).reshape([2, 36])

now = datetime.now()
to_date = datetime.strftime(now, '%d/%m/%Y')
from_date = datetime.strptime(to_date, '%d/%m/%Y')
from_date = from_date-dateutil.relativedelta.relativedelta(days=6)
from_date = datetime.strftime(from_date, '%d/%m/%Y')
from_date1 = datetime.strptime(to_date, '%d/%m/%Y')
from_date1 = from_date1-dateutil.relativedelta.relativedelta(days=40)
from_date1 = datetime.strftime(from_date1, '%d/%m/%Y')

def append_excel_table(x):
    global trade_table, Entry_bid, Trade, Target1, Tgt1_status, SL_pcent, trade_table_display, days_left
    global tradingsymbol, strategy, exchange, qty, SL_qty, date_time, rank, order_rej, strike, prem, SL_D_price
    global Entry_status, SL_price, SL_status, last_tgt, last_qty, sheet, order_placed, order_id, product
    print(x)
    date_time = datetime.now().strftime("%d/%m/%y,%H:%M:%S")
    trade_table[x] = trade_table[x].append({
        'time' : date_time, 'strategy' : strategy, 'exchange' : exchange, 'days_left' : days_left,
        'symbol' : tradingsymbol, 'qty' : qty, 'trade_type' : Trade, 'rank' : rank, 'product' : product,
        'Entry_price' : Entry_bid, 'Entry_status' : Entry_status, 'order_placed' : order_placed,
        'SL_qty' : SL_qty, 'SL_price': SL_price, 'SL_D_price': SL_D_price, 'SL_status' : SL_status, 'strike' : strike,
        'Tgt1_price' : Target1, 'Tgt1_status' : Tgt1_status, 'order_id' : order_id,
        '3pm_tgt' : last_tgt, '3pm_tgt_qty' : last_qty, 'order_rej' : order_rej, 'prem' : prem
    }, ignore_index=True)
    print(trade_table[x])
    return()

def display_trade():
    global trade_table_display, balance
    for d in range(len(client)):
        try:
            if d == 0:
                trade_table_display[d] = 2
            else:
                trade_table_display[d] = 3 + trade_table_display[d-1] + len(trade_table[d-1])
                sheet.range('A' + str(trade_table_display[d] - 2)).value = white_space
            sheet.range('A' + str(trade_table_display[d])).options(index=False).value = trade_table[d].sort_values(by=['time'])
            if time(7, 19) <= datetime.now().time():
                balance[d] = u[d].get_balance()
                sheet.range('G' + str(trade_table_display[d] - 1)).value = balance[d]['equity']['used_margin']
                sheet.range('I' + str(trade_table_display[d] - 1)).value = balance[d]['equity']['available_margin']
                sheet.range('F' + str(trade_table_display[d] - 1)).value = 'Used'
                sheet.range('H' + str(trade_table_display[d] - 1)).value = 'Available'
                sheet.range('T' + str(trade_table_display[d] - 1)).value = 'MTM'
                sheet.range('A' + str(trade_table_display[d] - 1)).value = client['Name'].iloc[d]
                sheet.range('X' + str(trade_table_display[d] - 1)).value = (flag['call_delta'][d] + flag['put_delta'][d])
                sheet.range('W' + str(trade_table_display[d] - 1)).value = 'Delta'
        except Exception as e:
            print(f'display_trade error in {d}: ', e)

def display_trade_postion():
    global position_book, positionbook_display, profit, trade_table_display, flag
    for p in range(len(client)):
        try:
            balance[p] = u[p].get_balance()
            position_book[p] = pd.DataFrame(u[p].get_positions())
            flag['profit'][p] = 0.0
            for i in range (len(position_book[p])):
                if position_book[p]['unrealized_profit'][i] != '':
                    flag['profit'][p] += float(position_book[p]['unrealized_profit'][i])
                if position_book[p]['realized_profit'][i] != '':
                    flag['profit'][p] += float(position_book[p]['realized_profit'][i])
            take_profit_max()
            if p == 0:
                positionbook_display[p] = 2
            else:
                positionbook_display[p] = 3 + positionbook_display[p-1] + len(position_book[p-1])
                position.range('A' + str(positionbook_display[p] - 2)).value = white_space
            position.range('A' + str(positionbook_display[p])).options(index=False).value = position_book[p]
            position.range('A' + str(positionbook_display[p]-1)).value = client['Client_ID'].iloc[p]
            position.range('G' + str(positionbook_display[p]-1)).value = balance[p]['equity']['used_margin']
            position.range('L' + str(positionbook_display[p]-1)).value = balance[p]['equity']['available_margin']
            position.range('F' + str(positionbook_display[p]-1)).value = 'Used'
            position.range('K' + str(positionbook_display[p]-1)).value = 'Available'
            position.range('S' + str(positionbook_display[p]-1)).value = 'Profit'
            position.range('T' + str(positionbook_display[p]-1)).value = flag['profit'][p]
            sheet.range('U' + str(trade_table_display[p] - 1)).value = flag['profit'][p]
            if flag['profit'][p] > flag['max_profit'][p]:
                flag['max_profit'][p] = flag['profit'][p]
                # flag['profit_time'][p] = str(datetime.now().time())
            elif flag['profit'][p] < flag['max_loss'][p]:
                flag['max_loss'][p] = flag['profit'][p]
                # flag['loss_time'][p] = str(datetime.now().time())
            sheet.range('K' + str(trade_table_display[p] - 1)).value = 'M.Profit'
            sheet.range('P' + str(trade_table_display[p] - 1)).value = 'M.Loss'
            sheet.range('L' + str(trade_table_display[p] - 1)).value = flag['max_profit'][p]
            sheet.range('Q' + str(trade_table_display[p] - 1)).value = flag['max_loss'][p]
            # sheet.range('M' + str(trade_table_display[p] - 1)).value = flag['profit_time'][p]
            # sheet.range('R' + str(trade_table_display[p] - 1)).value = flag['loss_time'][p]
            # for index, time in enumerate(flag.profit_time): flag.profit_time[index] = time.isoformat()
            flags.range('A2').options(index=False).value = flag
        except Exception as e:
            print(f'display_trade_position error in {p}: ', e)

def display_trade_book():
    global trade_book, tradebook_display
    for t in range(len(client)):
        try:
            trade_book[t] = pd.DataFrame(u[t].get_trade_book())
            if t == 0:
                tradebook_display[t] = 2
            else:
                tradebook_display[t] = 3 + tradebook_display[t-1] + len(trade_book[t-1])
                trade.range('A' + str(tradebook_display[t] - 2)).value = white_space
            trade_book[t] = trade_book[t][['exchange', 'token', 'symbol', 'product', 'order_type', 'transaction_type', 'traded_quantity', 'exchange_order_id', 'order_id',  'exchange_time', 'time_in_micro', 'traded_price', 'trade_id', 'user_comment', 'trading_symbol']]
            trade.range('A' + str(tradebook_display[t])).options(index=False).value = trade_book[t]
        except Exception as e:
            print(f'display_trade_book error in {t}: ', e)

def display_order():
    global order_book, orderbook_display
    # print('Starting order fetch')
    for o in range(len(client)):
        try:
            order_book[o] = pd.DataFrame(u[o].get_order_history())
            if o == 0:
                orderbook_display[o] = 2
            else:
                orderbook_display[o] = 3 + orderbook_display[o-1] + len(order_book[o-1])
                orders.range('A' + str(orderbook_display[o] - 2)).value = white_space
            try:
                order_book[o] = order_book[o][['client_id', 'symbol', 'time_in_micro', 'order_type', 'price', 'quantity', 'transaction_type', 'average_price', 'traded_quantity', 'order_id', 'status']]
                orders.range('A' + str(orderbook_display[o])).options(index=False).value = order_book[o]
            except Exception as e:
                print(f'orderbook empty in {o}:', e)
        except Exception as e:
            print(f'display_order error in {o}: ', e)
    print('Order update done')

def balance_status():
    global balance
    for c in range(len(client)):
        try:
            if balance[c]['equity']['available_margin'] < 0:
                print('Balance NEGATIVE in ', c, balance[c]['equity']['available_margin'])
                closing(c)
                position_book[c] = pd.DataFrame(u[c].get_positions())
                for i in range (len(position_book[c])):
                    if position_book[c]['unrealized_profit'][i] != '':
                        try:
                            if position_book[c]['net_quantity'][i] < 0:
                                u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(position_book[c]['exchange'][i],position_book[c]['symbol'][i]),
                                    abs(int(position_book[c]['net_quantity'][i])),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                        except Exception as e:
                            print(e, c, i)
                for i in range (len(position_book[c])):
                    if position_book[c]['unrealized_profit'][i] != '':
                        try:
                            if position_book[c]['net_quantity'][i] > 0:
                                u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(position_book[c]['exchange'][i],position_book[c]['symbol'][i]),
                                    int(position_book[c]['net_quantity'][i]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                        except Exception as e:
                            print(e, c, i)
                fresh_setup_delta_ironfly(c)
            elif balance[c]['equity']['available_margin'] < client['D20ironfly'].iloc[c] * 12500:
                print('Balance LOW in ', c, balance[c]['equity']['available_margin'])
        except Exception as e:
            print('Error getting balance in', c, e)

def round2(x):
    return(round(x * 2, 1) / 2)

def position_holding():
    global position_book, tradingsymbol, qty, exchange, SL_qty, Entry_status, Entry_bid, Trade, product, order_id, days_left, flag
    global strategy, SL_price, Target1, order_placed, Tgt1_status, SL_status, last_tgt, last_qty, rank, order_rej, strike, prem, SL_D_price
    today = datetime.today().weekday()
    todayte = datetime.today()
    cmon = todayte.month
    thursday = 10 - today
    if thursday >= 7:
        thursday -= 7
    last_thursday = 1
    for i in range(1, 6):
        t = todayte + relativedelta(weekday=TH(i))
        if t.month != cmon:
            t = t + relativedelta(weekday=TH(-2))
            last_thursday = t.day
            print('last thurday of month is', last_thursday)
            break
    for p in range(len(client)):
        print('Extracting position')
        position_book[p] = pd.DataFrame(u[p].get_positions())
        # print(position_book[p])
        for r in range(len(position_book[p])):
            if position_book[p]['cf_buy_quantity'][r] != position_book[p]['cf_sell_quantity'][r]:
                if position_book[p]['symbol'][r][:4] == 'NIFT' or position_book[p]['symbol'][r][:4] == 'BANK':
                    order_placed = 'YES'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    last_tgt = last_qty = 'OPEN'
                    if position_book[p]['cf_buy_quantity'][r] - position_book[p]['cf_sell_quantity'][r] < 0:
                        tradingsymbol = position_book[p]['symbol'][r]
                        SL_qty = qty = position_book[p]['cf_sell_quantity'][r] - position_book[p]['cf_buy_quantity'][r]
                        exchange = position_book[p]['exchange'][r]
                        Entry_status = 'Executed'
                        Entry_bid = float(position_book[p]['cf_avg_price'][r])
                        Trade = 'SELL @'
                        if client['3ironfly'].iloc[p] >= 1:
                            strategy = '3IRONFLY'
                        elif client['D20ironfly'].iloc[p] >= 1:
                            strategy = 'D20ironfly'
                        SL_price = SL_D_price = 'Nil'
                        if 'BANK' in tradingsymbol:
                            DD = tradingsymbol[-9:-7]
                            YY = tradingsymbol[9:11]
                            YYYY = 2000 + int(YY)
                            if len(tradingsymbol) == 21:
                                MM = tradingsymbol[11]
                                if any(map(str.isdigit, DD)):
                                    DD = last_thursday
                                    MM = cmon
                            else:
                                MM = tradingsymbol[11:13]
                        elif 'NIFTY' in tradingsymbol:
                            DD = tradingsymbol[-9:-7]
                            YY = tradingsymbol[5:7]
                            YYYY = 2000 + int(YY)
                            if len(tradingsymbol) == 17:
                                MM = tradingsymbol[7]
                                if any(map(str.isdigit, DD)):
                                    DD = last_thursday
                                    MM = cmon
                            else:
                                MM = tradingsymbol[7:9]
                        days_left = datetime(YYYY, MM, DD, 15, 30)
                        if 'CE' in tradingsymbol:
                            rank = 'D20c'
                        else:
                            rank = 'D20p'
                        Target1 = 2
                        strike = tradingsymbol[-7:-2]
                        prem = ''
                        product = position_book[p]['product'][r]
                        order_rej = 'NO'
                        order_id = ''
                        print(tradingsymbol, 'trade')
                        append_excel_table(p)
                    else:
                        tradingsymbol = position_book[p]['symbol'][r]
                        SL_qty = qty = position_book[p]['cf_buy_quantity'][r] - position_book[p]['cf_sell_quantity'][r]
                        exchange = position_book[p]['exchange'][r]
                        Entry_status = 'Executed'
                        Entry_bid = float(position_book[p]['cf_avg_price'][r])
                        Trade = 'BUY @'
                        if 'CE' in tradingsymbol:
                            rank = 'D10c'
                        else:
                            rank = 'D10p'
                        if client['3ironfly'].iloc[p] >= 1:
                            strategy = '3IRONFLY'
                        elif client['D20ironfly'].iloc[p] >= 1:
                            strategy = 'D20ironfly'
                        SL_price = SL_D_price = 0
                        Target1 = 500
                        if 'BANK' in tradingsymbol:
                            DD = tradingsymbol[-9:-7]
                            YY = tradingsymbol[9:11]
                            YYYY = 2000 + int(YY)
                            if len(tradingsymbol) == 21:
                                MM = tradingsymbol[11]
                                if any(map(str.isdigit, DD)):
                                    DD = last_thursday
                                    MM = cmon
                            else:
                                MM = tradingsymbol[11:13]
                        elif 'NIFTY' in tradingsymbol:
                            DD = tradingsymbol[-9:-7]
                            YY = tradingsymbol[5:7]
                            YYYY = 2000 + int(YY)
                            if len(tradingsymbol) == 17:
                                MM = tradingsymbol[7]
                                if any(map(str.isdigit, DD)):
                                    DD = last_thursday
                                    MM = cmon
                            else:
                                MM = tradingsymbol[7:9]
                        days_left = datetime(YYYY, MM, DD, 15, 30)
                        strike = tradingsymbol[-7:-2]
                        prem = 0
                        product = position_book[p]['product'][r]
                        order_rej = 'NO'
                        order_id = ''
                        print(tradingsymbol, 'trade')
                        append_excel_table(p)
                    print(trade_table[p])
    exchange = 'NSE_FO'
    flags.range('A2').options(index=False).value = flag

def d(sigma, S, K, r, t):
    sigma = sigma / 100
    # print(t)
    d1 = 1 / (sigma * np.sqrt(t)) * ( np.log(S/K) + (r + sigma**2/2) * t)
    # print(d1)
    d2 = d1 - sigma * np.sqrt(t)
    return d1, d2

def delta(d_1, contract_type):
    if 'CE' in contract_type:
        return norm.cdf(d_1)
    if 'PE' in contract_type:
        return -norm.cdf(-d_1)

def delta_strike(expiry, deltas, expiry_time):
    if 'BANK' in expiry:
        try:
            last_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
        except Exception as e:
            print(e)
            data_bank = s.get_ohlc(
                s.get_instrument_by_symbol(
                    'NSE_INDEX', 'NIFTY_BANK'
                    ),
                OHLCInterval.Minute_1, datetime.strptime(
                    '{}'.format(from_date), '%d/%m/%Y'
                    ).date(), datetime.strptime(
                        '{}'.format(to_date), '%d/%m/%Y'
                        ).date())
            data_bank = pd.DataFrame(data_bank)
            data_bank = data_bank.astype(
                {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
            last_price = data_bank['close'].iloc[-1]
        last_price_0 = round(last_price/100) * 100
        strike_ce = [(last_price_0 - 100), last_price_0, (last_price_0 + 100), (last_price_0 + 200), (last_price_0 + 300), (last_price_0 + 400), (last_price_0 + 500), (last_price_0 + 600), (last_price_0 + 700), (last_price_0 + 800), (last_price_0 + 900), (last_price_0 + 1000), (last_price_0 + 1100), (last_price_0 + 1200), (last_price_0 + 1300), (last_price_0 + 1400), (last_price_0 + 1500), (last_price_0 + 1600), (last_price_0 + 1700), (last_price_0 + 1800), (last_price_0 + 1900), (last_price_0 + 2000), (last_price_0 + 2100), (last_price_0 + 2200), (last_price_0 + 2300), (last_price_0 + 2400), (last_price_0 + 2500), (last_price_0 + 2600), (last_price_0 + 2700), (last_price_0 + 2800), (last_price_0 + 2900), (last_price_0 + 3000), (last_price_0 + 3100)]
        strike_pe = [(last_price_0 + 100), last_price_0, (last_price_0 - 100), (last_price_0 - 200), (last_price_0 - 300), (last_price_0 - 400), (last_price_0 - 500), (last_price_0 - 600), (last_price_0 - 700), (last_price_0 - 800), (last_price_0 - 900), (last_price_0 - 1000), (last_price_0 - 1100), (last_price_0 - 1200), (last_price_0 - 1300), (last_price_0 - 1400), (last_price_0 - 1500), (last_price_0 - 1600), (last_price_0 - 1700), (last_price_0 - 1800), (last_price_0 - 1900), (last_price_0 - 2000), (last_price_0 - 2100), (last_price_0 - 2200), (last_price_0 - 2300), (last_price_0 - 2400), (last_price_0 - 2500), (last_price_0 - 2600), (last_price_0 - 2700), (last_price_0 - 2800), (last_price_0 - 2900), (last_price_0 - 3000), (last_price_0 - 3100), (last_price_0 - 3200), (last_price_0 - 3300), (last_price_0 - 3400), (last_price_0 - 3500), (last_price_0 - 3600)]
    else:
        last_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_50'), LiveFeedType.LTP)['ltp']
        last_price_0 = round(last_price/50) * 50
        strike_ce = [(last_price_0 - 50), last_price_0, (last_price_0 + 50), (last_price_0 + 100), (last_price_0 + 150), (last_price_0 + 200), (last_price_0 + 250), (last_price_0 + 300), (last_price_0 + 350), (last_price_0 + 400), (last_price_0 + 450), (last_price_0 + 500), (last_price_0 + 550), (last_price_0 + 600), (last_price_0 + 650), (last_price_0 + 700), (last_price_0 + 750), (last_price_0 + 800), (last_price_0 + 850), (last_price_0 + 900), (last_price_0 + 950), (last_price_0 + 1000), (last_price_0 + 1050), (last_price_0 + 1100), (last_price_0 + 1150), (last_price_0 + 1200), (last_price_0 + 1250)]
        strike_pe = [(last_price_0 + 50), last_price_0, (last_price_0 - 50), (last_price_0 - 100), (last_price_0 - 150), (last_price_0 - 200), (last_price_0 - 250), (last_price_0 - 300), (last_price_0 - 350), (last_price_0 - 400), (last_price_0 - 450), (last_price_0 - 500), (last_price_0 - 550), (last_price_0 - 600), (last_price_0 - 650), (last_price_0 - 700), (last_price_0 - 750), (last_price_0 - 800), (last_price_0 - 850), (last_price_0 - 900), (last_price_0 - 950), (last_price_0 - 1000), (last_price_0 - 1050), (last_price_0 - 1100), (last_price_0 - 1150), (last_price_0 - 1200), (last_price_0 - 1250)]
    totime = datetime.now()
    t1 = expiry_time - totime
    a = t1/timedelta(days=1)
    tg = float(a/365)
    buff2 = 0
    if deltas > 0:
        print('for new call')
        for strike in strike_ce:
            symbol = expiry + str(strike) + 'CE'
            print(symbol)
            # ltp = s.get_live_feed(s.get_instrument_by_symbol('NSE_FO', symbol), LiveFeedType.LTP)['ltp']
            try:
                data = s.get_ohlc(
                    s.get_instrument_by_symbol(
                        'NSE_FO', symbol
                        ),
                    OHLCInterval.Minute_1, datetime.strptime(
                        '{}'.format(from_date), '%d/%m/%Y'
                        ).date(), datetime.strptime(
                            '{}'.format(to_date), '%d/%m/%Y'
                            ).date())
                data = pd.DataFrame(data)
                data = data.astype(
                    {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
            except Exception as e:
                print(e, 'Data not found')
                continue
            ltp = data['close'].iloc[-1]
            IV = iv(symbol, strike, ltp, last_price, tg)
            # print(IV, 'is IV')
            d1, d2 = d(IV, last_price, strike, 0.1, tg)
            delta1 = delta(d1, symbol)
            print(delta1, 'is delta for', symbol)
            if deltas > delta1:
                buff1 = delta1
                if buff2 - deltas > deltas - buff1:
                    return strike, symbol
                else:
                    if 'BANK' in symbol:
                        symbol = expiry + str(strike - 100) + 'CE'
                        strike -= 100
                        return strike, symbol 
                    else:
                        symbol = expiry + str(strike - 50) + 'CE'
                        strike -= 50
                        return strike, symbol
            else:
                buff2 = delta1
    else:
        print('for new put')
        for strike in strike_pe:
            symbol = expiry + str(strike) + 'PE'
            # ltp = s.get_live_feed(s.get_instrument_by_symbol('NSE_FO', symbol), LiveFeedType.LTP)['ltp']
            try:
                data = s.get_ohlc(
                    s.get_instrument_by_symbol(
                        'NSE_FO', symbol
                        ),
                    OHLCInterval.Minute_1, datetime.strptime(
                        '{}'.format(from_date), '%d/%m/%Y'
                        ).date(), datetime.strptime(
                            '{}'.format(to_date), '%d/%m/%Y'
                            ).date())
                data = pd.DataFrame(data)
                data = data.astype(
                    {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
            except Exception as e:
                print(e, 'Data not found')
                continue
            ltp = data['close'].iloc[-1]
            IV = iv(symbol, strike, ltp, last_price, tg)
            d1, d2 = d(IV, last_price, strike, 0.1, tg)
            delta1 = delta(d1, symbol)
            if deltas < delta1:
                buff1 = delta1
                if buff2 + deltas < deltas + buff1:
                    print(symbol)
                    return strike, symbol
                else:
                    if 'BANK' in symbol:
                        symbol = expiry + str(strike + 100) + 'PE'
                        strike += 100
                        print(symbol)
                        return strike, symbol
                    else:
                        symbol = expiry + str(strike + 50) + 'PE'
                        strike += 50
                        print(symbol)
                        return strike, symbol
            else:
                buff2 = delta1

def rsi_update():
    global bank_rsi, bank_rsi_prev
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    print('RSI checking')
    if time(9, 20) <= datetime.now().time():
        try:
            bank_data = s.get_ohlc(
                s.get_instrument_by_symbol(
                    'nse_index', 'NIFTY_BANK'
                    ),
                OHLCInterval.Minute_5, datetime.strptime(
                    '{}'.format(from_date), '%d/%m/%Y'
                    ).date(), datetime.strptime(
                        '{}'.format(to_date), '%d/%m/%Y'
                        ).date())
        except Exception as e:
            print('Error in getting OHLC for RSI', e)
            return
        bank_data = pd.DataFrame(bank_data)
        bank_data = bank_data.astype(
            {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
        bank_data['rsi'] = RSI(bank_data['close'], 21)
        bank_rsi = bank_data['rsi'].iloc[-1]
        bank_rsi_prev = bank_data['rsi'].iloc[-2]
        if time(9, 20) <= datetime.now().time() <= time(9, 22):
            bank_rsi_prev = bank_data['rsi'].iloc[-3]
        if bank_rsi >= 66 and bank_rsi_prev < 66:
            for c in range(len(client)):
                if (client['D20ironfly'].iloc[c] >= 1 or client['batman'].iloc[c] >= 1) and client['banknifty'].iloc[c] == 1 and flag['rsi'][c] <= 0:
                    try:
                        flag['rsi'][c] = 1
                        # if client['D20ironfly'].iloc[c] >= 1:
                        #     rank = 'D20c'
                        #     qty = SL_qty = int(int(client['D20ironfly'].iloc[c] / 2) * 25)
                        # elif client['batman'].iloc[c] >= 1:
                        #     rank = 'B30c'
                        #     qty = SL_qty = int(client['batman'].iloc[c] * 25)
                        # ind = (trade_table[c][trade_table[c]['rank'] == rank]
                        #     [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        # Trade = 'BUY @'
                        # strategy = 'RSI'
                        # order_placed = 0
                        # SL_D_price = 'Nil'
                        # prem = 0
                        # Target1 = 'Nil'
                        # SL_price = 'Nil'
                        # Entry_status = 'Ordered'
                        # Tgt1_status = SL_status = 'NOT EXEC'
                        # order_rej = 'NO'
                        # last_tgt = last_qty = 'OPEN'
                        # product = 'D'
                        # strike = trade_table[c]['strike'][ind]
                        # tradingsymbol = trade_table[c]['symbol'][ind]
                        # days_left = trade_table[c]['days_left'][ind]
                        # rank = 'RSI'
                        # data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                        # Entry_bid = data['bids'][0]['price'] + 0.05
                        # order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        #     qty,OrderType.Market,ProductType.Delivery,
                        #     0.0,None,0,DurationType.DAY,None,None,None)
                        # order_id = order_id1['order_id']
                        # append_excel_table(c)
                        try:
                            ind20c = (trade_table[c][trade_table[c]['rank'] == 'RSI20C']
                                [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                            ind10c = (trade_table[c][trade_table[c]['rank'] == 'RSI10C']
                                [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        except:
                            print('No existing RSI20C available')
                            continue
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                            int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind20c] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                        trade_table[c]['Entry_status'][ind20c] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                        trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                        trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                        trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                            int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind10c] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                        trade_table[c]['Entry_status'][ind10c] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                        trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                        trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                        trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
                    except Exception as e:
                        print('RSI Not complete for', c, e)
        elif bank_rsi <= 34 and bank_rsi_prev > 34:
            for c in range(len(client)):
                if (client['D20ironfly'].iloc[c] >= 1 or client['batman'].iloc[c] >= 1) and client['banknifty'].iloc[c] == 1 and flag['rsi'][c] >= 0:
                    flag['rsi'][c] = -1
                    # if client['D20ironfly'].iloc[c] >= 1:
                    #     rank = 'D20p'
                    #     qty = SL_qty = int(int(client['D20ironfly'].iloc[c] / 2) * 25)
                    # elif client['batman'].iloc[c] >= 1:
                    #     rank = 'B30p'
                    #     qty = SL_qty = int(client['batman'].iloc[c] * 25)
                    # ind = (trade_table[c][trade_table[c]['rank'] == rank]
                    #     [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    # Trade = 'BUY @'
                    # strategy = 'RSI'
                    # order_placed = 0
                    # SL_D_price = 'Nil'
                    # prem = 0
                    # Target1 = 'Nil'
                    # SL_price = 'Nil'
                    # Entry_status = 'Ordered'
                    # Tgt1_status = SL_status = 'NOT EXEC'
                    # order_rej = 'NO'
                    # last_tgt = last_qty = 'OPEN'
                    # product = 'D'
                    # strike = trade_table[c]['strike'][ind]
                    # tradingsymbol = trade_table[c]['symbol'][ind]
                    # days_left = trade_table[c]['days_left'][ind]
                    # rank = 'RSI'
                    # data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    # Entry_bid = data['bids'][0]['price'] + 0.05
                    # order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    #     qty,OrderType.Market,ProductType.Delivery,
                    #     0.0,None,0,DurationType.DAY,None,None,None)
                    # order_id = order_id1['order_id']
                    # append_excel_table(c)
                    try:
                        ind20p = (trade_table[c][trade_table[c]['rank'] == 'RSI20P']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        ind10p = (trade_table[c][trade_table[c]['rank'] == 'RSI10P']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    except:
                        print('No existing RSI20P available')
                        continue
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                        int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                    trade_table[c]['SL_status'][ind20p] = 'Closed'
                    trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                    trade_table[c]['Entry_status'][ind20p] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                    trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                    trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                    trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                    trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                        int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                    trade_table[c]['SL_status'][ind10p] = 'Closed'
                    trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                    trade_table[c]['Entry_status'][ind10p] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                    trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                    trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                    trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                    trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
        elif (bank_rsi <= 64 and bank_rsi_prev > 64) or (bank_rsi <= 64 and flag['rsi'].max() == 1):
            for c in range(len(client)):
                if (client['D20ironfly'].iloc[c] >= 1 or client['batman'].iloc[c] >= 1) and client['banknifty'].iloc[c] == 1 and flag['rsi'][c] == 1:
                    flag['rsi'][c] = 0
                    # try:
                    #     ind = (trade_table[c][trade_table[c]['rank'] == 'RSI']
                    #         [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    # except:
                    #     continue
                    # order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                    #     int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                    #     0.0,None,0,DurationType.DAY,None,None,None)
                    # order_id = order_id1['order_id']
                    # trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                    # trade_table[c]['SL_status'][ind] = 'Closed'
                    # trade_table[c]['3pm_tgt'][ind] = 'Closed'
                    # trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                    # trade_table[c]['Entry_status'][ind] = 'Closed'
                    # order = pd.DataFrame(u[c].get_order_history())
                    # index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                    # trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                    # trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                    # trade_table[c]['SL_qty'][ind] = 0
                    # trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        expiry = week0b
                    else:
                        expiry = week1b #trade_table[c]['symbol'][ind][:-7]
                    try:
                        strike1, tradingsymbol1 = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                        strike, tradingsymbol = delta_strike(expiry, 0.07, trade_table[c]['days_left'][ind])
                    except:
                        continue
                    if strike < strike1 + 300:
                        strike = strike1 + 300
                        tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                    rank = 'RSI10C'
                    Trade = 'BUY @'
                    strategy = trade_table[c]['strategy'][ind]
                    order_placed = 0
                    SL_D_price = 'Nil'
                    prem = 0
                    Target1 = 2
                    SL_price = 'Nil'
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    last_tgt = last_qty = 'OPEN'
                    product = 'D'
                    days_left = trade_table[c]['days_left'][ind]
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['bids'][0]['price'] + 0.05
                    if client['D20ironfly'].iloc[c] >= 1:
                        qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                    else:
                        qty = SL_qty = int(client['batman'].iloc[c] * 15)
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                    if strike < trade_table[c]['strike'][ind]:
                        strike = trade_table[c]['strike'][ind]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                    rank = 'RSI20C'
                    Trade = 'SELL @'
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['asks'][0]['price'] - 0.05
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    order = pd.DataFrame(u[c].get_order_history())
                    index = order[order['order_id'] == int(order_id)].index[0]
                    if order['status'].iloc[index] == 'rejected':
                        print('Order rejected')
                        ind = (trade_table[c][trade_table[c]['rank'] == 'RSI20C']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Rejected'
                        trade_table[c]['R.Profit'][ind] = 0
                        trade_table[c]['Profit'][ind] = 0
                        ind10c = (trade_table[c][trade_table[c]['rank'] == 'RSI10C']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                            int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind10c] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                        trade_table[c]['Entry_status'][ind10c] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                        trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                        trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                        trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
        elif (bank_rsi >= 36 and bank_rsi_prev < 36) or (bank_rsi >= 36 and flag['rsi'].min() == -1):
            for c in range(len(client)):
                if (client['D20ironfly'].iloc[c] >= 1 or client['batman'].iloc[c] >= 1) and client['banknifty'].iloc[c] == 1 and flag['rsi'][c] == -1:
                    flag['rsi'][c] = 0
                    # try:
                    #     ind = (trade_table[c][trade_table[c]['rank'] == 'RSI']
                    #         [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    # except:
                    #     continue
                    # order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                    #     int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                    #     0.0,None,0,DurationType.DAY,None,None,None)
                    # order_id = order_id1['order_id']
                    # trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                    # trade_table[c]['SL_status'][ind] = 'Closed'
                    # trade_table[c]['3pm_tgt'][ind] = 'Closed'
                    # trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                    # trade_table[c]['Entry_status'][ind] = 'Closed'
                    # order = pd.DataFrame(u[c].get_order_history())
                    # index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                    # trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                    # trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                    # trade_table[c]['SL_qty'][ind] = 0
                    # trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        expiry = week0b #trade_table[c]['symbol'][ind][:-7]
                    else:
                        expiry = week1b
                    try:
                        strike1, tradingsymbol1 = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                        strike, tradingsymbol = delta_strike(expiry, -0.07, trade_table[c]['days_left'][ind])
                    except:
                        continue
                    if strike > strike1 - 300:
                        strike = strike1 - 300
                        tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                    rank = 'RSI10P'
                    Trade = 'BUY @'
                    strategy = trade_table[c]['strategy'][ind]
                    order_placed = 0
                    SL_D_price = 'Nil'
                    prem = 0
                    Target1 = 2
                    SL_price = 'Nil'
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    last_tgt = last_qty = 'OPEN'
                    product = 'D'
                    days_left = trade_table[c]['days_left'][ind]
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['bids'][0]['price'] + 0.05
                    if client['D20ironfly'].iloc[c] >= 1:
                        qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                    else:
                        qty = SL_qty = int(client['batman'].iloc[c] * 15)
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                    if strike > trade_table[c]['strike'][ind]:
                        strike = trade_table[c]['strike'][ind]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                    rank = 'RSI20P'
                    Trade = 'SELL @'
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['asks'][0]['price'] - 0.05
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    order = pd.DataFrame(u[c].get_order_history())
                    index = order[order['order_id'] == int(order_id)].index[0]
                    if order['status'].iloc[index] == 'rejected':
                        print('Order rejected')
                        ind = (trade_table[c][trade_table[c]['rank'] == 'RSI20P']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Rejected'
                        trade_table[c]['R.Profit'][ind] = 0
                        trade_table[c]['Profit'][ind] = 0
                        ind10p = (trade_table[c][trade_table[c]['rank'] == 'RSI10P']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                            int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind10p] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                        trade_table[c]['Entry_status'][ind10p] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                        trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                        trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                        trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
        elif bank_rsi <= 50 and bank_rsi_prev > 50:
            for c in range(len(client)):
                try:
                    ind20c = (trade_table[c][trade_table[c]['rank'] == 'RSI20C']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    ind10c = (trade_table[c][trade_table[c]['rank'] == 'RSI10C']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                except:
                    continue
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                trade_table[c]['SL_status'][ind20c] = 'Closed'
                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                trade_table[c]['SL_status'][ind10c] = 'Closed'
                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
        elif bank_rsi >= 50 and bank_rsi_prev < 50:
            for c in range(len(client)):
                try:
                    ind20p = (trade_table[c][trade_table[c]['rank'] == 'RSI20P']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    ind10p = (trade_table[c][trade_table[c]['rank'] == 'RSI10P']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                except:
                    continue
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                trade_table[c]['SL_status'][ind20p] = 'Closed'
                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                trade_table[c]['SL_status'][ind10p] = 'Closed'
                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
        for c in range(len(client)):
            try:
                ind20c = (trade_table[c][trade_table[c]['rank'] == 'D20c']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                option_data = s.get_ohlc(
                    s.get_instrument_by_symbol(
                        'nse_fo', trade_table[c]['symbol'][ind20c]
                        ),
                    OHLCInterval.Minute_5, datetime.strptime(
                        '{}'.format(from_date), '%d/%m/%Y'
                        ).date(), datetime.strptime(
                            '{}'.format(to_date), '%d/%m/%Y'
                            ).date())
                option_data = pd.DataFrame(option_data)
                option_data = option_data.astype(
                    {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
                option_data['rsi'] = RSI(option_data['close'], 21)
                option_rsi = option_data['rsi'].iloc[-1]
                option_rsi_prev = option_data['rsi'].iloc[-2]
                if time(9, 20) <= datetime.now().time() <= time(9, 22):
                    option_rsi_prev = option_data['rsi'].iloc[-3]
                if option_rsi >= 62 and option_rsi_prev < 62:
                    if client['optionrsi'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1 and flag['rsi_ce'][c] <= 0:
                        flag['rsi_ce'][c] = 1
                        if client['D20ironfly'].iloc[c] >= 1:
                            qty = SL_qty = int(client['optionrsi'].iloc[c] * 15)
                        Trade = 'BUY @'
                        strategy = 'RSI_CE'
                        order_placed = 0
                        SL_D_price = 'Nil'
                        prem = 0
                        Target1 = 'Nil'
                        SL_price = 'Nil'
                        Entry_status = 'Ordered'
                        Tgt1_status = SL_status = 'NOT EXEC'
                        order_rej = 'NO'
                        last_tgt = last_qty = 'OPEN'
                        product = 'D'
                        strike = trade_table[c]['strike'][ind20c]
                        tradingsymbol = trade_table[c]['symbol'][ind20c]
                        days_left = trade_table[c]['days_left'][ind20c]
                        rank = 'RSI_CE'
                        data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                        Entry_bid = data['bids'][0]['price'] + 0.05
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            qty,OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                elif (option_rsi <= 60 and option_rsi_prev > 60) or (option_rsi <= 65 and option_rsi_prev > 65):
                    if flag['rsi_ce'][c] == 1:
                        flag['rsi_ce'][c] = 0
                        try:
                            ind = (trade_table[c][trade_table[c]['rank'] == 'RSI_CE']
                                [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        except:
                            continue
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                        trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
            except Exception as e:
                print('RSI_CE Not complete for', c, e)
            try:
                ind20p = (trade_table[c][trade_table[c]['rank'] == 'D20p']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                option_data = s.get_ohlc(
                    s.get_instrument_by_symbol(
                        'nse_fo', trade_table[c]['symbol'][ind20p]
                        ),
                    OHLCInterval.Minute_5, datetime.strptime(
                        '{}'.format(from_date), '%d/%m/%Y'
                        ).date(), datetime.strptime(
                            '{}'.format(to_date), '%d/%m/%Y'
                            ).date())
                option_data = pd.DataFrame(option_data)
                option_data = option_data.astype(
                    {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
                option_data['rsi'] = RSI(option_data['close'], 21)
                option_rsi = option_data['rsi'].iloc[-1]
                option_rsi_prev = option_data['rsi'].iloc[-2]
                if time(9, 20) <= datetime.now().time() <= time(9, 22):
                    option_rsi_prev = option_data['rsi'].iloc[-3]
                if option_rsi >= 62 and option_rsi_prev < 62:
                    if client['optionrsi'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1 and flag['rsi_pe'][c] <= 0:
                        flag['rsi_pe'][c] = 1
                        if client['D20ironfly'].iloc[c] >= 1:
                            qty = SL_qty = int(client['optionrsi'].iloc[c] * 15)
                        Trade = 'BUY @'
                        strategy = 'RSI_PE'
                        order_placed = 0
                        SL_D_price = 'Nil'
                        prem = 0
                        Target1 = 'Nil'
                        SL_price = 'Nil'
                        Entry_status = 'Ordered'
                        Tgt1_status = SL_status = 'NOT EXEC'
                        order_rej = 'NO'
                        last_tgt = last_qty = 'OPEN'
                        product = 'D'
                        strike = trade_table[c]['strike'][ind20p]
                        tradingsymbol = trade_table[c]['symbol'][ind20p]
                        days_left = trade_table[c]['days_left'][ind20p]
                        rank = 'RSI_PE'
                        data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                        Entry_bid = data['bids'][0]['price'] + 0.05
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            qty,OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                elif (option_rsi <= 60 and option_rsi_prev > 60) or (option_rsi <= 65 and option_rsi_prev > 65):
                    if flag['rsi_pe'][c] == 1:
                        flag['rsi_pe'][c] = 0
                        try:
                            ind = (trade_table[c][trade_table[c]['rank'] == 'RSI_PE']
                                [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        except:
                            continue
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                        trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
            except Exception as e:
                print('RSI_PE Not complete for', c, e)
    bankfuture_5()
    chart()

def bankfuture_change(timeframe, Multiplier):
    global sti
    if timeframe == 'Minute_5':
        interval = OHLCInterval.Minute_5
    elif timeframe == 'Minute_15':
        interval = OHLCInterval.Minute_15
    elif timeframe == 'Minute_60':
        interval = OHLCInterval.Minute_60
    # elif timeframe == 'Day_1':
    #     interval = OHLCInterval.Day_1
    tradingsymbol = month1b + 'FUT'
    try:
        data = s.get_ohlc(
            s.get_instrument_by_symbol(
                'NSE_FO', tradingsymbol
                ),
            interval, datetime.strptime(
                '{}'.format(from_date), '%d/%m/%Y'
                ).date(), datetime.strptime(
                    '{}'.format(to_date), '%d/%m/%Y'
                    ).date())
    except Exception as e:
        print(e)
    data = pd.DataFrame(data)
    data = data.astype(
        {'open': float, 'high': float, 'low': float, 'close': float})
    sti = ta.supertrend(data['high'], data['low'], data['close'], 5, Multiplier)
    if Multiplier == 1:
        if sti['SUPERTd_5_1.0'].iloc[-1] != sti['SUPERTd_5_1.0'].iloc[-2]:
            return(sti['SUPERTd_5_1.0'].iloc[-1])
        else:
            return(sti['SUPERT_5_1.0'].iloc[-1])
    elif Multiplier == 2:
        if sti['SUPERTd_5_2.0'].iloc[-1] != sti['SUPERTd_5_2.0'].iloc[-2]:
            return(sti['SUPERTd_5_2.0'].iloc[-1])
        else:
            return(sti['SUPERT_5_2.0'].iloc[-1])
    elif Multiplier == 3:
        if sti['SUPERTd_5_3.0'].iloc[-1] != sti['SUPERTd_5_3.0'].iloc[-2]:
            return(sti['SUPERTd_5_3.0'].iloc[-1])
        else:
            return(sti['SUPERT_5_3.0'].iloc[-1])
    # elif timeframe == 'Minute_15':
    #     sti = ta.supertrend(data['high'], data['low'], data['close'], 5, 2)
    #     if sti['SUPERTd_5_2.0'].iloc[-1] != sti['SUPERTd_5_2.0'].iloc[-2]:
    #         return(sti['SUPERTd_5_2.0'].iloc[-1])
    #     else:
    #         return(0)
    # else:
    #     sti = ta.supertrend(data['high'], data['low'], data['close'], 5, 1)
    #     if sti['SUPERTd_5_1.0'].iloc[-1] != sti['SUPERTd_5_1.0'].iloc[-2]:
    #         return(sti['SUPERTd_5_1.0'].iloc[-1])  
    #     else:
    #         return(0)

def bankfuture_change1():
    global sti
    interval = OHLCInterval.Day_1
    try:
        data = s.get_ohlc(
            s.get_instrument_by_symbol(
                'nse_index', 'NIFTY_BANK'
                ),
            interval, datetime.strptime(
                '{}'.format(from_date1), '%d/%m/%Y'
                ).date(), datetime.strptime(
                    '{}'.format(to_date), '%d/%m/%Y'
                    ).date())
    except Exception as e:
        print(e)
    data = pd.DataFrame(data)
    data = data.astype(
        {'open': float, 'high': float, 'low': float, 'close': float})
    sti = ta.supertrend(data['high'], data['low'], data['close'], 5, 1)
    if sti['SUPERTd_5_1.0'].iloc[-1] != sti['SUPERTd_5_1.0'].iloc[-2]:
        return(sti['SUPERTd_5_1.0'].iloc[-1])
    else:
        return(0)

def bankfuture_5():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, exchange
    x = bankfuture_change('Minute_5', 1)
    y = bankfuture_change('Minute_5', 2)
    z = bankfuture_change('Minute_5', 3)
    if x==1 or y==1 or z==1 or x==-1 or y==-1 or z==-1:
        for c in range(len(client)):
            if client['future_5'].iloc[c] >= 1:
                try:
                    ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['strategy'] == 'FUT']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == '5min']).index[0]
                except Exception as e:
                    print(e, 'Not found existing trade for 5min Future')
                    print('First trade for 5min Future')
                    tradingsymbol = month1b + 'FUT'
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    qty = SL_qty = client['future_5'].iloc[c] * 15
                    strategy = 'FUT'
                    product = 'D'
                    rank = '5min'
                    strike = 'NA'
                    # exchange = 'NSE_FO'
                    order_placed = 0
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    SL_D_price = 0
                    prem = 0
                    last_tgt = last_qty = 'OPEN'
                    Entry_bid = last_price
                    Target1 = 'Nil'
                    SL_price = 'Nil'
                    if x == 1 or y == 1 or z == 1:
                        Trade = 'BUY @'
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['5min'][c] = client['future_5'].iloc[c]
                    elif x == -1 or y == -1 or z == -1:
                        Trade = 'SELL @'
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['5min'][c] = -client['future_5'].iloc[c]
                    continue
                strike = 'NA'
                # exchange = 'NSE_FO'
                order_placed = 0
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                SL_D_price = 0
                prem = 0
                last_tgt = last_qty = 'OPEN'
                Target1 = 'Nil'
                SL_price = 'Nil'
                strategy = 'FUT'
                product = 'D'
                if x == 1 or y == 1 or z == 1:
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'SELL @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '5min']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        sell_price = trade_table[c]['Entry_price'][ind]
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        if last_price > sell_price:
                            if (x==1 and (last_price < y or last_price < z)) or (y==1 and last_price < z) or (z > last_price):
                                print(last_price, 'Last price')
                                print(sell_price, 'Sell price')
                                print('x=', x)
                                print('y=', y)
                                print('z=', z)
                                return
                        Entry_bid = last_price
                        qty = SL_qty = client['future_5'].iloc[c] * 15
                        rank = '5min'
                        Trade = 'BUY @'
                        trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['5min'][c] = flag['5min'][c] + (client['future_5'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                    except Exception as e:
                        print(e, ind)
                elif x == -1 or y == -1 or z == -1:
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'BUY @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '5min']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        buy_price = trade_table[c]['Entry_price'][ind]
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        if last_price < buy_price:
                            if (x==-1 and (last_price > y > 1 or last_price > z > 1)) or (y==-1 and last_price > z > 1) or (z > 1 and z < last_price):
                                print(last_price, 'Last price')
                                print(buy_price, 'Buy price')
                                print('x=', x)
                                print('y=', y)
                                print('z=', z)
                                return
                        qty = SL_qty = client['future_5'].iloc[c] * 15
                        Entry_bid = last_price
                        rank = '5min'
                        Trade = 'SELL @'
                        if tradingsymbol != month1b + 'FUT':
                            trade_qty = qty
                        else:
                            trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        # append_excel_table(c)
                        flag['5min'][c] = flag['5min'][c] - (client['future_5'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        if tradingsymbol != month1b + 'FUT':
                            tradingsymbol = month1b + 'FUT'
                            last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                                int(trade_qty),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                        append_excel_table(c)
                    except Exception as e:
                        print(e, ind)
    # bankfuture_change('Minute_15')

def bankfuture_15():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, exchange
    x = bankfuture_change('Minute_15', 1)
    y = bankfuture_change('Minute_15', 2)
    if x==1 or y==1 or x==-1 or y==-1:
        for c in range(len(client)):
            print('Executing 15m FUT for client', c)
            if client['future_15'].iloc[c] >= 1:
                try:
                    ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['strategy'] == 'FUT']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == '15min']).index[0]
                except Exception as e:
                    print(e, 'Not found existing trade for 15min Future')
                    print('First trade for 15min Future')
                    tradingsymbol = month1b + 'FUT'
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    qty = SL_qty = client['future_15'].iloc[c] * 15
                    strategy = 'FUT'
                    product = 'D'
                    rank = '15min'
                    strike = 'NA'
                    # exchange = 'NSE_FO'
                    order_placed = 0
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    SL_D_price = 0
                    prem = 0
                    last_tgt = last_qty = 'OPEN'
                    Entry_bid = last_price
                    Target1 = 'Nil'
                    SL_price = 'Nil'
                    if x == 1 or y == 1:
                        Trade = 'BUY @'
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['15min'][c] = client['future_15'].iloc[c]
                    elif x == -1 or y == -1:
                        Trade = 'SELL @'
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['15min'][c] = -client['future_15'].iloc[c]
                    continue
                # for i in range(len(trade_table[c])):
                strike = 'NA'
                # exchange = 'NSE_FO'
                order_placed = 0
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                SL_D_price = 0
                prem = 0
                last_tgt = last_qty = 'OPEN'
                Target1 = 'Nil'
                SL_price = 'Nil'
                strategy = 'FUT'
                product = 'D'
                if x == 1 or y == 1:
                    try:
                        print('Checking existing SELL 15min Future')
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'SELL @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '15min']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        sell_price = trade_table[c]['Entry_price'][ind]
                        print('Found in line', ind)
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        if last_price > sell_price:
                            if (x==1 and last_price < y) or (y > last_price):
                                print(last_price, 'Last price')
                                print(sell_price, 'Sell price')
                                print('x=', x)
                                print('y=', y)
                                return
                        qty = SL_qty = client['future_15'].iloc[c] * 15
                        Entry_bid = last_price
                        rank = '15min'
                        Trade = 'BUY @'
                        trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['15min'][c] = flag['15min'][c] + (client['future_15'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                    except Exception as e:
                        print(e, ind)
                elif x == -1 or y == -1:
                    try:
                        print('Checking existing BUY 15min Future')
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'BUY @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '15min']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        buy_price = trade_table[c]['Entry_price'][ind]
                        print('Found in line', ind)
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        if last_price < buy_price:
                            if (x==-1 and last_price > y > 1) or (y > 1 and y < last_price):
                                print(last_price, 'Last price')
                                print(buy_price, 'Buy price')
                                print('x=', x)
                                print('y=', y)
                                return
                        qty = SL_qty = client['future_15'].iloc[c] * 15
                        rank = '15min'
                        Entry_bid = last_price
                        Trade = 'SELL @'
                        if tradingsymbol != month1b + 'FUT':
                            trade_qty = qty
                        else:
                            trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        # append_excel_table(c)
                        flag['15min'][c] = flag['15min'][c] - (client['future_15'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        if tradingsymbol != month1b + 'FUT':
                            tradingsymbol = month1b + 'FUT'
                            last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                                int(trade_qty),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                        append_excel_table(c)
                    except Exception as e:
                        print(e, ind)

def bankfuture_60():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, exchange
    x = bankfuture_change('Minute_60', 1)
    if x==1 or x==-1:
        for c in range(len(client)):
            if client['future_60'].iloc[c] >= 1:
                try:
                    ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['strategy'] == 'FUT']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == '60min']).index[0]
                except Exception as e:
                    print(e, 'Not found existing trade for 60min Future')
                    print('First trade for 60min Future')
                    tradingsymbol = month1b + 'FUT'
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    qty = SL_qty = client['future_60'].iloc[c] * 15
                    strategy = 'FUT'
                    product = 'D'
                    rank = '60min'
                    strike = 'NA'
                    # exchange = 'NSE_FO'
                    order_placed = 0
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    SL_D_price = 0
                    prem = 0
                    last_tgt = last_qty = 'OPEN'
                    Entry_bid = last_price
                    Target1 = 'Nil'
                    SL_price = 'Nil'
                    if x == 1:
                        Trade = 'BUY @'
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['60min'][c] = client['future_60'].iloc[c]
                    elif x == -1:
                        Trade = 'SELL @'
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['60min'][c] = -client['future_60'].iloc[c]
                    continue
                # for i in range(len(trade_table[c])):
                strike = 'NA'
                # exchange = 'NSE_FO'
                order_placed = 0
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                SL_D_price = 0
                prem = 0
                last_tgt = last_qty = 'OPEN'
                Target1 = 'Nil'
                SL_price = 'Nil'
                strategy = 'FUT'
                product = 'D'
                if x == 1:
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'SELL @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '60min']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        qty = SL_qty = client['future_60'].iloc[c] * 15
                        rank = '60min'
                        Entry_bid = last_price
                        Trade = 'BUY @'
                        trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['60min'][c] = flag['60min'][c] + (client['future_60'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                    except Exception as e:
                        print(e, ind)
                elif x == -1:
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'BUY @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '60min']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        qty = SL_qty = client['future_60'].iloc[c] * 15
                        rank = '60min'
                        Entry_bid = last_price
                        Trade = 'SELL @'
                        if tradingsymbol != month1b + 'FUT':
                            trade_qty = qty
                        else:
                            trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        # append_excel_table(c)
                        flag['60min'][c] = flag['60min'][c] - (client['future_60'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        if tradingsymbol != month1b + 'FUT':
                            tradingsymbol = month1b + 'FUT'
                            last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                                int(trade_qty),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                        append_excel_table(c)
                    except Exception as e:
                        print(e, ind)

def bankfuture_1D():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, exchange
    a = bankfuture_change1()
    if a!=0:
        for c in range(len(client)):
            if client['future_1D'].iloc[c] >= 1:
                try:
                    ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['strategy'] == 'FUT']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == '1day']).index[0]
                except Exception as e:
                    print(e, 'Not found existing trade for 1day Future')
                    print('First trade for 1day Future')
                    tradingsymbol = month1b + 'FUT'
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    qty = SL_qty = client['future_1D'].iloc[c] * 15
                    strategy = 'FUT'
                    product = 'D'
                    rank = '1day'
                    strike = 'NA'
                    # exchange = 'NSE_FO'
                    order_placed = 0
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    SL_D_price = 0
                    prem = 0
                    last_tgt = last_qty = 'OPEN'
                    Entry_bid = last_price
                    Target1 = 'Nil'
                    SL_price = 'Nil'
                    if a > 0:
                        Trade = 'BUY @'
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['1day'][c] = client['future_1D'].iloc[c]
                    elif a < 0:
                        Trade = 'SELL @'
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['1day'][c] = -client['future_1D'].iloc[c]
                    continue
                # for i in range(len(trade_table[c])):
                strike = 'NA'
                order_placed = 0
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                SL_D_price = 0
                prem = 0
                last_tgt = last_qty = 'OPEN'
                Target1 = 'Nil'
                SL_price = 'Nil'
                strategy = 'FUT'
                product = 'D'
                if a > 0:
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'SELL @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '1day']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        qty = SL_qty = client['future_1D'].iloc[c] * 15
                        rank = '1day'
                        Trade = 'BUY @'
                        Entry_bid = last_price
                        trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        append_excel_table(c)
                        flag['1day'][c] = flag['1day'][c] + (client['future_1D'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                    except Exception as e:
                        print(e, ind)
                elif a < 0:
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['strategy'] == 'FUT']
                            [trade_table[c]['trade_type'] == 'BUY @']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == '1day']).index[0]
                        tradingsymbol = trade_table[c]['symbol'][ind]
                        last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                        qty = SL_qty = client['future_1D'].iloc[c] * 15
                        rank = '1day'
                        Trade = 'SELL @'
                        Entry_bid = last_price
                        if tradingsymbol != month1b + 'FUT':
                            trade_qty = qty
                        else:
                            trade_qty = qty * 2
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                            int(trade_qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        # append_excel_table(c)
                        flag['1day'][c] = flag['1day'][c] - (client['future_1D'].iloc[c] * 2)
                        trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print(e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        if tradingsymbol != month1b + 'FUT':
                            tradingsymbol = month1b + 'FUT'
                            last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, tradingsymbol),
                                int(trade_qty),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                        append_excel_table(c)
                    except Exception as e:
                        print(e, ind)

def supertrend():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    print('Supertrend checking')
    if time(9, 20) <= datetime.now().time():
        for c in range(len(client)):
            if client['supertrend'].iloc[c] >= 1:
                try:
                    ind20p = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == 'D20p']).index[0]
                    data = s.get_ohlc(
                        s.get_instrument_by_symbol(
                            'nse_fo', trade_table[c]['symbol'][ind20p]
                            ),
                        OHLCInterval.Minute_5, datetime.strptime(
                            '{}'.format(from_date), '%d/%m/%Y'
                            ).date(), datetime.strptime(
                                '{}'.format(to_date), '%d/%m/%Y'
                                ).date())
                except Exception as e:
                    print(e)
                    continue
                data = pd.DataFrame(data)
                data = data.astype(
                    {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
                sti10 = ta.supertrend(data['high'], data['low'], data['close'], 5, 1)
                if sti10['SUPERT_5_1.0'].iloc[-1] < data['close'].iloc[-1] and flag['supertrend_pe'][c] == 0:
                    flag['supertrend_pe'][c] = 1
                    rank = 'STp'
                    qty = SL_qty = int(client['supertrend'].iloc[c] * 15)
                    if client['D20ironfly'].iloc[c] >= 1:
                        rank = 'STp'
                        qty = SL_qty = int(client['supertrend'].iloc[c] * 15)
                    # ind = (trade_table[c][trade_table[c]['rank'] == rank]
                    #     [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    Trade = 'BUY @'
                    strategy = 'ST'
                    order_placed = 0
                    SL_D_price = 'Nil'
                    prem = 0
                    Target1 = 'Nil'
                    SL_price = 'Nil'
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    last_tgt = last_qty = 'OPEN'
                    product = 'D'
                    strike = trade_table[c]['strike'][ind20p]
                    tradingsymbol = trade_table[c]['symbol'][ind20p]
                    days_left = trade_table[c]['days_left'][ind20p]
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['bids'][0]['price'] + 0.05
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                elif sti10['SUPERT_5_1.0'].iloc[-1] > data['close'].iloc[-1] and flag['supertrend_pe'][c] == 1:
                    flag['supertrend_pe'][c] = 0
                    try:
                        ind = (trade_table[c][trade_table[c]['rank'] == 'STp']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    except Exception as e:
                        print('No STp found in', c, e)
                        continue
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                        int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                    trade_table[c]['SL_status'][ind] = 'Closed'
                    trade_table[c]['3pm_tgt'][ind] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                    trade_table[c]['Entry_status'][ind] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                    trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                    trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                    trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                    trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                try:
                    ind20c = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == 'D20c']).index[0]
                    data = s.get_ohlc(
                        s.get_instrument_by_symbol(
                            'nse_fo', trade_table[c]['symbol'][ind20c]
                            ),
                        OHLCInterval.Minute_5, datetime.strptime(
                            '{}'.format(from_date), '%d/%m/%Y'
                            ).date(), datetime.strptime(
                                '{}'.format(to_date), '%d/%m/%Y'
                                ).date())
                except Exception as e:
                    print(e)
                    continue
                data = pd.DataFrame(data)
                data = data.astype(
                    {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
                sti10 = ta.supertrend(data['high'], data['low'], data['close'], 5, 1)
                if sti10['SUPERT_5_1.0'].iloc[-1] < data['close'].iloc[-1] and flag['supertrend_ce'][c] == 0:
                    flag['supertrend_ce'][c] = 1
                    if client['D20ironfly'].iloc[c] >= 1:
                        rank = 'STc'
                        qty = SL_qty = int(int(client['supertrend'].iloc[c])* 15)
                    # ind = (trade_table[c][trade_table[c]['rank'] == rank]
                    #     [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    Trade = 'BUY @'
                    strategy = 'ST'
                    order_placed = 0
                    SL_D_price = 'Nil'
                    prem = 0
                    Target1 = 'Nil'
                    SL_price = 'Nil'
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    last_tgt = last_qty = 'OPEN'
                    product = 'D'
                    strike = trade_table[c]['strike'][ind20c]
                    tradingsymbol = trade_table[c]['symbol'][ind20c]
                    days_left = trade_table[c]['days_left'][ind20c]
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['bids'][0]['price'] + 0.05
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                elif sti10['SUPERT_5_1.0'].iloc[-1] > data['close'].iloc[-1] and flag['supertrend_ce'][c] == 1:
                    flag['supertrend_ce'][c] = 0
                    try:
                        ind = (trade_table[c][trade_table[c]['rank'] == 'STc']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                    except Exception as e:
                        print('No STc found in', c, e)
                        continue
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                        int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                    trade_table[c]['SL_status'][ind] = 'Closed'
                    trade_table[c]['3pm_tgt'][ind] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                    trade_table[c]['Entry_status'][ind] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                    trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                    trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                    trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                    trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]

def add_SL(c, y, order, index):
    global trade_table
    if order['status'].iloc[index] == 'complete' and trade_table[c]['qty'][y] != 0:
        trade_table[c]['Entry_status'][y] = 'Executed'
        trade_table[c]['R.Profit'][y] = 0
        trade_table[c]['order_placed'][y] = 'YES'
        if (trade_table[c]['trade_type'][y] == 'BUY ABOVE' or trade_table[c]['trade_type'][y] == 'BUY @') and trade_table[c]['rank'][y] == 'D':
            order_id=u[c].place_order(TransactionType.Sell, u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                int(trade_table[c]['qty'][y]),OrderType.StopLossMarket,ProductType.Delivery,
                0.0,float(trade_table[c]['SL_D_price'][y]),0,DurationType.DAY,None,None,None)
            trade_table[c]['order_placed'][y] = 'YES'
            trade_table[c]['SL_id'][y] = order_id['order_id']
            trade_table[c]['time'][y] = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
            print(c, trade_table[c]['symbol'][y], 'Buy SL Trigger placed', trade_table[c]['SL_id'][y])
        elif trade_table[c]['trade_type'][y] == 'SELL BELOW' or trade_table[c]['trade_type'][y] == 'SELL @' and trade_table[c]['rank'][y] == 'D':
            if trade_table[c]['product'][y] == 'I':
                order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    int(trade_table[c]['qty'][y]),OrderType.StopLossMarket,ProductType.Intraday,
                    0.0,float(trade_table[c]['SL_D_price'][y]),0,DurationType.DAY,None,None,None)
            else:
                order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    int(trade_table[c]['qty'][y]),OrderType.StopLossMarket,ProductType.Delivery,
                    0.0,float(trade_table[c]['SL_D_price'][y]),0,DurationType.DAY,None,None,None)
            trade_table[c]['order_placed'][y] = 'YES'
            trade_table[c]['SL_id'][y] = order_id['order_id']
            trade_table[c]['time'][y] = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
            print(c, trade_table[c]['symbol'][y], 'Sell SL Trigger placed', trade_table[c]['SL_id'][y])
    else:
        trade_table[c]['order_placed'][y] = 'NO'
        trade_table[c]['order_rej'][y] = 'YES'

def batman_shift(c, y):
    global trade_table, Entry_bid, Trade, Target1, Tgt1_status, SL_pcent, trade_table_display, days_left
    global tradingsymbol, strategy, exchange, qty, SL_qty, date_time, rank, order_rej, strike, prem, SL_D_price
    global Entry_status, SL_price, SL_status, last_tgt, last_qty, sheet, order_placed, order_id, product
    expiry = trade_table[c]['symbol'][y][:-7]
    if 'CE' in trade_table[c]['symbol'][y]:
        strike, tradingsymbol = delta_strike(expiry, 0.09, trade_table[c]['days_left'][y])
        x = 'B30p'
        x1 = 'B20c'
    else:
        strike, tradingsymbol = delta_strike(expiry, -0.09, trade_table[c]['days_left'][y])
        x = 'B30c'
        x1 = 'B20p'
    order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
        int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
        0.0,None,0,DurationType.DAY,None,None,None)
    trade_table[c]['order_id_Sft'][y] = int(order_id['order_id'])
    trade_table[c]['SL_status'][y] = 'Shifted'
    trade_table[c]['3pm_tgt'][y] = 'Shifted'
    trade_table[c]['3pm_tgt_qty'][y] = 'Shifted'
    trade_table[c]['Entry_status'][y] = 'Shifted'
    trade_table[c]['Tgt1_status'][y] = 'Tgt Hit'
    order = pd.DataFrame(u[c].get_order_history())
    index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][y])].index)[0]
    trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
    trade_table[c]['Tgt1'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['Tgt1_price'][y]) * trade_table[c]['qty'][y]
    trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
    trade_table[c]['R.Profit'][y] = trade_table[c]['Tgt1'][y]
    ind = (trade_table[c][trade_table[c]['rank'] == x1]
        [trade_table[c]['Entry_status'] == 'Executed']).index[0]
    order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][ind],trade_table[c]['symbol'][ind]),
        int(trade_table[c]['SL_qty'][ind]),OrderType.Market,ProductType.Delivery,
        0.0,None,0,DurationType.DAY,None,None,None)
    trade_table[c]['order_id_Sft'][ind] = int(order_id['order_id'])
    trade_table[c]['SL_status'][ind] = 'Shifted'
    trade_table[c]['3pm_tgt'][ind] = 'Shifted'
    trade_table[c]['3pm_tgt_qty'][ind] = 'Shifted'
    trade_table[c]['Entry_status'][ind] = 'Shifted'
    trade_table[c]['Tgt1_status'][ind] = 'Tgt Hit'
    order = pd.DataFrame(u[c].get_order_history())
    index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][ind])].index)[0]
    trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
    trade_table[c]['Tgt1'][ind] = (trade_table[c]['Tgt1_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
    trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
    trade_table[c]['R.Profit'][ind] = trade_table[c]['Tgt1'][ind]
    rank = x1
    Trade = 'BUY @'
    order_placed = 0
    SL_D_price = 'Nil'
    prem = 0
    Target1 = 'Nil'
    SL_price = 'Nil'
    Entry_status = 'Ordered'
    Tgt1_status = SL_status = 'NOT EXEC'
    order_rej = 'NO'
    last_tgt = last_qty = 'OPEN'
    product = 'D'
    strategy = trade_table[c]['strategy'][y]
    days_left = trade_table[c]['days_left'][y]
    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
    Entry_bid = data['bids'][0]['price'] + 0.05
    qty = SL_qty = int(trade_table[c]['qty'][ind])
    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
        qty,OrderType.Market,ProductType.Delivery,
        0.0,None,0,DurationType.DAY,None,None,None)
    order_id = order_id1['order_id']
    append_excel_table(c)
    if 'CE' in trade_table[c]['symbol'][y]:
        strike, tradingsymbol = delta_strike(expiry, 0.3, trade_table[c]['days_left'][y])
    else:
        strike, tradingsymbol = delta_strike(expiry, -0.3, trade_table[c]['days_left'][y])
    rank = trade_table[c]['rank'][y]
    Trade = 'SELL @'
    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
    Entry_bid = data['asks'][0]['price'] - 0.05
    qty = SL_qty = int(trade_table[c]['qty'][y])
    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
        qty,OrderType.Market,ProductType.Delivery,
        0.0,None,0,DurationType.DAY,None,None,None)
    order_id = order_id1['order_id']
    append_excel_table(c)
    ind = (trade_table[c][trade_table[c]['rank'] == x]
        [trade_table[c]['Entry_status'] == 'Executed']).index[0]
    trade_table[c]['SL_price'][ind] = 'Nil'
    chart()

def expiry_trade():
    global trade_table, flag, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej, week0b, fromtime0
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    bank_data = s.get_ohlc(
        s.get_instrument_by_symbol(
            'nse_index', 'NIFTY_BANK'
            ),
        OHLCInterval.Minute_1, datetime.strptime(
            '{}'.format(to_date), '%d/%m/%Y'
            ).date(), datetime.strptime(
                '{}'.format(to_date), '%d/%m/%Y'
                ).date())
    bank_data = pd.DataFrame(bank_data)
    bank_data = bank_data.astype(
        {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
    bank_data['rsi'] = RSI(bank_data['close'], 9)
    bank_rsi = bank_data['rsi'].iloc[-1]
    bank_rsi_prev = bank_data['rsi'].iloc[-2]
    if bank_rsi >= 67.5 and bank_rsi_prev < 67.5:
        for c in range(len(client)):
            if client['expiry'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1 and flag['expiry_bank'][c] <= 0:
                flag['expiry_bank'][c] = 1
                rank = 'EL50c'
                qty = SL_qty = int(client['expiry'].iloc[c] * 15)
                Trade = 'BUY @'
                strategy = 'ERSI'
                order_placed = 0
                SL_D_price = 'Nil'
                prem = 0
                Target1 = 'Nil'
                SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                strike, tradingsymbol = delta_strike(week0b, 0.5, fromtime0)
                days_left = fromtime0
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['bids'][0]['price'] + 0.05
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
    elif bank_rsi <= 63.5 and bank_rsi_prev > 63.5:
        for c in range(len(client)):
            if client['expiry'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1 and flag['expiry_bank'][c] == 1:
                flag['expiry_bank'][c] = 0
                try:
                    ind = (trade_table[c][trade_table[c]['rank'] == 'EL50c']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                except Exception as e:
                    print('No EL50c found in', c, e)
                    continue
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                    int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                trade_table[c]['SL_status'][ind] = 'Closed'
                trade_table[c]['3pm_tgt'][ind] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                trade_table[c]['Entry_status'][ind] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
    elif bank_rsi <= 32.5 and bank_rsi_prev > 32.5:
        for c in range(len(client)):
            if client['expiry'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1 and flag['expiry_bank'][c] >= 0:
                flag['expiry_bank'][c] = -1
                qty = SL_qty = int(client['expiry'].iloc[c] * 15)
                Trade = 'BUY @'
                strategy = 'ERSI'
                order_placed = 0
                SL_D_price = 'Nil'
                prem = 0
                Target1 = 'Nil'
                SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                strike, tradingsymbol = delta_strike(week0b, -0.5, fromtime0)
                days_left = fromtime0
                rank = 'EL50p'
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['bids'][0]['price'] + 0.05
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
    elif bank_rsi >= 36.5 and bank_rsi_prev < 36.5:
        for c in range(len(client)):
            if client['expiry'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1 and flag['expiry_bank'][c] == -1:
                flag['expiry_bank'][c] = 0
                try:
                    ind = (trade_table[c][trade_table[c]['rank'] == 'EL50p']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                except Exception as e:
                    print('No EL50p found in', c, e)
                    continue
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                    int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                trade_table[c]['SL_id'][ind] = int(order_id1['order_id'])
                trade_table[c]['SL_status'][ind] = 'Closed'
                trade_table[c]['3pm_tgt'][ind] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                trade_table[c]['Entry_status'][ind] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
    for c in range(len(client)):
        if client['expiry'].iloc[c] >= 1:
            strike, tradingsymbol = delta_strike(week0b, -0.3, fromtime0)
            try:
                ind = (trade_table[c][trade_table[c]['rank'] == 'E50p']
                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
            except Exception as e:
                print('No E50p found in', c, e)
                continue
            if strike != trade_table[c]['strike'][ind]:
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                    int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                trade_table[c]['order_id_Tgt1'][ind] = int(order_id1['order_id'])
                trade_table[c]['SL_status'][ind] = 'Closed'
                trade_table[c]['3pm_tgt'][ind] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                trade_table[c]['Entry_status'][ind] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['order_id_Tgt1'][ind])].index)[0]
                trade_table[c]['Tgt1_price'][ind] = order['average_price'].iloc[index]
                trade_table[c]['Tgt1'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['Tgt1_price'][ind]) * trade_table[c]['qty'][ind]
                trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                trade_table[c]['R.Profit'][ind] = trade_table[c]['Tgt1'][ind]
                Trade = 'SELL @'
                rank = 'E50p'
                strategy = 'Expiry'
                order_placed = 0
                SL_D_price = 'Nil'
                prem = 0
                Target1 = 'Nil'
                SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                days_left = fromtime0
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 3.5
                if Entry_bid < 1:
                    close_position()
                if strike > trade_table[c]['strike'][ind]:
                    qty = SL_qty = int(client['expiry'].iloc[c] * 15)
                else:
                    qty = SL_qty = int(client['expiry'].iloc[c] * 15 / 2)
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Limit,ProductType.Delivery,
                    Entry_bid,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
            strike, tradingsymbol = delta_strike(week0b, 0.3, fromtime0)
            try:
                ind = (trade_table[c][trade_table[c]['rank'] == 'E50c']
                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
            except Exception as e:
                print('No E50c found in', c, e)
                continue
            if strike != trade_table[c]['strike'][ind]:
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][ind]),
                    int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                trade_table[c]['order_id_Tgt1'][ind] = int(order_id1['order_id'])
                trade_table[c]['SL_status'][ind] = 'Closed'
                trade_table[c]['3pm_tgt'][ind] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                trade_table[c]['Entry_status'][ind] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['order_id_Tgt1'][ind])].index)[0]
                trade_table[c]['Tgt1_price'][ind] = order['average_price'].iloc[index]
                trade_table[c]['Tgt1'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['Tgt1_price'][ind]) * trade_table[c]['qty'][ind]
                trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                trade_table[c]['R.Profit'][ind] = trade_table[c]['Tgt1'][ind]
                Trade = 'SELL @'
                rank = 'E50c'
                strategy = 'Expiry'
                order_placed = 0
                SL_D_price = 'Nil'
                prem = 0
                Target1 = 'Nil'
                SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                days_left = fromtime0
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 3.5
                if Entry_bid < 1:
                    close_position()
                if strike < trade_table[c]['strike'][ind]:
                    qty = SL_qty = int(client['expiry'].iloc[c] * 15)
                else:
                    qty = SL_qty = int(client['expiry'].iloc[c] * 15 / 2)
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Limit,ProductType.Delivery,
                    Entry_bid,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)

def update_target_SL(c, y):
    global trade_table, trade_book, data, order, flag
    if trade_table[c]['SL_status'][y] == 'NOT EXEC' and trade_table[c]['Entry_status'][y] == 'Executed':
        try:
            order = pd.DataFrame(u[c].get_order_history())
            if trade_table[c]['strategy'][y] == 'EMA':
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                if trade_table[c]['symbol'][y][:4] == 'NIFT':
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_INDEX', 'NIFTY_50'), LiveFeedType.LTP)['ltp']
                else:
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
                if order['status'].iloc[index] == 'complete':
                    trade_table[c]['Tgt1_status'][y] = 'SL Hit'
                    trade_table[c]['3pm_tgt'][y] = 'SL Hit'
                    trade_table[c]['3pm_tgt_qty'][y] = 'SL Hit'
                    trade_table[c]['SL_status'][y] = 'SL Hit'
                    print(tradingsymbol, 'SL Hit')
                    trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                    trade_table[c]['SL'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['SL_price'][y]) * trade_table[c]['SL_qty'][y]
                    trade_table[c]['SL_qty'][y] = 0
                    trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    if trade_table[c]['symbol'][y][-2:] == 'CE':
                        flag['ema_ce'][c] = 0
                    else:
                        flag['ema_pe'][c] = 0
                elif (last_price >= trade_table[c]['SL_price'][y] and trade_table[c]['symbol'][y][-2:] == 'CE') or (last_price <= trade_table[c]['SL_price'][y] and trade_table[c]['symbol'][y][-2:] == 'PE'):
                    trade_table[c]['Tgt1_status'][y] = 'SL Hit'
                    trade_table[c]['3pm_tgt'][y] = 'SL Hit'
                    trade_table[c]['3pm_tgt_qty'][y] = 'SL Hit'
                    trade_table[c]['SL_status'][y] = 'SL Hit'
                    print(tradingsymbol, 'SL Hit')
                    # trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                    # trade_table[c]['SL'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['SL_price'][y]) * trade_table[c]['SL_qty'][y]
                    # trade_table[c]['SL_qty'][y] = 0
                    # trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    order_id = u[c].cancel_order(int(trade_table[c]['SL_id'][y]))
                    print(tradingsymbol, order_id, 'SL cancelled')
                    if trade_table[c]['product'][y] == 'I':
                        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Intraday,
                            0.0,None,0,DurationType.DAY,None,None,None)
                    else:
                        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                    print(order_id)
                    trade_table[c]['SL_id'][y] = order_id['order_id']
                    order = pd.DataFrame(u[c].get_order_history())
                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                    trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                    trade_table[c]['SL'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['SL_price'][y]) * trade_table[c]['qty'][y]
                    trade_table[c]['SL_qty'][y] = 0
                    trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    if trade_table[c]['symbol'][y][-2:] == 'CE':
                        flag['ema_ce'][c] = 0
                    else:
                        flag['ema_pe'][c] = 0
                elif trade_table[c]['LTP'][y] <= trade_table[c]['Tgt1_price'][y]:
                    trade_table[c]['Tgt1_status'][y] = 'Tgt1 Hit'
                    trade_table[c]['SL_status'][y] = 'Not Hit'
                    trade_table[c]['3pm_tgt'][y] = 'Tgt complete'
                    trade_table[c]['3pm_tgt_qty'][y] = 'Tgt Hit'
                    order_id = u[c].cancel_order(int(trade_table[c]['SL_id'][y]))
                    print(tradingsymbol, order_id, 'SL cancelled')
                    if trade_table[c]['product'][y] == 'I':
                        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Intraday,
                            0.0,None,0,DurationType.DAY,None,None,None)
                    else:
                        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                    print(order_id)
                    trade_table[c]['order_id_Tgt1'][y] = order_id['order_id']
                    order = pd.DataFrame(u[c].get_order_history())
                    index = list(order[order['order_id'] == int(trade_table[c]['order_id_Tgt1'][y])].index)[0]
                    trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
                    trade_table[c]['Tgt1'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['Tgt1_price'][y]) * trade_table[c]['qty'][y]
                    trade_table[c]['SL_qty'][y] = 0
                    trade_table[c]['R.Profit'][y] = trade_table[c]['Tgt1'][y]
                    if trade_table[c]['symbol'][y][-2:] == 'CE':
                        flag['ema_ce'][c] = 0
                    else:
                        flag['ema_pe'][c] = 0
                elif trade_table[c]['LTP'][y] * 1.2 < trade_table[c]['SL_D_price'][y]:
                    trade_table[c]['SL_D_price'][y] = round2(trade_table[c]['LTP'][y] * 1.2)
                    try:
                        u[c].modify_order(int(trade_table[c]['SL_id'][y]), trigger_price=trade_table[c]['SL_D_price'][y])
                        print('SL being modified for', c, trade_table[c]['SL_D_price'][y], trade_table[c]['symbol'][y])
                    except Exception as e:
                        print('Warning!!! Modify order not done for', c, trade_table[c]['SL_id'][y])
            elif trade_table[c]['strategy'][y] == 'Batman':
                if trade_table[c]['SL_price'][y] == 'Nil' and trade_table[c]['rank'][y] == 'B30c':
                    if len(Chart_table[c]) > 0:
                        for i in range(len(Chart_table[c]) - 1):
                            if Chart_table[c]['final'][i] < 0 and Chart_table[c]['final'][i+1] > 0:
                                trade_table[c]['SL_price'][y] = (100 * abs(Chart_table[c]['final'][i]) / (Chart_table[c]['final'][i+1] - Chart_table[c]['final'][i])) + Chart_table[c]['price'][i]
                                break
                            elif i == (len(Chart_table[c]) - 2):
                                trade_table[c]['SL_price'][y] = 0
                elif trade_table[c]['SL_price'][y] == 'Nil' and trade_table[c]['rank'][y] == 'B30p':
                    if len(Chart_table[c]) > 0:
                        for i in range(len(Chart_table[c]) - 1):
                            if Chart_table[c]['final'][i] > 0 and Chart_table[c]['final'][i+1] < 0:
                                trade_table[c]['SL_price'][y] = (100 * abs(Chart_table[c]['final'][i]) / (Chart_table[c]['final'][i] - Chart_table[c]['final'][i+1])) + Chart_table[c]['price'][i]                
                                break
                            elif i == (len(Chart_table[c]) - 2):
                                last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_INDEX', 'NIFTY_50'), LiveFeedType.LTP)['ltp']
                                trade_table[c]['SL_price'][y] = last_price * 1.1
                elif trade_table[c]['rank'][y] == 'B30c':
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
                    if last_price <= trade_table[c]['SL_price'][y]:
                        batman_shift(c, y)
                elif trade_table[c]['rank'][y] == 'B30p':
                    last_price = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
                    if last_price >= trade_table[c]['SL_price'][y]:
                        batman_shift(c, y)
        except Exception as e:
            print(e)

def ema_entry():
    global flag, week1b, thursday, strike, week0b
    global Trade, rank, strategy, tradingsymbol, exchange, days_left, order_placed, qty, SL_qty, Target1, prem, SL_price, SL_D_price
    global Entry_status, Tgt1_status, order_rej, SL_status, Entry_bid, product, last_tgt, last_qty, strike, order_id
    # try:
    interval = OHLCInterval.Minute_5
    data = s.get_ohlc( 
        s.get_instrument_by_symbol(
            'NSE_INDEX', 'NIFTY_BANK'
            ),
        interval, datetime.strptime(
            '{}'.format(from_date), '%d/%m/%Y'
            ).date(), datetime.strptime(
                '{}'.format(to_date), '%d/%m/%Y'
                ).date())
    data = pd.DataFrame(data)
    data = data.astype(
        {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
    data['ema'] = EMA(data['close'].values, 50)
    data['ema21'] = EMA(data['close'].values, 21)
    data['ema7'] = EMA(data['close'].values, 7)
    for c in range(len(client)):
        if client['EMA'].iloc[c] >= 1 and time(9, 20) <= datetime.now().time() and flag['close'][c] == 0:
            if (data['ema'].iloc[-2] < data['close'].iloc[-2] and -120 <= (data['ema'].iloc[-1] - data['close'].iloc[-1]) <= 120 and data['ema'].iloc[-1] > data['close'].iloc[-1] and flag['ema_ce'][c] == 0 and flag['ema_pe'][c] == 0) or (data['ema'].iloc[-1] - 10 > data['close'].iloc[-1] and flag['ema_pe'][c] >= 1) or (0 <= (data['ema'].iloc[-1] - data['close'].iloc[-1]) <= 80 and flag['ema_ce'][c] == 0 and flag['ema_pe'][c] == 0):
            # if (-80 <= (data['ema21'].iloc[-1] - data['ema7'].iloc[-1]) <= 80 and data['ema7'].iloc[-1] < data['ema21'].iloc[-1] and flag['ema_ce'][c] == 0 and flag['ema_pe'][c] == 0) or (data['ema7'].iloc[-2] > data['ema21'].iloc[-2] and data['ema7'].iloc[-1] < data['ema21'].iloc[-1] and flag['ema_ce'][c] == 0):
                print('Sell Sell Sell @', data['close'].iloc[-1])
                if flag['ema_pe'][c] == 1:
                    try:
                        y = (trade_table[c][trade_table[c]['rank'] == 'DUP']
                            [trade_table[c]['symbol'].apply(lambda x: x[:4] == 'BANK')]
                            [trade_table[c]['symbol'].apply(lambda x: x[-2:] == 'PE')]
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['strategy'] == 'EMA']).index[0]
                        trade_table[c]['Tgt1_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt'][y] = 'Change Hit'
                        trade_table[c]['Entry_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt_qty'][y] = 'Change Hit'
                        trade_table[c]['SL_status'][y] = 'Change Hit'
                        print(trade_table[c]['symbol'][y], 'Change Hit')
                        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        print(order_id)
                        trade_table[c]['SL_id'][y] = order_id['order_id']
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                        trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['SL_price'][y]) * trade_table[c]['qty'][y]
                        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                        trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                        y = (trade_table[c][trade_table[c]['rank'] == 'DbUP']
                            [trade_table[c]['symbol'].apply(lambda x: x[:4] == 'BANK')]
                            [trade_table[c]['symbol'].apply(lambda x: x[-2:] == 'PE')]
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['strategy'] == 'EMA']).index[0]
                        trade_table[c]['Tgt1_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt_qty'][y] = 'Change Hit'
                        trade_table[c]['Entry_status'][y] = 'Change Hit'
                        trade_table[c]['SL_status'][y] = 'Change Hit'
                        print(tradingsymbol, 'Change Hit')
                        order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        print(order_id)
                        trade_table[c]['SL_id'][y] = order_id['order_id']
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                        trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][y] = (trade_table[c]['SL_price'][y] - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y]
                        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                        trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    except Exception as e:
                        print('Error DUP or DbUP not available in', c, e)
                    flag['ema_pe'][c] = 0
                elif flag['ema_pe'][c] == 2:
                    try:
                        y = (trade_table[c][trade_table[c]['rank'] == 'DbUP']
                            [trade_table[c]['symbol'].apply(lambda x: x[:4] == 'BANK')]
                            [trade_table[c]['symbol'].apply(lambda x: x[-2:] == 'CE')]
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['strategy'] == 'EMA']).index[0]
                        trade_table[c]['Tgt1_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt_qty'][y] = 'Change Hit'
                        trade_table[c]['Entry_status'][y] = 'Change Hit'
                        trade_table[c]['SL_status'][y] = 'Change Hit'
                        print(tradingsymbol, 'Change Hit')
                        order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        print(order_id)
                        trade_table[c]['SL_id'][y] = order_id['order_id']
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                        trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][y] = (trade_table[c]['SL_price'][y] - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y]
                        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                        trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    except Exception as e:
                        print('Error DbUP not available in', c, e)
                    flag['ema_pe'][c] = 0    
                strategy = 'EMA'
                rank = 'DbDown'
                order_placed = 0
                qty = SL_qty = int(client['EMA'].iloc[c] * 15)
                Target1 = 'Nil'
                SL_D_price = SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                Trade = 'BUY @'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                prem = 0
                if client['EMA_type'].iloc[c] == 1:
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        strike, tradingsymbol = delta_strike(week0b, 0.2, fromtime0)
                        days_left = fromtime0
                    else:
                        strike, tradingsymbol = delta_strike(week1b, 0.2, fromtime1)
                        days_left = fromtime1
                    Entry_bid = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id['order_id']
                    append_excel_table(c)
                    last_price_bank = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
                    strike_price = round(last_price_bank/100) * 100
                    strike = strike_price
                    Trade = 'SELL @'
                    strategy = 'EMA'
                    rank = 'DDown'
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        tradingsymbol = str(week0b) + str(strike_price) + 'CE'
                        days_left = fromtime0
                    else:
                        tradingsymbol = str(week1b) + str(strike_price) + 'CE'
                        days_left = fromtime1
                    order_placed = 0
                    qty = SL_qty = int(client['EMA'].iloc[c] * 15)
                    Target1 = 2
                    Entry_bid = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    SL_D_price = SL_price = 'Nil'
                    prem = 0
                    # SL_price = data['low'].iloc[-2:].max()
                    Entry_status = 'Ordered'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    last_tgt = last_qty = 'OPEN'
                    product = 'D'
                    order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id['order_id']
                    append_excel_table(c)
                    flag['ema_ce'][c] = 1
                    order = pd.DataFrame(u[c].get_order_history())
                    index = order[order['order_id'] == int(order_id)].index[0]
                    if order['status'].iloc[index] == 'rejected':
                        print('Order rejected')
                        ind = (trade_table[c][trade_table[c]['rank'] == 'DDown']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        indDbD = (trade_table[c][trade_table[c]['rank'] == 'DbDown']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][indDbD]),
                            int(trade_table[c]['qty'][indDbD]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][indDbD] = order_id1['order_id']
                        trade_table[c]['SL_status'][indDbD] = 'Closed'
                        trade_table[c]['3pm_tgt'][indDbD] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][indDbD] = 'Closed'
                        trade_table[c]['Entry_status'][indDbD] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][indDbD])].index)[0]
                        trade_table[c]['SL_price'][indDbD] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][indDbD] = (trade_table[c]['SL_price'][indDbD] - trade_table[c]['Entry_price'][indDbD]) * trade_table[c]['qty'][indDbD]
                        trade_table[c]['SL_qty'][indDbD] = trade_table[c]['Profit'][indDbD] = 0
                        trade_table[c]['R.Profit'][indDbD] = trade_table[c]['SL'][indDbD]
                elif client['EMA_type'].iloc[c] == 2:
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        strike, tradingsymbol = delta_strike(week0b, -0.7, fromtime0)
                        days_left = fromtime0
                    else:
                        strike, tradingsymbol = delta_strike(week1b, -0.7, fromtime1)
                        days_left = fromtime1
                    Entry_bid = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id['order_id']
                    append_excel_table(c)
                    flag['ema_ce'][c] = 2
            elif (data['ema'].iloc[-2] > data['close'].iloc[-2] and -120 <= (data['ema'].iloc[-1] - data['close'].iloc[-1]) <= 120 and data['ema'].iloc[-1] < data['close'].iloc[-1] and flag['ema_ce'][c] == 0 and flag['ema_pe'][c] == 0) or (data['ema'].iloc[-1] + 10 < data['close'].iloc[-1] and flag['ema_ce'][c] >= 1) or (0 <= (data['close'].iloc[-1] - data['ema'].iloc[-1]) <= 80 and flag['ema_ce'][c] == 0 and flag['ema_pe'][c] == 0):
            # elif (-80 <= (data['ema21'].iloc[-1] - data['ema7'].iloc[-1]) <= 80 and data['ema7'].iloc[-1] > data['ema21'].iloc[-1] and flag['ema_ce'][c] == 0 and flag['ema_pe'][c] == 0) or (data['ema7'].iloc[-2] < data['ema21'].iloc[-2] and data['ema7'].iloc[-1] > data['ema21'].iloc[-1] and flag['ema_pe'][c] == 0):
                print('Buy Buy Buy @', data['close'].iloc[-1])
                if flag['ema_ce'][c] == 1:
                    try:
                        y = (trade_table[c][trade_table[c]['rank'] == 'DDown']
                            [trade_table[c]['symbol'].apply(lambda x: x[:4] == 'BANK')]
                            [trade_table[c]['symbol'].apply(lambda x: x[-2:] == 'CE')]
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['strategy'] == 'EMA']).index[0]
                        trade_table[c]['Tgt1_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt_qty'][y] = 'Change Hit'
                        trade_table[c]['Entry_status'][y] = 'Change Hit'
                        trade_table[c]['SL_status'][y] = 'Change Hit'
                        print(tradingsymbol, 'SL Hit')
                        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        print(order_id)
                        trade_table[c]['SL_id'][y] = order_id['order_id']
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                        trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['SL_price'][y]) * trade_table[c]['qty'][y]
                        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                        trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                        y = (trade_table[c][trade_table[c]['rank'] == 'DbDown']
                            [trade_table[c]['symbol'].apply(lambda x: x[:4] == 'BANK')]
                            [trade_table[c]['symbol'].apply(lambda x: x[-2:] == 'CE')]
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['strategy'] == 'EMA']).index[0]
                        trade_table[c]['Tgt1_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt_qty'][y] = 'Change Hit'
                        trade_table[c]['Entry_status'][y] = 'Change Hit'
                        trade_table[c]['SL_status'][y] = 'Change Hit'
                        print(tradingsymbol, 'Change Hit')
                        order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        print(order_id)
                        trade_table[c]['SL_id'][y] = order_id['order_id']
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                        trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][y] = (trade_table[c]['SL_price'][y] - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y]
                        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                        trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    except Exception as e:
                        print('Error DDown not available in', c, e)
                    flag['ema_ce'][c] = 0
                elif flag['ema_ce'][c] == 2:
                    try:
                        y = (trade_table[c][trade_table[c]['rank'] == 'DbDown']
                            [trade_table[c]['symbol'].apply(lambda x: x[:4] == 'BANK')]
                            [trade_table[c]['symbol'].apply(lambda x: x[-2:] == 'PE')]
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['strategy'] == 'EMA']).index[0]
                        trade_table[c]['Tgt1_status'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt'][y] = 'Change Hit'
                        trade_table[c]['3pm_tgt_qty'][y] = 'Change Hit'
                        trade_table[c]['Entry_status'][y] = 'Change Hit'
                        trade_table[c]['SL_status'][y] = 'Change Hit'
                        print(tradingsymbol, 'Change Hit')
                        order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        print(order_id)
                        trade_table[c]['SL_id'][y] = order_id['order_id']
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][y])].index)[0]
                        trade_table[c]['SL_price'][y] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][y] = (trade_table[c]['SL_price'][y] - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y]
                        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                        trade_table[c]['R.Profit'][y] = trade_table[c]['SL'][y]
                    except Exception as e:
                        print('Error DbDown not available in', c, e)
                    flag['ema_ce'][c] = 0
                strategy = 'EMA'
                rank = 'DbUP'
                order_placed = 0
                qty = SL_qty = int(client['EMA'].iloc[c] * 15)
                Target1 = 'Nil'
                SL_D_price = SL_price = 'Nil'
                Entry_status = 'Ordered'
                Trade = 'BUY @'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                prem = 0
                if client['EMA_type'].iloc[c] == 1:
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        strike, tradingsymbol = delta_strike(week0b, -0.2, fromtime0)
                        days_left = fromtime0
                    else:
                        strike, tradingsymbol = delta_strike(week1b, -0.2, fromtime1)
                        days_left = fromtime1
                    Entry_bid = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id['order_id']
                    append_excel_table(c)
                    last_price_bank = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
                    strike_price = round(last_price_bank/100) * 100
                    strike = strike_price
                    Trade = 'SELL @'
                    strategy = 'EMA'
                    rank = 'DUP'
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        tradingsymbol = str(week0b) + str(strike_price) + 'PE'
                        days_left = fromtime0
                    else:
                        tradingsymbol = str(week1b) + str(strike_price) + 'PE'
                        days_left = fromtime1
                    print(tradingsymbol)
                    order_placed = 0
                    Entry_bid = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    # SL_D_price = round2(Entry_bid * 1.5)
                    prem = 0
                    qty = SL_qty = int(client['EMA'].iloc[c] * 15)
                    Target1 = 2
                    SL_D_price = SL_price = 'Nil'
                    Entry_status = 'Ordered'
                    Trade = 'SELL @'
                    Tgt1_status = SL_status = 'NOT EXEC'
                    order_rej = 'NO'
                    last_tgt = last_qty = 'OPEN'
                    product = 'D'
                    order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id['order_id']
                    append_excel_table(c)
                    flag['ema_pe'][c] = 1
                    order = pd.DataFrame(u[c].get_order_history())
                    index = order[order['order_id'] == int(order_id)].index[0]
                    if order['status'].iloc[index] == 'rejected':
                        print('Order rejected')
                        ind = (trade_table[c][trade_table[c]['rank'] == 'DUP']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        indDbU = (trade_table[c][trade_table[c]['rank'] == 'DbUP']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][indDbU]),
                            int(trade_table[c]['qty'][indDbU]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][indDbU] = order_id1['order_id']
                        trade_table[c]['SL_status'][indDbU] = 'Closed'
                        trade_table[c]['3pm_tgt'][indDbU] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][indDbU] = 'Closed'
                        trade_table[c]['Entry_status'][indDbU] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][indDbU])].index)[0]
                        trade_table[c]['SL_price'][indDbU] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][indDbU] = (trade_table[c]['SL_price'][indDbU] - trade_table[c]['Entry_price'][indDbU]) * trade_table[c]['qty'][indDbU]
                        trade_table[c]['SL_qty'][indDbU] = trade_table[c]['Profit'][indDbU] = 0
                        trade_table[c]['R.Profit'][indDbU] = trade_table[c]['SL'][indDbU]
                elif client['EMA_type'].iloc[c] == 2:
                    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                        strike, tradingsymbol = delta_strike(week0b, 0.7, fromtime0)
                        days_left = fromtime0
                    else:
                        strike, tradingsymbol = delta_strike(week1b, 0.7, fromtime1)
                        days_left = fromtime1
                    Entry_bid = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.LTP)['ltp']
                    order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id['order_id']
                    append_excel_table(c)
                    flag['ema_pe'][c] = 2

def weeks():
    global week0b, week1b, fromtime0, fromtime1, thursday, days_left, month0b, month1b, wednesday, week0n, week1n, fromtime0n, fromtime1n, days_leftn
    today = datetime.today().weekday()
    todayte = datetime.today()
    cmon = todayte.month
    thursday = 10 - today
    if thursday > 7:
        thursday -= 7
    wednesday = 9 - today
    if wednesday > 7:
        wednesday -= 7
    # print(thursday)
    now = datetime.now()
    todate = datetime.today().date().day
    thursday1 = datetime.strftime(now, '%d/%m/%Y')
    thursday1 = datetime.strptime(thursday1, '%d/%m/%Y')
    thursday1 = thursday1+relativedelta(days=thursday)
    wednesday1 = datetime.strftime(now, '%d/%m/%Y')
    wednesday1 = datetime.strptime(wednesday1, '%d/%m/%Y')
    wednesday1 = wednesday1+relativedelta(days=wednesday)
    # if wednesday == 7 or (wednesday == 1 and shortweek == 1):
    #     if wednesday == 1 and shortweek == 1:
    #         wednesday0 = wednesday1-relativedelta(days=1)
    #         wednesday1 = wednesday1+relativedelta(days=7)
    #     else:
    #         wednesday0 = wednesday1-relativedelta(days=7)
    #     YY0 = wednesday0.year
    #     YY0 -= 2000
    #     MM0 = wednesday0.month
    #     DD0 = wednesday0.day
    #     print('Bank Expiry today on',DD0)
    #     if DD0 < 10:
    #         DD0 = '0' + str(DD0)
    # elif shortweek == 1:
    #     wednesday1 = wednesday1-relativedelta(days=1)
    # YY1 = wednesday1.year
    # YY1 -= 2000
    # MM1 = wednesday1.month
    # DD1 = wednesday1.day
    # print('Next Bank Expiry on', DD1)
    # if DD1 < 10:
    #     DD1 = '0' + str(DD1)
    last_thursday = 1
    for i in range(1, 7):
        t = todayte + relativedelta(weekday=TH(i))
        if t.month != cmon:
            t = t + relativedelta(weekday=TH(-2))
            last_thursday = t.day
            print('last thurday of month is', last_thursday)
            break
    if last_thursday == wednesday1.day + 1:
        wednesday1 = wednesday1+relativedelta(days=1)
    elif last_thursday == wednesday1.day - 6:
        print('Doing this on comming week for monthly expiry')
        wednesday1 = wednesday1-relativedelta(days=6)
    todate = datetime.today().day
    print(todate)
    print(last_thursday)
    if last_thursday == todate:
        print('today last day of the monthly expiry')
        wednesday = 7
    # YY1 = wednesday1.year
    # YY1 -= 2000
    # MM1 = wednesday1.month
    DD1 = wednesday1.day
    # print('Next Bank Expiry on', DD1)
    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
        wednesday0 = wednesday1-relativedelta(days=6)
        if wednesday == 1 and shortweek == 1:
            print('Should do on short week')
            wednesday0 = wednesday1-relativedelta(days=1)
            wednesday1 = wednesday1+relativedelta(days=7)
        elif last_thursday == wednesday0.day:
            print('Should be doing on last week of the monthly expiry')
        else:
            if last_thursday == wednesday1.day:
                wednesday0 = wednesday1-relativedelta(days=8)
            else:
                wednesday0 = wednesday1-relativedelta(days=7)
            print('Today Banknifty weekly expiry')
        YY0 = wednesday0.year
        YY0 -= 2000
        MM0 = wednesday0.month
        DD0 = wednesday0.day
        print('Next week expiry date', DD1)
        print('Today expiry date', DD0)
        if DD1 != DD0 + 1:
            print('Bank Expiry today on',DD0)
            if DD0 < 10:
                DD0 = '0' + str(DD0)
        # else:
        #     DD0 = DD1
        #     wednesday0 = wednesday1-relativedelta(days=6)
    elif shortweek == 1:
        wednesday1 = wednesday1-relativedelta(days=1)
    YY1 = wednesday1.year
    YY1 -= 2000
    MM1 = wednesday1.month
    DD1 = wednesday1.day
    if DD1 < 10:
        DD1 = '0' + str(DD1)
    print('Next Bank Expiry on', DD1)
    if wednesday == 7 and shortweek == 1:
        if DD0 == last_thursday - 2 or DD0 == last_thursday - 1:
            MM0 = datetime.now().strftime('%h')
            week0b = 'BANKNIFTY' + str(YY0) + str(MM0.upper())
            month0b = week0b
            print('Month0 for Bank is', month0b)
    elif wednesday == 7 or (wednesday == 1 and shortweek == 1):
        if wednesday == 7 and last_thursday == wednesday0.day:
            MM0 = datetime.now().strftime('%h')
            week0b = 'BANKNIFTY' + str(YY0) + str(MM0.upper())
        else:
            week0b = 'BANKNIFTY' + str(YY0) + str(MM0) + str(DD0)
        print('Week0 is', week0b)
    if wednesday == 6:
        thursday0 = thursday1-relativedelta(days=7)
        DDT0 = thursday0.day
        if DDT0 == last_thursday:
            YY0 = thursday0.year
            YY0 -= 2000
            MM0 = datetime.now().strftime('%h')
            week0b = 'BANKNIFTY' + str(YY0) + str(MM0.upper())
            month0b = week0b
            print('Month0 for Bank is', month0b)
            if DDT0 == 31:
                MM1 = datetime.now().replace(month=MM0)
            else:
                MMM0 = datetime.today().month
                print(MMM0)
                MM1 = datetime.now().replace(month=MMM0+1)
                print(MM1)
            MM1 = MM1.strftime('%h')
            month1b = 'BANKNIFTY' + str(YY1) + str(MM1.upper())
    print(DD1)
    print(last_thursday)
    if DD1 == last_thursday: # - 2 or DD1 == last_thursday - 1 or DD1 == last_thursday - 3 or DD1 == last_thursday - 6:
        MM1 = datetime.now().strftime('%h')
        week1b = 'BANKNIFTY' + str(YY1) + str(MM1.upper())
        month1b = week1b
    else:
        week1b = 'BANKNIFTY' + str(YY1) + str(MM1) + str(DD1)
        MM0 = datetime.now().strftime('%h')
        month1b = 'BANKNIFTY' + str(YY1) + str(MM0.upper())
        if wednesday == 7 or (wednesday == 1 and shortweek == 1):
            if DD0 == last_thursday - 2 or DD0 == last_thursday - 1:
                MM0 = wednesday0.month
                if DD0 == 30:
                    MM1 = datetime.now().replace(month=MM0)
                else:
                    MM1 = datetime.now().replace(month=MM0+1)
                MM1 = MM1.strftime('%h')
                month1b = 'BANKNIFTY' + str(YY1) + str(MM1.upper())
    if datetime.now().strftime('%h') != thursday1.month:
        month1b = 'BANKNIFTY' + str(YY1) + str(thursday1.strftime('%h').upper())
    YY1 += 2000
    MM1 = thursday1.month
    DD1 = int(DD1)
    days_left = fromtime1 = datetime(YY1, MM1, DD1, 15, 30) # expiry date (YYYY, MM, DD, HR, MIN)
    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
        YY0 += 2000
        MM0 = wednesday0.month
        DD0 = int(DD0)
        fromtime0 = datetime(YY0, MM0, DD0, 15, 30)
        days_left = fromtime0
    print('Week1 bank is', week1b)
    print('Month1 bank is', month1b)
    print('Time to expiry for bank is', days_left)
    if thursday == 7 or (thursday == 1 and shortweek == 1):
        if thursday == 1 and shortweek == 1:
            thursday0 = thursday1-relativedelta(days=1)
            thursday1 = thursday1+relativedelta(days=7)
        else:
            thursday0 = thursday1-relativedelta(days=7)
        YY0 = thursday0.year
        YY0 -= 2000
        MM0 = thursday0.month
        DD0 = thursday0.day
        print('Expiry today on',DD0)
        if DD0 < 10:
            DD0 = '0' + str(DD0)
    elif shortweek == 1:
        thursday1 = thursday1-relativedelta(days=1)
    YY1 = thursday1.year
    YY1 -= 2000
    MM1 = thursday1.month
    DD1 = thursday1.day
    print('Next Expiry on', DD1)
    if DD1 < 10:
        DD1 = '0' + str(DD1)
    last_thursday = 1
    for i in range(1, 6):
        t = todayte + relativedelta(weekday=TH(i))
        if t.month != cmon:
            t = t + relativedelta(weekday=TH(-2))
            last_thursday = t.day
            print('last thurday of month is', last_thursday)
            break
    if thursday == 7 or (thursday == 1 and shortweek == 1):
        if DD0 == last_thursday or DD0 == last_thursday - 1:
            MM0 = datetime.now().strftime('%h')
            week0n = 'NIFTY' + str(YY0) + str(MM0.upper())
            month0n = week0n
            print('Month0 for nifty is', month0n)
        else:
            week0n = 'NIFTY' + str(YY0) + str(MM0) + str(DD0)
        print('Week0 nifty is', week0n)
    if DD1 == last_thursday or DD1 == last_thursday - 1:
        MM1 = datetime.now().strftime('%h')
        week1n = 'NIFTY' + str(YY1) + str(MM1.upper())
        month1n = week1n
    else:
        week1n = 'NIFTY' + str(YY1) + str(MM1) + str(DD1)
        MM0 = datetime.now().strftime('%h')
        month1n = 'NIFTY' + str(YY1) + str(MM0.upper())
        if thursday == 7 or (thursday == 1 and shortweek == 1):
            if DD0 == last_thursday or DD0 == last_thursday - 1:
                MM0 = thursday0.month
                if DD0 == 31:
                    MM1 = datetime.now().replace(month=MM0)
                else:
                    MM1 = datetime.now().replace(month=MM0+1)
                MM1 = MM1.strftime('%h')
                month1n = 'NIFTY' + str(YY1) + str(MM1.upper())
    if datetime.now().strftime('%h') != thursday1.month:
        month1n = 'NIFTY' + str(YY1) + str(thursday1.strftime('%h').upper())
    YY1 += 2000
    MM1 = thursday1.month
    DD1 = int(DD1)
    days_leftn = fromtime1n = datetime(YY1, MM1, DD1, 15, 30) # expiry date (YYYY, MM, DD, HR, MIN)
    if thursday == 7 or (thursday == 1 and shortweek == 1):
        YY0 += 2000
        MM0 = thursday0.month
        DD0 = int(DD0)
        fromtime0n = datetime(YY0, MM0, DD0, 15, 30)
        days_leftn = fromtime0n
    print('Week1 for Nifty is', week1n)
    print('Month1 for Nifty is', month1n)
    print('Time to expiry for Nifty is', days_leftn)

def stbt():
    global trade_table, week1b, fromtime1, strategy, order_placed, SL_D_price, prem, Entry_bid
    global Target1, SL_price, Entry_status, Tgt1_status, SL_status, order_rej, last_tgt
    global last_qty, product, rank, Trade, strike, qty, SL_qty, order_id, days_left, tradingsymbol
    strategy = 'STBT'
    order_placed = 0
    SL_D_price = 'Nil'
    prem = 0
    days_left = fromtime1
    Target1 = 'Nil'
    SL_price = 'Nil'
    Entry_status = 'Ordered'
    Tgt1_status = SL_status = 'NOT EXEC'
    order_rej = 'NO'
    last_tgt = last_qty = 'OPEN'
    product = 'D'
    for c in range(len(client)):
        if client['stbt'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1:
            qty = SL_qty = int(client['stbt'].iloc[c] * 15)
            strike, tradingsymbol = delta_strike(week1b, -0.05, fromtime1)
            rank = 'S05p'
            Trade = 'BUY @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['bids'][0]['price'] + 0.05
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            strike, tradingsymbol = delta_strike(week1b, 0.05, fromtime1)
            rank = 'S05c'
            Trade = 'BUY @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['bids'][0]['price'] + 0.05
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            strike, tradingsymbol = delta_strike(week1b, -0.2, fromtime1)
            rank = 'S20p'
            Trade = 'SELL @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            strike, tradingsymbol = delta_strike(week1b, 0.2, fromtime1)
            rank = 'S20c'
            Trade = 'SELL @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)

def fresh_setup_delta_ironfly(c):
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej, fromtime1
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid, week1b, week0b
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, straddle_table_bank, fromtime0
    Trade = 'SELL @'
    strategy = '3IRONFLY'
    order_placed = 0
    SL_D_price = 'Nil'
    prem = 0
    Target1 = 'Nil'
    SL_price = 'Nil'
    Entry_status = 'Ordered'
    Tgt1_status = SL_status = 'NOT EXEC'
    order_rej = 'NO'
    last_tgt = last_qty = 'OPEN'
    product = 'D'
    if client['D20ironfly'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1:
        if not ((wednesday == 7 or (wednesday == 1 and shortweek == 1)) and time(12, 30) < datetime.now().time() and client['expiry'].iloc[c] >= 1):
            strategy = 'D20ironfly'
            Trade = 'BUY @'
            rank = 'D07c'
            if client['week0'].iloc[c] == 1 and wednesday == 7:
                expiry = week0b
                strike, tradingsymbol = delta_strike(week0b, 0.07, fromtime0)
                strike1, tradingsymbol1 = delta_strike(week0b, (client['Delta'].iloc[c]/100), fromtime0)
                if strike < strike1 + 300:
                    strike = strike1 + 300
                    tradingsymbol = week0b + str(strike) + tradingsymbol[-2:]
                days_left = fromtime0
            elif client['week1'].iloc[c] == 1:
                strike, tradingsymbol = delta_strike(week1b, 0.07, fromtime1)
                days_left = fromtime1
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            print(data['bids'][0]['price'])
            Entry_bid = data['bids'][0]['price'] + 2.5
            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15)
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            rank = 'D07p'
            if client['week0'].iloc[c] == 1 and wednesday == 7:
                expiry = week0b
                strike, tradingsymbol = delta_strike(expiry, (client['Delta'].iloc[c]/100), fromtime0)
                print(tradingsymbol)
                strike, tradingsymbol = delta_strike(week0b, -0.07, fromtime0)
                strike1, tradingsymbol1 = delta_strike(week0b, -(client['Delta'].iloc[c]/100), fromtime0)
                if strike > strike1 - 300:
                    strike = strike1 - 300
                    tradingsymbol = week0b + str(strike) + tradingsymbol[-2:]
                days_left = fromtime0
            elif client['week1'].iloc[c] == 1:
                strike, tradingsymbol = delta_strike(week1b, -0.07, fromtime1)
                days_left = fromtime1
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['bids'][0]['price'] + 2.5
            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15)
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            display_trade()
            rank = 'D20c'
            Trade = 'SELL @'
            if client['week0'].iloc[c] == 1 and wednesday == 7:
                expiry = week0b
                print(expiry)
                print(client['Delta'].iloc[c])
                strike, tradingsymbol = delta_strike(week0b, (client['Delta'].iloc[c]/100), fromtime0)
                days_left = fromtime0
            elif client['week1'].iloc[c] == 1:
                expiry = week1b
                print(expiry)
                print(client['Delta'].iloc[c])
                strike, tradingsymbol = delta_strike(expiry, (client['Delta'].iloc[c]/100), fromtime1)
                print(tradingsymbol)
                days_left = fromtime1
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15)
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Limit,ProductType.Delivery,
                Entry_bid,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            rank = 'D20p'
            if client['week0'].iloc[c] == 1 and wednesday == 7:
                strike, tradingsymbol = delta_strike(week0b, -(client['Delta'].iloc[c]/100), fromtime0)
                days_left = fromtime0
            elif client['week1'].iloc[c] == 1:
                expiry = week1b
                strike, tradingsymbol = delta_strike(expiry, -(client['Delta'].iloc[c]/100), fromtime1)
                days_left = fromtime1
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15)
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Limit,ProductType.Delivery,
                Entry_bid,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
    display_trade()

def single_strangle_entry():
    global trade_table, flag, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    strategy = 'SSTNGLE'
    order_placed = 0
    SL_D_price = 'Nil'
    prem = 0
    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
        days_left = fromtime0
    else:
        days_left = fromtime1
    Target1 = 'Nil'
    SL_price = 'Nil'
    Entry_status = 'Ordered'
    Tgt1_status = SL_status = 'NOT EXEC'
    order_rej = 'NO'
    last_tgt = last_qty = 'OPEN'
    product = 'D'
    for c in range(len(client)):
        if client['sstrgle'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1:
            qty = SL_qty = int(client['sstrgle'].iloc[c] * 15)
            strike, tradingsymbol = delta_strike(week1b, -0.05, days_left)
            rank = 'SS05f'
            Trade = 'BUY @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['bids'][0]['price'] + 0.05
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            strike, tradingsymbol = delta_strike(week1b, 0.05, days_left)
            rank = 'SS05b'
            Trade = 'BUY @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['bids'][0]['price'] + 0.05
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            strike, tradingsymbol = delta_strike(week1b, -0.2, days_left)
            strike1, tradingsymbol1 = delta_strike(week1b, 0.2, days_left)
            rank = 'SS20f'
            Trade = 'SELL @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            strike = strike1
            tradingsymbol = tradingsymbol1
            rank = 'SS20b'
            Trade = 'SELL @'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)

def upgrade(c, y):
    global trade_table, flag, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    print(c, y, 'c and y for upgrade')
    expiry = trade_table[c]['symbol'][y][:-7]
    if trade_table[c]['trade_type'][y] == 'SELL @' and flag['close'][c] == 0:
        if 'CE' in trade_table[c]['symbol'][y] and trade_table[c]['strategy'][y] != 'SSTNGLE':
            strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][y])
        elif 'CE' in trade_table[c]['symbol'][y] and trade_table[c]['strategy'][y] == 'SSTNGLE':
            delta = trade_table[c]['delta'][y] + 0.12
            strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][y])
        elif 'PE' in trade_table[c]['symbol'][y] and trade_table[c]['strategy'][y] != 'SSTNGLE':
            strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][y])
        elif 'PE' in trade_table[c]['symbol'][y] and trade_table[c]['strategy'][y] == 'SSTNGLE':
            delta = trade_table[c]['delta'][y] - 0.12
            strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][y])
        else:
            r = 'not done'
            return r
        if trade_table[c]['symbol'][y] == tradingsymbol:
            r = 'not done'
            return r
        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
            0.0,None,0,DurationType.DAY,None,None,None)
        trade_table[c]['order_id_Sft'][y] = int(order_id['order_id'])
        trade_table[c]['SL_status'][y] = 'Shifted'
        trade_table[c]['3pm_tgt'][y] = 'Shifted'
        trade_table[c]['3pm_tgt_qty'][y] = 'Shifted'
        trade_table[c]['Entry_status'][y] = 'Shifted'
        trade_table[c]['Tgt1_status'][y] = 'Tgt Hit'
        order = pd.DataFrame(u[c].get_order_history())
        try:
            index_upgrade1 = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][y])].index)[0]
            trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index_upgrade1]
        except Exception as e:
            print(e)
            print('Error in upgrade module in getting index_upgrade1')
            trade_table[c]['Tgt1_price'][y] = 0
        trade_table[c]['Tgt1'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['Tgt1_price'][y]) * trade_table[c]['qty'][y]
        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
        trade_table[c]['R.Profit'][y] = trade_table[c]['Tgt1'][y]
        rank = trade_table[c]['rank'][y]
        Trade = 'SELL @'
        strategy = trade_table[c]['strategy'][y]
        order_placed = 0
        SL_D_price = 'Nil'
        prem = 0
        Target1 = 2
        SL_price = 'Nil'
        Entry_status = 'Ordered'
        Tgt1_status = SL_status = 'NOT EXEC'
        order_rej = 'NO'
        last_tgt = last_qty = 'OPEN'
        product = 'D'
        days_left = trade_table[c]['days_left'][y]
        data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
        Entry_bid = data['asks'][0]['price'] - 0.05
        qty = SL_qty = int(trade_table[c]['qty'][y])
        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
            qty,OrderType.Market,ProductType.Delivery,
            0.0,None,0,DurationType.DAY,None,None,None)
        print('sold option')
        order_id = order_id1['order_id']
        order = pd.DataFrame(u[c].get_order_history())
        try:
            index = order[order['order_id'] == int(order_id)].index[0]
        except Exception as e:
            print('error getting order history',e)
            sleep(7)
            order = pd.DataFrame(u[c].get_order_history())
            try:
                index = order[order['order_id'] == int(order_id)].index[0]
            except Exception as e:
                print('Tried again to get order history but failed', e)
                append_excel_table(c)
                return
        if order['status'].iloc[index] == 'rejected':
            print('Order rejected', c, y, datetime.now())
            if trade_table[c]['rank'][y] != 'D20p' and 'PE' in trade_table[c]['symbol'][y]:
                try:
                    ind20p = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']
                        [trade_table[c]['order_rej'] == 'NO']
                        [trade_table[c]['rank'] == 'D20p']).index[0]
                except Exception as e:
                    print('error getting D20p in', c, e)
                    return    
                delta = trade_table[c]['delta'][ind20p] - 0.1
                expiry = trade_table[c]['symbol'][ind20p][:-7]
                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20p])
                if strike == trade_table[c]['strike'][ind20p]:
                    strike = strike + 100
                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                trade_table[c]['SL_status'][ind20p] = 'Closed'
                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                qty = SL_qty = int(trade_table[c]['qty'][ind20p])
                rank = 'D20p'
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                rank = 'D10p' + trade_table[c]['rank'][y][-1:]
                ind10p = (trade_table[c][trade_table[c]['rank'] == rank]
                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                trade_table[c]['SL_status'][ind10p] = 'Closed'
                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
            elif trade_table[c]['rank'][y] != 'D20c' and 'CE' in trade_table[c]['symbol'][y]:
                try:
                    ind20c = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['SL_status'] == 'NOT EXEC']
                        [trade_table[c]['order_rej'] == 'NO']
                        [trade_table[c]['rank'] == 'D20c']).index[0]
                except Exception as e:
                    print('error getting D20c in', c, e)
                    return
                delta = trade_table[c]['delta'][ind20c] + 0.1
                expiry = trade_table[c]['symbol'][ind20c][:-7]
                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20c])
                if strike == trade_table[c]['strike'][ind20c]:
                    strike = strike - 100
                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                trade_table[c]['SL_status'][ind20c] = 'Closed'
                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                qty = SL_qty = int(trade_table[c]['qty'][ind20c])
                rank = 'D20c'
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                rank = 'D10c' + trade_table[c]['rank'][y][-1:]
                ind10c = (trade_table[c][trade_table[c]['rank'] == rank]
                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                trade_table[c]['SL_status'][ind10c] = 'Closed'
                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
            elif trade_table[c]['rank'][y] == 'D20p' and 'PE' in trade_table[c]['symbol'][y]:
                ind07p = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                    [trade_table[c]['Entry_status'] == 'Executed']
                    [trade_table[c]['rank'] == 'D07p']).index[0]
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind07p]),
                    int(trade_table[c]['qty'][ind07p]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind07p] = order_id1['order_id']
                trade_table[c]['SL_status'][ind07p] = 'Closed'
                trade_table[c]['3pm_tgt'][ind07p] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind07p] = 'Closed'
                trade_table[c]['Entry_status'][ind07p] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind07p])].index)[0]
                trade_table[c]['SL_price'][ind07p] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind07p] = (trade_table[c]['SL_price'][ind07p] - trade_table[c]['Entry_price'][ind07p]) * trade_table[c]['qty'][ind07p]
                trade_table[c]['SL_qty'][ind07p] = trade_table[c]['Profit'][ind07p] = 0
                trade_table[c]['R.Profit'][ind07p] = trade_table[c]['SL'][ind07p]
                strike, tradingsymbol = delta_strike(expiry, -0.06, trade_table[c]['days_left'][y])
                if trade_table[c]['symbol'][ind07p] == tradingsymbol:
                    strike = strike + 100
                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                rank = trade_table[c]['rank'][ind07p]
                Trade = 'BUY @'
                strategy = trade_table[c]['strategy'][ind07p]
                order_placed = 0
                SL_D_price = 'Nil'
                prem = 0
                Target1 = 'Nil'
                SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                days_left = trade_table[c]['days_left'][ind07p]
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                qty = SL_qty = int(trade_table[c]['qty'][ind07p])
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][y])
                Trade = 'SELL @'
                rank = 'D20p'
                strategy = trade_table[c]['strategy'][y]
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                qty = SL_qty = int(trade_table[c]['qty'][y])
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
            elif trade_table[c]['rank'][y] == 'D20c' and 'CE' in trade_table[c]['symbol'][y]:
                ind07c = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                    [trade_table[c]['Entry_status'] == 'Executed']
                    [trade_table[c]['rank'] == 'D07c']).index[0]
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind07c]),
                    int(trade_table[c]['qty'][ind07c]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][ind07c] = order_id1['order_id']
                trade_table[c]['SL_status'][ind07c] = 'Closed'
                trade_table[c]['3pm_tgt'][ind07c] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][ind07c] = 'Closed'
                trade_table[c]['Entry_status'][ind07c] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind07c])].index)[0]
                trade_table[c]['SL_price'][ind07c] = order['average_price'].iloc[index]
                trade_table[c]['SL'][ind07c] = (trade_table[c]['SL_price'][ind07c] - trade_table[c]['Entry_price'][ind07c]) * trade_table[c]['qty'][ind07c]
                trade_table[c]['SL_qty'][ind07c] = trade_table[c]['Profit'][ind07c] = 0
                trade_table[c]['R.Profit'][ind07c] = trade_table[c]['SL'][ind07c]
                strike, tradingsymbol = delta_strike(expiry, -0.06, trade_table[c]['days_left'][y])
                if trade_table[c]['symbol'][ind07c] == tradingsymbol:
                    strike = strike + 100
                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                rank = trade_table[c]['rank'][ind07c]
                Trade = 'BUY @'
                strategy = trade_table[c]['strategy'][ind07c]
                order_placed = 0
                SL_D_price = 'Nil'
                prem = 0
                Target1 = 'Nil'
                SL_price = 'Nil'
                Entry_status = 'Ordered'
                Tgt1_status = SL_status = 'NOT EXEC'
                order_rej = 'NO'
                last_tgt = last_qty = 'OPEN'
                product = 'D'
                days_left = trade_table[c]['days_left'][ind07c]
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                qty = SL_qty = int(trade_table[c]['qty'][ind07c])
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][y])
                Trade = 'SELL @'
                rank = 'D20c'
                strategy = trade_table[c]['strategy'][y]
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                qty = SL_qty = int(trade_table[c]['qty'][y])
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
        else:
            append_excel_table(c)
        r = 'done'
        return r
    else:
        if 'CE' in trade_table[c]['symbol'][y] and flag['close'][c] == 0:
            strike, tradingsymbol = delta_strike(expiry, 0.06, trade_table[c]['days_left'][y])
        else:
            strike, tradingsymbol = delta_strike(expiry, -0.06, trade_table[c]['days_left'][y])
        if trade_table[c]['symbol'][y] == tradingsymbol:
            r = 'not done'
            return r
        rank = trade_table[c]['rank'][y]
        Trade = 'BUY @'
        strategy = trade_table[c]['strategy'][y]
        order_placed = 0
        SL_D_price = 'Nil'
        prem = 0
        Target1 = 'Nil'
        SL_price = 'Nil'
        Entry_status = 'Ordered'
        Tgt1_status = SL_status = 'NOT EXEC'
        order_rej = 'NO'
        last_tgt = last_qty = 'OPEN'
        product = 'D'
        days_left = trade_table[c]['days_left'][y]
        try:
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            qty = SL_qty = int(trade_table[c]['qty'][y])
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            print(order_id)
            print(order_id1)
            append_excel_table(c)
            order = pd.DataFrame(u[c].get_order_history())
            index = list(order[order['order_id'] == int(order_id)].index)[0]
            if order['status'].iloc[index] != 'rejected':
                order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                    int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                trade_table[c]['order_id_Sft'][y] = int(order_id['order_id'])
                trade_table[c]['SL_status'][y] = 'Shifted'
                trade_table[c]['3pm_tgt'][y] = 'Shifted'
                trade_table[c]['3pm_tgt_qty'][y] = 'Shifted'
                trade_table[c]['Entry_status'][y] = 'Shifted'
                trade_table[c]['Tgt1_status'][y] = 'Tgt Hit'
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][y])].index)[0]
                trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
                trade_table[c]['Tgt1'][y] = (trade_table[c]['Tgt1_price'][y] - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y]
                trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
                trade_table[c]['R.Profit'][y] = trade_table[c]['Tgt1'][y]
            else:
                print('buy order got rejected in', c)
        except Exception as e:
            print(e)
        # rank = trade_table[c]['rank'][y]
        r = 'done'
        return r

def delta_shift(c, y):
    global trade_table, flag, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    print(trade_table[c]['delta'][y])
    if datetime.now().date() != datetime.strptime(str(trade_table[c]['days_left'][y]).split()[0], '%Y-%m-%d').date() and time(9, 19) <= datetime.now().time():
        # print('checking extreme')
        if (((-0.8 >= trade_table[c]['delta'][y] or trade_table[c]['delta'][y] >= 0.8) and client['Delta'].iloc[c] >= 40) or ((-0.65 >= trade_table[c]['delta'][y] or trade_table[c]['delta'][y] >= 0.65) and client['Delta'].iloc[c] < 40)) and trade_table[c]['trade_type'][y] == 'SELL @' and time(9, 20) <= datetime.now().time():
            expiry = trade_table[c]['symbol'][y][:-7]
            if 'CE' in trade_table[c]['symbol'][y]:
                strike, tradingsymbol = delta_strike(expiry, 0.55, trade_table[c]['days_left'][y])
            else:
                strike, tradingsymbol = delta_strike(expiry, -0.55, trade_table[c]['days_left'][y])
            if trade_table[c]['symbol'][y] == tradingsymbol:
                return
            order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
                int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            trade_table[c]['order_id_Sft'][y] = int(order_id['order_id'])
            trade_table[c]['SL_status'][y] = 'Shifted'
            trade_table[c]['3pm_tgt'][y] = 'Shifted'
            trade_table[c]['3pm_tgt_qty'][y] = 'Shifted'
            trade_table[c]['Entry_status'][y] = 'Shifted'
            trade_table[c]['Tgt1_status'][y] = 'Tgt Hit'
            order = pd.DataFrame(u[c].get_order_history())
            try:
                index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][y])].index)[0]
                trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
            except Exception as e:
                print('get order history failed in delta_shift', e)
                trade_table[c]['Tgt1_price'][y] = 0
            trade_table[c]['Tgt1'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['Tgt1_price'][y]) * trade_table[c]['qty'][y]
            trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
            trade_table[c]['R.Profit'][y] = trade_table[c]['Tgt1'][y]
            rank = trade_table[c]['rank'][y]
            Trade = 'SELL @'
            strategy = trade_table[c]['strategy'][y]
            order_placed = 0
            SL_D_price = 'Nil'
            prem = 0
            Target1 = 2
            SL_price = 'Nil'
            Entry_status = 'Ordered'
            Tgt1_status = SL_status = 'NOT EXEC'
            order_rej = 'NO'
            last_tgt = last_qty = 'OPEN'
            product = 'D'
            days_left = trade_table[c]['days_left'][y]
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            qty = SL_qty = int(trade_table[c]['qty'][y])
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            return
    else:
        # if time(12, 40) <= datetime.now().time() <= time(12, 42) and client['expiry'].iloc[c] >= 1 and (thursday == 7 or (thursday == 1 and shortweek == 1)):
        #         close_and_fresh(c)
        if time(13, 1) <= datetime.now().time() <= time(13, 3):# and client['expiry'].iloc[c] == 0:
            if (flag['call_delta'][c] < 0.45 and flag['put_delta'][c] > -0.45) or (client['expiry'].iloc[c] >= 1 and (wednesday == 7 or (wednesday == 1 and shortweek == 1))):
                flag['ironfly_close'][c] = 1
            else:
                flag['ironfly_close'][c] = 2
        if flag['ironfly_close'][c] == 1:
            if flag['call_delta'][c] > 0.45 or flag['put_delta'][c] < -0.45:
                flag['ironfly_shift'][c] = 0
                flag['call_delta'][c] = 0
                flag['put_delta'][c] = 0
                flag['double_call'][c] = 0
                flag['double_put'][c] = 0
                flag['ironfly_close'][c] = 0
                close_and_fresh(c)
                if client['expiry'].iloc[c] >= 1 and client['week0'].iloc[c] == 1 and (wednesday == 7 or (wednesday == 1 and shortweek == 1)):
                    if client['D20ironfly'].iloc[c] >= 1:
                        fresh_setup_delta_ironfly(c)
        if time(14, 35) <= datetime.now().time() and flag['ironfly_close'][c] >= 1:
            flag['ironfly_shift'][c] = 0
            flag['call_delta'][c] = 0
            flag['put_delta'][c] = 0
            flag['double_call'][c] = 0
            flag['double_put'][c] = 0
            flag['ironfly_close'][c] = 0
            close_and_fresh(c)
            if client['expiry'].iloc[c] >= 1 and client['week0'].iloc[c] == 1 and (wednesday == 7 or (wednesday == 1 and shortweek == 1)):
                if client['D20ironfly'].iloc[c] >= 1:
                    fresh_setup_delta_ironfly(c)
    if -0.10 <= trade_table[c]['delta'][y] <= 0.10 and trade_table[c]['trade_type'][y] == 'SELL @' and time(9, 20) <= datetime.now().time():
        if trade_table[c]['delta'][y] != 0:
            print('Shifting sellers')
            r = upgrade(c, y)
    elif -0.04 <= trade_table[c]['delta'][y] <= 0.04 and trade_table[c]['trade_type'][y] == 'BUY @' and time(9, 20) <= datetime.now().time():
        if datetime.now().date() != datetime.strptime(str(trade_table[c]['days_left'][y]).split()[0], '%Y-%m-%d').date() or time(9, 45) >= datetime.now().time() >= time(9, 20):
            print('Shifting insurance')
            r = upgrade(c, y)
    elif (-0.65 >= trade_table[c]['delta'][y] or trade_table[c]['delta'][y] >= 0.65) and trade_table[c]['trade_type'][y] == 'SELL @' and time(9, 20) <= datetime.now().time():
        expiry = trade_table[c]['symbol'][y][:-7]
        if 'CE' in trade_table[c]['symbol'][y]:
            strike, tradingsymbol = delta_strike(expiry, 0.55, trade_table[c]['days_left'][y])
        else:
            strike, tradingsymbol = delta_strike(expiry, -0.55, trade_table[c]['days_left'][y])
        if trade_table[c]['symbol'][y] == tradingsymbol:
            return
        order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(trade_table[c]['exchange'][y],trade_table[c]['symbol'][y]),
            int(trade_table[c]['SL_qty'][y]),OrderType.Market,ProductType.Delivery,
            0.0,None,0,DurationType.DAY,None,None,None)
        trade_table[c]['order_id_Sft'][y] = int(order_id['order_id'])
        trade_table[c]['SL_status'][y] = 'Shifted'
        trade_table[c]['3pm_tgt'][y] = 'Shifted'
        trade_table[c]['3pm_tgt_qty'][y] = 'Shifted'
        trade_table[c]['Entry_status'][y] = 'Shifted'
        trade_table[c]['Tgt1_status'][y] = 'Tgt Hit'
        order = pd.DataFrame(u[c].get_order_history())
        try:
            index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][y])].index)[0]
            trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
        except Exception as e:
            print('get order history failed', e)
            try:
                sleep(3)
                order = pd.DataFrame(u[c].get_order_history())
                index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][y])].index)[0]
                trade_table[c]['Tgt1_price'][y] = order['average_price'].iloc[index]
            except Exception as e:
                print('Tried again to get order history but failed', e)
                trade_table[c]['Tgt1_price'][y] = 0
        trade_table[c]['Tgt1'][y] = (trade_table[c]['Entry_price'][y] - trade_table[c]['Tgt1_price'][y]) * trade_table[c]['qty'][y]
        trade_table[c]['SL_qty'][y] = trade_table[c]['Profit'][y] = 0
        trade_table[c]['R.Profit'][y] = trade_table[c]['Tgt1'][y]
        rank = trade_table[c]['rank'][y]
        Trade = 'SELL @'
        strategy = trade_table[c]['strategy'][y]
        order_placed = 0
        SL_D_price = 'Nil'
        prem = 0
        Target1 = 2
        SL_price = 'Nil'
        Entry_status = 'Ordered'
        Tgt1_status = SL_status = 'NOT EXEC'
        order_rej = 'NO'
        last_tgt = last_qty = 'OPEN'
        product = 'D'
        days_left = trade_table[c]['days_left'][y]
        data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
        Entry_bid = data['asks'][0]['price'] - 0.05
        qty = SL_qty = int(trade_table[c]['qty'][y])
        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
            qty,OrderType.Market,ProductType.Delivery,
            0.0,None,0,DurationType.DAY,None,None,None)
        order_id = order_id1['order_id']
        append_excel_table(c)
        return

def call_price(sigma, S, K, r, t, d1, d2):
    C = norm.cdf(d1) * S - norm.cdf(d2) * K * np.exp(-r * t)
    return C

def put_price(sigma, S, K, r, t, d1, d2):
    P = -norm.cdf(-d1) * S + norm.cdf(-d2) * K * np.exp(-r * t)
    return P

def chart():
    global Chart_table, chart_display
    Chart_table = [pd.DataFrame(columns=[
        'price', 'current', 'final' , 'spot'
    ])] * len(client)
    try:
        last_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
    except Exception as e:
        print(e)
        try:
            data_bank = s.get_ohlc(
                s.get_instrument_by_symbol(
                    'NSE_INDEX', 'NIFTY_BANK'
                    ),
                OHLCInterval.Minute_1, datetime.strptime(
                    '{}'.format(to_date), '%d/%m/%Y'
                    ).date(), datetime.strptime(
                        '{}'.format(to_date), '%d/%m/%Y'
                        ).date())
            data_bank = pd.DataFrame(data_bank)
            data_bank = data_bank.astype(
                {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
            last_price = data_bank['close'].iloc[-1]
        except Exception as e:
            print(e)
            print('W a r n i n g !!!   L o s t  C o n n e c t i o n')
            return
    last_price_0 = round(last_price/100) * 100
    strike = [(last_price_0 - 2000), (last_price_0 - 1900), (last_price_0 - 1800), (last_price_0 - 1700), (last_price_0 - 1600), (last_price_0 - 1500), (last_price_0 - 1400), (last_price_0 - 1300), (last_price_0 - 1200), (last_price_0 - 1100), (last_price_0 - 1000), (last_price_0 - 900), (last_price_0 - 800), (last_price_0 - 700), (last_price_0 - 600), (last_price_0 - 500), (last_price_0 - 400), (last_price_0 - 300), (last_price_0 - 200), (last_price_0 - 100), last_price_0, (last_price_0 + 100), (last_price_0 + 200), (last_price_0 + 300), (last_price_0 + 400), (last_price_0 + 500), (last_price_0 + 600), (last_price_0 + 700), (last_price_0 + 800), (last_price_0 + 900), (last_price_0 + 1000), (last_price_0 + 1100), (last_price_0 + 1200), (last_price_0 + 1300), (last_price_0 + 1400), (last_price_0 + 1500), (last_price_0 + 1600), (last_price_0 + 1700), (last_price_0 + 1800), (last_price_0 + 1900), (last_price_0 + 2000), (last_price_0 + 2100), (last_price_0 + 2200), (last_price_0 + 2300), (last_price_0 + 2400), (last_price_0 + 2500)]
    for c in range(len(client)):
        try:
            totime = datetime.now()
            t1 = trade_table[c]['days_left'][0] - totime
            a = t1/timedelta(days=1)
            tg = float(a/365)
            for strike_price in strike:
                current = 0
                final = 0
                for y in range(len(trade_table[c])):
                    if trade_table[c]['3pm_tgt'][y] == 'OPEN' and trade_table[c]['strategy'][y] != 'FUT':
                        IV = iv(trade_table[c]['symbol'][y], trade_table[c]['strike'][y], trade_table[c]['LTP'][y], last_price, tg)
                        d1, d2 = d(IV, strike_price, trade_table[c]['strike'][y], 0.1, tg)
                        if 'CE' in trade_table[c]['symbol'][y] and trade_table[c]['trade_type'][y] == 'BUY @':
                            current += (call_price(IV, strike_price, trade_table[c]['strike'][y], 0.1, tg, d1, d2) * trade_table[c]['qty'][y]) - (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            # final += (call_price(IV, strike_price, trade_table[c]['strike'][y], 0.1, 0.0, d1, d2) * trade_table[c]['qty'][y])
                            if trade_table[c]['strike'][y] - strike_price >= 0:
                                final -= (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            else:
                                diff = strike_price - trade_table[c]['strike'][y]
                                final -= ((trade_table[c]['Entry_price'][y] - diff) * trade_table[c]['qty'][y])
                        elif 'CE' in trade_table[c]['symbol'][y] and trade_table[c]['trade_type'][y] == 'SELL @':
                            current -= (call_price(IV, strike_price, trade_table[c]['strike'][y], 0.1, tg, d1, d2) * trade_table[c]['qty'][y]) - (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            if trade_table[c]['strike'][y] - strike_price >= 0:
                                final += (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            else:
                                diff = strike_price - trade_table[c]['strike'][y]
                                final += ((trade_table[c]['Entry_price'][y] - diff) * trade_table[c]['qty'][y])
                        elif 'PE' in trade_table[c]['symbol'][y] and trade_table[c]['trade_type'][y] == 'BUY @':
                            current += (put_price(IV, strike_price, trade_table[c]['strike'][y], 0.1, tg, d1, d2) * trade_table[c]['qty'][y]) - (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            if trade_table[c]['strike'][y] - strike_price <= 0:
                                final -= (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            else:
                                diff = trade_table[c]['strike'][y] - strike_price
                                final += ((diff - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y])
                        elif 'PE' in trade_table[c]['symbol'][y] and trade_table[c]['trade_type'][y] == 'SELL @':
                            current -= (put_price(IV, strike_price, trade_table[c]['strike'][y], 0.1, tg, d1, d2) * trade_table[c]['qty'][y]) - (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            if trade_table[c]['strike'][y] - strike_price <= 0:
                                final += (trade_table[c]['Entry_price'][y] * trade_table[c]['qty'][y])
                            else:
                                diff = trade_table[c]['strike'][y] - strike_price
                                final -= ((diff - trade_table[c]['Entry_price'][y]) * trade_table[c]['qty'][y])
                    elif trade_table[c]['strategy'][y] != 'FUT':
                        current += trade_table[c]['R.Profit'][y]
                        final += trade_table[c]['R.Profit'][y]
                current += flag['prev_profit'][c]
                final += flag['prev_profit'][c]
                Chart_table[c] = Chart_table[c].append({'price': strike_price, 'current': current, 'final': final }, ignore_index=True)
            Chart_table[c] = Chart_table[c].append({'price': last_price, 'spot': Chart_table[c]['final'].max()*1.1 }, ignore_index=True)
            Chart_table[c] = Chart_table[c].append({'price': last_price, 'spot': Chart_table[c]['final'].min()*1.1 }, ignore_index=True)
            if c == 0:
                chart_display[c] = 2
            else:
                chart_display[c] = 3 + chart_display[c-1] + len(Chart_table[c-1])
                charts.range('A' + str(chart_display[c] - 2)).value = white_space
            charts.range('A' + str(chart_display[c])).options(index=False).value = Chart_table[c]
            print('charting done')
        except Exception as e:
            print(e)
            pass

def double():
    global trade_table, flag, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty
    print('Double requirement check')
    for c in range(len(client)):
        if len(trade_table[c]) != 0:
            flag['call_delta'][c] = flag['put_delta'][c] = 0.0
            flag['scall_delta'][c] = flag['sput_delta'][c] = 0.0
            for i in range(len(trade_table[c])):
                if 'c' in trade_table[c]['rank'][i] and trade_table[c]['Entry_status'][i] == 'Executed' and client['D20ironfly'].iloc[c] > 0:
                    if trade_table[c]['trade_type'][i] == 'SELL @':
                        flag['call_delta'][c] += float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['D20ironfly'].iloc[c] / 15)
                    else:
                        flag['call_delta'][c] -= float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['D20ironfly'].iloc[c] / 15)
                elif 'p' in trade_table[c]['rank'][i] and trade_table[c]['Entry_status'][i] == 'Executed' and client['D20ironfly'].iloc[c] > 0:
                    if trade_table[c]['trade_type'][i] == 'SELL @':
                        flag['put_delta'][c] += float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['D20ironfly'].iloc[c] / 15)
                    else:
                        flag['put_delta'][c] -= float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['D20ironfly'].iloc[c] / 15)
                elif 'b' in trade_table[c]['rank'][i] and trade_table[c]['Entry_status'][i] == 'Executed' and client['sstrgle'].iloc[c] > 0:
                    if trade_table[c]['trade_type'][i] == 'SELL @':
                        flag['scall_delta'][c] += float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['sstrgle'].iloc[c] / 15)
                    else:
                        flag['scall_delta'][c] -= float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['sstrgle'].iloc[c] / 15)
                elif 'f' in trade_table[c]['rank'][i] and trade_table[c]['Entry_status'][i] == 'Executed' and client['sstrgle'].iloc[c] > 0:
                    if trade_table[c]['trade_type'][i] == 'SELL @':
                        flag['sput_delta'][c] += float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['sstrgle'].iloc[c] / 15)
                    else:
                        flag['sput_delta'][c] -= float(trade_table[c]['delta'][i] * trade_table[c]['qty'][i] / client['sstrgle'].iloc[c] / 15)
            if client['D20ironfly'].iloc[c] > 0 and time(9, 20) <= datetime.now().time() <= time(15, 20):
                try:
                    ind20p = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == 'D20p']).index[0]
                    ind07p = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == 'D07p']).index[0]
                    if (trade_table[c]['strike'][ind20p] - trade_table[c]['strike'][ind07p]) <= 100:
                        flag['put_delta'][c] -= 0.1
                    ind20c = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == 'D20c']).index[0]
                    ind07c = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                        [trade_table[c]['Entry_status'] == 'Executed']
                        [trade_table[c]['rank'] == 'D07c']).index[0]
                    if (trade_table[c]['strike'][ind07c] - trade_table[c]['strike'][ind20c]) <= 100:
                        flag['call_delta'][c] += 0.1
                except Exception as e:
                    print('Error in getting base', c, e)
                    try:
                        ind20c = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['order_rej'] == 'YES']
                            [trade_table[c]['rank'] == 'D20c']).index[0]
                        if flag['closing_profit'][c] == 0:
                            flag['closing_profit'][c] = flag['profit'][c]
                        else:
                            if flag['profit'][c] > flag['closing_profit'][c]:
                                flag['closing_profit'][c] = flag['profit'][c]
                            elif flag['profit'][c] < flag['closing_profit'][c] - (client['D20ironfly'].iloc[c] * 500):
                                close_and_fresh(c)
                                fresh_setup_delta_ironfly(c)
                    except Exception as e:
                        print('Call is OK', c, e)
                    try:
                        ind20p = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['order_rej'] == 'YES']
                            [trade_table[c]['rank'] == 'D20p']).index[0]
                        if flag['closing_profit'][c] == 0:
                            flag['closing_profit'][c] = flag['profit'][c]
                        else:
                            if flag['profit'][c] > flag['closing_profit'][c]:
                                flag['closing_profit'][c] = flag['profit'][c]
                            elif flag['profit'][c] < flag['closing_profit'][c] - (client['D20ironfly'].iloc[c] * 500):
                                close_and_fresh(c)
                                fresh_setup_delta_ironfly(c)
                    except Exception as e:
                        print('Put is OK', c, e)
                if ((flag['call_delta'][c] + flag['put_delta'][c]) > 0.25 and client['shift'].iloc[c] == 0) or (client['shift'].iloc[c] != 0 and (flag['call_delta'][c] + flag['put_delta'][c]) > client['shift'].iloc[c]):
                    print('Delta is ', flag['call_delta'][c] + flag['put_delta'][c])
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D20p']).index[0]
                    except Exception as e:
                        print('Error in getting base put', c, e)
                        continue
                    if trade_table[c]['delta'][ind] > -0.15:
                        r = upgrade(c, ind)
                        if r == 'done':
                            continue
                    if flag['double_call'][c] == 3:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D20c3']).index[0]
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error in getting order history in double call 3', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D10c3']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        flag['double_call'][c] = 2
                    elif flag['double_call'][c] == 2:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D20c2']).index[0]
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D10c2']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        flag['double_call'][c] = 1
                    elif flag['double_call'][c] == 1:
                        if flag['double_put'][c] == 0:
                            flag['double_put'][c] = 1
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, -0.07, trade_table[c]['days_left'][ind])
                            if strike > strike1 - 300:
                                strike = strike1 - 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10p1'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            if strike > trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20p1'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Tried again to get order history but failed', e)
                                    append_excel_table(c)
                                    print('Check if D20p1 rejected')
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20p] - 0.1
                                expiry = trade_table[c]['symbol'][ind20p][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20p])
                                if strike == trade_table[c]['strike'][ind20p]:
                                    strike = strike + 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                                trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20p])
                                rank = 'D20p'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10p = (trade_table[c][trade_table[c]['rank'] == 'D10p1']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                                trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
                                flag['double_put'][c] = 0
                            else:
                                append_excel_table(c)
                        elif flag['double_put'][c] == 1:
                            flag['double_put'][c] = 2
                            expiry = trade_table[c]['symbol'][i][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, -0.07, trade_table[c]['days_left'][ind])
                            if strike > strike1 - 300:
                                strike = strike1 - 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10p2'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            if strike > trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20p2'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Tried again to get order history but failed', e)
                                    append_excel_table(c)
                                    print('Check if D20p2 rejected')
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20p] - 0.1
                                expiry = trade_table[c]['symbol'][ind20p][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20p])
                                if strike == trade_table[c]['strike'][ind20p]:
                                    strike = strike + 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                                trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20p])
                                rank = 'D20p'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10p = (trade_table[c][trade_table[c]['rank'] == 'D10p2']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                                trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
                                flag['double_put'][c] = 1
                            else:
                                append_excel_table(c)
                        elif flag['double_put'][c] == 2:
                            try:
                                ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                        [trade_table[c]['Entry_status'] == 'Executed']
                                        [trade_table[c]['rank'] == 'D20c1']).index[0]
                            except Exception as e:
                                print('Error in getting D20c1 in', c, e)
                                ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                    [trade_table[c]['Entry_status'] == 'Executed']
                                    [trade_table[c]['rank'] == 'D10c1']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                    int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                                trade_table[c]['Entry_status'][ind] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                                trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                                trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                                flag['double_call'][c] = 0
                                return
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            trade_table[c]['SL_id'][ind] = order_id1['order_id']
                            trade_table[c]['SL_status'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                            trade_table[c]['Entry_status'][ind] = 'Closed'
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                trade_table[c]['SL_price'][ind] = 0
                            trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                            trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                            trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                            ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                [trade_table[c]['Entry_status'] == 'Executed']
                                [trade_table[c]['rank'] == 'D10c1']).index[0]
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            trade_table[c]['SL_id'][ind] = order_id1['order_id']
                            trade_table[c]['SL_status'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                            trade_table[c]['Entry_status'][ind] = 'Closed'
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                trade_table[c]['SL_price'][ind] = 0
                            trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                            trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                            trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                            flag['double_call'][c] = 0
                    elif flag['double_call'][c] == 0:
                        if flag['double_put'][c] == 2:
                            flag['double_put'][c] = 3
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, -0.07, trade_table[c]['days_left'][ind])
                            if strike > strike1 - 300:
                                strike = strike1 - 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10p3'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            if strike > trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20p3'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Tried again to get order history but failed', e)
                                    append_excel_table(c)
                                    print('Check if D20p3 rejected')
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20p] - 0.1
                                expiry = trade_table[c]['symbol'][ind20p][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20p])
                                if strike == trade_table[c]['strike'][ind20p]:
                                    strike = strike + 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                                trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20p])
                                rank = 'D20p'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10p = (trade_table[c][trade_table[c]['rank'] == 'D10p3']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                                trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
                                flag['double_put'][c] = 2
                            else:
                                append_excel_table(c)
                        elif flag['double_put'][c] == 1:
                            flag['double_put'][c] = 2
                            expiry = trade_table[c]['symbol'][i][:-7]
                            print(trade_table[c]['symbol'][i])
                            print(expiry, c, i)
                            strike1, tradingsymbol1 = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, -0.07, trade_table[c]['days_left'][ind])
                            if strike > strike1 - 300:
                                strike = strike1 - 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10p2'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            if strike > trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20p2'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Tried again to get order history but failed', e)
                                    append_excel_table(c)
                                    print('Check if D20p2 rejected')
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20p] - 0.1
                                expiry = trade_table[c]['symbol'][ind20p][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20p])
                                if strike == trade_table[c]['strike'][ind20p]:
                                    strike = strike + 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                                trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20p])
                                rank = 'D20p'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10p = (trade_table[c][trade_table[c]['rank'] == 'D10p2']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                                trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
                                flag['double_put'][c] = 1
                            else:
                                append_excel_table(c)
                        elif flag['double_put'][c] == 0:
                            flag['double_put'][c] = 1
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, -0.07, trade_table[c]['days_left'][ind])
                            if strike > strike1 - 300:
                                strike = strike1 - 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10p1'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, -0.2, trade_table[c]['days_left'][ind])
                            if strike > trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20p1'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history in', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Check D20p1 Error in getting order history 2nd time in', c, e)
                                    append_excel_table(c)
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20p] - 0.1
                                expiry = trade_table[c]['symbol'][ind20p][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20p])
                                if strike == trade_table[c]['strike'][ind20p]:
                                    strike = strike + 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20p]),
                                    int(trade_table[c]['qty'][ind20p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20p] = 'Closed'
                                trade_table[c]['Entry_status'][ind20p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                try:
                                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20p])].index)[0]
                                    trade_table[c]['SL_price'][ind20p] = order['average_price'].iloc[index]
                                except Exception as e:
                                    print('Error in getting order history', c, e)    
                                    trade_table[c]['SL_price'][ind20p] = 0
                                trade_table[c]['SL'][ind20p] = (trade_table[c]['Entry_price'][ind20p] - trade_table[c]['SL_price'][ind20p]) * trade_table[c]['qty'][ind20p]
                                trade_table[c]['SL_qty'][ind20p] = trade_table[c]['Profit'][ind20p] = 0
                                trade_table[c]['R.Profit'][ind20p] = trade_table[c]['SL'][ind20p]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20p])
                                rank = 'D20p'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10p = (trade_table[c][trade_table[c]['rank'] == 'D10p1']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10p]),
                                    int(trade_table[c]['qty'][ind10p]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10p] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10p] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10p] = 'Closed'
                                trade_table[c]['Entry_status'][ind10p] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                try:
                                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10p])].index)[0]
                                    trade_table[c]['SL_price'][ind10p] = order['average_price'].iloc[index]
                                except Exception as e:
                                    print('Error in getting order history', c, e)    
                                    trade_table[c]['SL_price'][ind10p] = 0
                                trade_table[c]['SL'][ind10p] = (trade_table[c]['SL_price'][ind10p] - trade_table[c]['Entry_price'][ind10p]) * trade_table[c]['qty'][ind10p]
                                trade_table[c]['SL_qty'][ind10p] = trade_table[c]['Profit'][ind10p] = 0
                                trade_table[c]['R.Profit'][ind10p] = trade_table[c]['SL'][ind10p]
                                flag['double_put'][c] = 0
                            else:
                                append_excel_table(c)
                        elif flag['double_put'][c] == 3:
                            ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                [trade_table[c]['Entry_status'] == 'Executed']
                                [trade_table[c]['rank'] == 'D20c']).index[0]
                            new = trade_table[c]['delta'][ind] - 0.15
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike, tradingsymbol = delta_strike(expiry, new, trade_table[c]['days_left'][ind])
                            if strike == trade_table[c]['strike'][ind]:
                                continue
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            trade_table[c]['SL_id'][ind] = order_id1['order_id']
                            trade_table[c]['SL_status'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                            trade_table[c]['Entry_status'][ind] = 'Closed'
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                            except Exception as e:
                                trade_table[c]['SL_price'][ind] = 0
                            trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                            trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                            trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                            rank = trade_table[c]['rank'][ind]
                            Trade = 'SELL @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15)
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                elif ((flag['call_delta'][c] + flag['put_delta'][c]) < -0.25 and client['shift'].iloc[c] == 0) or (client['shift'].iloc[c] != 0 and (flag['call_delta'][c] + flag['put_delta'][c]) < -(client['shift'].iloc[c])):
                    print('Delta is ', flag['call_delta'][c] + flag['put_delta'][c])
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D20c']).index[0]
                    except Exception as e:
                        print('Error in getting base call', c, e)
                        continue
                    if trade_table[c]['delta'][ind] < 0.18:
                        r = upgrade(c, ind)
                        if r == 'done':
                            continue
                    if flag['double_put'][c] == 3:
                        try:
                            ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                [trade_table[c]['Entry_status'] == 'Executed']
                                [trade_table[c]['rank'] == 'D20p3']).index[0]
                        except Exception as e:
                            print('Error in getting D20p3 put for', c, e)
                            continue
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error in getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D10p3']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error in getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        flag['double_put'][c] = 2
                    elif flag['double_put'][c] == 2:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D20p2']).index[0]
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error in getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D10p2']).index[0]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                            int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                        trade_table[c]['Entry_status'][ind] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        try:
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                        except Exception as e:
                            print('Error in getting order history', c, e)
                            trade_table[c]['SL_price'][ind] = 0
                        trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                        trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                        trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                        flag['double_put'][c] = 1
                    elif flag['double_put'][c] == 1:
                        if flag['double_call'][c] == 0:
                            flag['double_call'][c] = 1
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, 0.07, trade_table[c]['days_left'][ind])
                            if strike < strike1 + 300:
                                strike = strike1 + 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10c1'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            if strike < trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20c1'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:    
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Tried again to get order history but failed', e)
                                    append_excel_table(c)
                                    print('Check if D20c1 rejected')
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20c] + 0.1
                                expiry = trade_table[c]['symbol'][ind20c][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20c])
                                if strike == trade_table[c]['strike'][ind20c]:
                                    strike = strike - 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                try:
                                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                                    trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                                except Exception as e:
                                    print('Error in getting order history in', c, e)
                                    trade_table[c]['SL_price'][ind20c] = 0
                                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20c])
                                rank = 'D20c'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10c = (trade_table[c][trade_table[c]['rank'] == 'D10c1']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
                                flag['double_call'][c] = 0
                            else:
                                append_excel_table(c)
                        elif flag['double_call'][c] == 1:
                            flag['double_call'][c] = 2
                            expiry = trade_table[c]['symbol'][i][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, 0.07, trade_table[c]['days_left'][ind])
                            if strike < strike1 + 300:
                                strike = strike1 + 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10c2'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            if strike < trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20c2'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Tried again to get order history but failed', e)
                                    append_excel_table(c)
                                    print('Check if D20c2 rejected')
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20c] + 0.1
                                expiry = trade_table[c]['symbol'][ind20c][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20c])
                                if strike == trade_table[c]['strike'][ind20c]:
                                    strike = strike - 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                try:
                                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                                    trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                                except Exception as e:
                                    print('Error in getting order history in', c, e)
                                    trade_table[c]['SL_price'][ind20c] = 0
                                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20c])
                                rank = 'D20c'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10c = (trade_table[c][trade_table[c]['rank'] == 'D10c2']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
                                flag['double_call'][c] = 1
                            else:
                                append_excel_table(c)
                        elif flag['double_call'][c] == 2:
                            ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                [trade_table[c]['Entry_status'] == 'Executed']
                                [trade_table[c]['rank'] == 'D20p1']).index[0]
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            trade_table[c]['SL_id'][ind] = order_id1['order_id']
                            trade_table[c]['SL_status'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                            trade_table[c]['Entry_status'][ind] = 'Closed'
                            order = pd.DataFrame(u[c].get_order_history())
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                            trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                            trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                            trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                            ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                                [trade_table[c]['Entry_status'] == 'Executed']
                                [trade_table[c]['rank'] == 'D10p1']).index[0]
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            trade_table[c]['SL_id'][ind] = order_id1['order_id']
                            trade_table[c]['SL_status'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                            trade_table[c]['Entry_status'][ind] = 'Closed'
                            order = pd.DataFrame(u[c].get_order_history())
                            index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                            trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                            trade_table[c]['SL'][ind] = (trade_table[c]['SL_price'][ind] - trade_table[c]['Entry_price'][ind]) * trade_table[c]['qty'][ind]
                            trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                            trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                            flag['double_put'][c] = 0
                    elif flag['double_put'][c] == 0:
                        if flag['double_call'][c] == 0:
                            flag['double_call'][c] = 1
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, 0.07, trade_table[c]['days_left'][ind])
                            if strike < strike1 + 300:
                                strike = strike1 + 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10c1'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            if strike < trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20c1'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Check D20c1 Error in getting order history in', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Error in getting order history 2nd time in', c, e)
                                    append_excel_table(c)
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20c] + 0.1
                                expiry = trade_table[c]['symbol'][ind20c][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20c])
                                if strike == trade_table[c]['strike'][ind20c]:
                                    strike = strike - 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                                trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20c])
                                rank = 'D20c'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10c = (trade_table[c][trade_table[c]['rank'] == 'D10c1']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
                                flag['double_call'][c] = 0
                            else:
                                append_excel_table(c)
                        elif flag['double_call'][c] == 1:
                            flag['double_call'][c] = 2
                            expiry = trade_table[c]['symbol'][i][:-7]
                            print(expiry)
                            strike1, tradingsymbol1 = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, 0.07, trade_table[c]['days_left'][ind])
                            if strike < strike1 + 300:
                                strike = strike1 + 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10c2'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            if strike < trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20c2'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history in', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Check D20c2 Error in getting order history 2nd time in', c, e)
                                    append_excel_table(c)
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20c] + 0.1
                                expiry = trade_table[c]['symbol'][ind20c][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20c])
                                if strike == trade_table[c]['strike'][ind20c]:
                                    strike = strike - 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                                trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20c])
                                rank = 'D20c'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10c = (trade_table[c][trade_table[c]['rank'] == 'D10c2']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
                                flag['double_call'][c] = 1
                            else:
                                append_excel_table(c)
                        elif flag['double_call'][c] == 2:
                            flag['double_call'][c] = 3
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike1, tradingsymbol1 = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            strike, tradingsymbol = delta_strike(expiry, 0.07, trade_table[c]['days_left'][ind])
                            if strike < strike1 + 300:
                                strike = strike1 + 300
                                tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                            rank = 'D10c3'
                            Trade = 'BUY @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['bids'][0]['price'] + 0.05
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15 / 2)
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
                            strike, tradingsymbol = delta_strike(expiry, 0.2, trade_table[c]['days_left'][ind])
                            if strike < trade_table[c]['strike'][ind]:
                                strike = trade_table[c]['strike'][ind]
                                tradingsymbol = trade_table[c]['symbol'][ind]
                            rank = 'D20c3'
                            Trade = 'SELL @'
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = order[order['order_id'] == int(order_id)].index[0]
                            except Exception as e:
                                print('Error in getting order history in', c, e)
                                try:
                                    sleep(3)
                                    order = pd.DataFrame(u[c].get_order_history())
                                    index = order[order['order_id'] == int(order_id)].index[0]
                                except Exception as e:
                                    print('Check D20c3 Error in getting order history 2nd time in', c, e)
                                    append_excel_table(c)
                                    return
                            if order['status'].iloc[index] == 'rejected':
                                print('Order rejected')
                                delta = trade_table[c]['delta'][ind20c] + 0.1
                                expiry = trade_table[c]['symbol'][ind20c][:-7]
                                strike, tradingsymbol = delta_strike(expiry, delta, trade_table[c]['days_left'][ind20c])
                                if strike == trade_table[c]['strike'][ind20c]:
                                    strike = strike - 100
                                    tradingsymbol = expiry + str(strike) + tradingsymbol[-2:]
                                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind20c]),
                                    int(trade_table[c]['qty'][ind20c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind20c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind20c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind20c] = 'Closed'
                                trade_table[c]['Entry_status'][ind20c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind20c])].index)[0]
                                trade_table[c]['SL_price'][ind20c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind20c] = (trade_table[c]['Entry_price'][ind20c] - trade_table[c]['SL_price'][ind20c]) * trade_table[c]['qty'][ind20c]
                                trade_table[c]['SL_qty'][ind20c] = trade_table[c]['Profit'][ind20c] = 0
                                trade_table[c]['R.Profit'][ind20c] = trade_table[c]['SL'][ind20c]
                                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                                Entry_bid = data['asks'][0]['price'] - 0.05
                                qty = SL_qty = int(trade_table[c]['qty'][ind20c])
                                rank = 'D20c'
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                    qty,OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                order_id = order_id1['order_id']
                                append_excel_table(c)
                                ind10c = (trade_table[c][trade_table[c]['rank'] == 'D10c3']
                                    [trade_table[c]['SL_status'] == 'NOT EXEC']).index[0]
                                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind10c]),
                                    int(trade_table[c]['qty'][ind10c]),OrderType.Market,ProductType.Delivery,
                                    0.0,None,0,DurationType.DAY,None,None,None)
                                trade_table[c]['SL_id'][ind10c] = order_id1['order_id']
                                trade_table[c]['SL_status'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt'][ind10c] = 'Closed'
                                trade_table[c]['3pm_tgt_qty'][ind10c] = 'Closed'
                                trade_table[c]['Entry_status'][ind10c] = 'Closed'
                                order = pd.DataFrame(u[c].get_order_history())
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind10c])].index)[0]
                                trade_table[c]['SL_price'][ind10c] = order['average_price'].iloc[index]
                                trade_table[c]['SL'][ind10c] = (trade_table[c]['SL_price'][ind10c] - trade_table[c]['Entry_price'][ind10c]) * trade_table[c]['qty'][ind10c]
                                trade_table[c]['SL_qty'][ind10c] = trade_table[c]['Profit'][ind10c] = 0
                                trade_table[c]['R.Profit'][ind10c] = trade_table[c]['SL'][ind10c]
                                flag['double_call'][c] = 2
                            else:
                                append_excel_table(c)
                        elif flag['double_call'][c] == 3:
                            ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'D20p']).index[0]
                            new = trade_table[c]['delta'][ind] + 0.15
                            expiry = trade_table[c]['symbol'][ind][:-7]
                            strike, tradingsymbol = delta_strike(expiry, new, trade_table[c]['days_left'][ind])
                            if strike == trade_table[c]['strike'][ind]:
                                continue
                            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind]),
                                int(trade_table[c]['qty'][ind]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            trade_table[c]['SL_id'][ind] = order_id1['order_id']
                            trade_table[c]['SL_status'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt'][ind] = 'Closed'
                            trade_table[c]['3pm_tgt_qty'][ind] = 'Closed'
                            trade_table[c]['Entry_status'][ind] = 'Closed'
                            order = pd.DataFrame(u[c].get_order_history())
                            try:
                                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind])].index)[0]
                                trade_table[c]['SL_price'][ind] = order['average_price'].iloc[index]
                            except Exception as e:
                                print('Error in getting order history in', c, e)
                                trade_table[c]['SL_price'][ind] = 0
                            trade_table[c]['SL'][ind] = (trade_table[c]['Entry_price'][ind] - trade_table[c]['SL_price'][ind]) * trade_table[c]['qty'][ind]
                            trade_table[c]['SL_qty'][ind] = trade_table[c]['Profit'][ind] = 0
                            trade_table[c]['R.Profit'][ind] = trade_table[c]['SL'][ind]
                            rank = trade_table[c]['rank'][ind]
                            Trade = 'SELL @'
                            strategy = trade_table[c]['strategy'][ind]
                            order_placed = 0
                            SL_D_price = 'Nil'
                            prem = 0
                            Target1 = 2
                            SL_price = 'Nil'
                            Entry_status = 'Ordered'
                            Tgt1_status = SL_status = 'NOT EXEC'
                            order_rej = 'NO'
                            last_tgt = last_qty = 'OPEN'
                            product = 'D'
                            qty = SL_qty = int(client['D20ironfly'].iloc[c] * 15)
                            days_left = trade_table[c]['days_left'][ind]
                            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                            Entry_bid = data['asks'][0]['price'] - 0.05
                            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                                qty,OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            order_id = order_id1['order_id']
                            append_excel_table(c)
            if client['sstrgle'].iloc[c] > 0 and time(9, 20) <= datetime.now().time() <= time(15, 20):
                if (flag['scall_delta'][c] + flag['sput_delta'][c]) > 0.18:
                    print('SSTNGLE delta very high', (flag['scall_delta'][c] + flag['sput_delta'][c]))
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'SS05f']).index[0]
                        print('shifting insurance put', c, ind)
                    except Exception as e:
                        print('Error in getting buy put', c, e)
                        continue
                    upgrade(c, ind)
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'SS20f']).index[0]
                        print('shifting sell put', c, ind, datetime.now())
                    except Exception as e:
                        print('Error in getting sell put', c, e)
                        continue
                    upgrade(c, ind)
                    order = pd.DataFrame(u[c].get_order_history())
                    try:
                        index = order[order['order_id'] == trade_table[c]['order_id'].iloc[-1]].index[0]
                    except Exception as e:
                        print('Error in getting order history in', c, e)
                        try:
                            sleep(3)
                            order = pd.DataFrame(u[c].get_order_history())
                            index = order[order['order_id'] == trade_table[c]['order_id'].iloc[-1]].index[0]
                        except Exception as e:
                            print('Check sstrgle Error in getting order history 2nd time in', c, e)
                            append_excel_table(c)
                            return
                    if order['status'].iloc[index] == 'rejected':
                        trade_table[c]['Entry_status'].iloc[-1] = 'rejected'
                        trade_table[c]['SL_status'].iloc[-1] = 'closed'
                        trade_table[c]['3pm_tgt'].iloc[-1] = 'closed'
                        trade_table[c]['3pm_tgt_qty'].iloc[-1] = 'closed'
                        ind05f = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['order_rej'] == 'NO']
                            [trade_table[c]['rank'] == 'SS05f']).index[0]
                        new = trade_table[c]['delta'][ind05f] - 0.05
                        expiry = trade_table[c]['symbol'][ind05f][:-7]
                        strike, tradingsymbol = delta_strike(expiry, new, trade_table[c]['days_left'][ind05f])
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            int(trade_table[c]['qty'][ind05f]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        rank = trade_table[c]['rank'][ind05f]
                        Trade = 'BUY @'
                        strategy = trade_table[c]['strategy'][ind05f]
                        order_placed = 0
                        SL_D_price = 'Nil'
                        prem = 0
                        Target1 = 2
                        SL_price = 'Nil'
                        Entry_status = 'Ordered'
                        Tgt1_status = SL_status = 'NOT EXEC'
                        order_rej = 'NO'
                        last_tgt = last_qty = 'OPEN'
                        product = 'D'
                        qty = SL_qty = trade_table[c]['qty'][ind05f]
                        days_left = trade_table[c]['days_left'][ind05f]
                        append_excel_table(c)
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind05f]),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind05f] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind05f] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind05f] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind05f] = 'Closed'
                        trade_table[c]['Entry_status'][ind05f] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind05f])].index)[0]
                        trade_table[c]['SL_price'][ind05f] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind05f] = (trade_table[c]['SL_price'][ind05f] - trade_table[c]['Entry_price'][ind05f]) * trade_table[c]['qty'][ind05f]
                        trade_table[c]['SL_qty'][ind05f] = trade_table[c]['Profit'][ind05f] = 0
                        trade_table[c]['R.Profit'][ind05f] = trade_table[c]['SL'][ind05f]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'].iloc[-2]),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        rank = trade_table[c]['rank'].iloc[-2]
                        Trade = 'SELL @'
                        strategy = trade_table[c]['strategy'].iloc[-2]
                        append_excel_table(c)
                elif (flag['scall_delta'][c] + flag['sput_delta'][c]) < -0.18:
                    print('SSTNGLE delta very low')
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'SS05b']).index[0]
                        print('shifting insurance call', c, ind)
                    except Exception as e:
                        print('Error in getting buy call', c, e)
                        continue
                    upgrade(c, ind)
                    try:
                        ind = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['Entry_status'] == 'Executed']
                            [trade_table[c]['rank'] == 'SS20b']).index[0]
                        print('shifting sell call', c, ind, datetime.now())
                    except Exception as e:
                        print('Error in getting sell call', c, e)
                        continue
                    upgrade(c, ind)
                    order = pd.DataFrame(u[c].get_order_history())
                    try:
                        index = order[order['order_id'] == trade_table[c]['order_id'].iloc[-1]].index[0]
                    except Exception as e:
                        print('Error in getting order history in', c, e)
                        try:
                            sleep(3)
                            order = pd.DataFrame(u[c].get_order_history())
                            index = order[order['order_id'] == trade_table[c]['order_id'].iloc[-1]].index[0]
                        except Exception as e:
                            print('Check sstrgle Error in getting order history 2nd time in', c, e)
                            append_excel_table(c)
                            return
                    if order['status'].iloc[index] == 'rejected':
                        trade_table[c]['Entry_status'].iloc[-1] = 'rejected'
                        trade_table[c]['SL_status'].iloc[-1] = 'closed'
                        trade_table[c]['3pm_tgt'].iloc[-1] = 'closed'
                        trade_table[c]['3pm_tgt_qty'].iloc[-1] = 'closed'
                        ind05b = (trade_table[c][trade_table[c]['3pm_tgt'] == 'OPEN']
                            [trade_table[c]['SL_status'] == 'NOT EXEC']
                            [trade_table[c]['order_rej'] == 'NO']
                            [trade_table[c]['rank'] == 'SS05b']).index[0]
                        new = trade_table[c]['delta'][ind05b] + 0.05
                        expiry = trade_table[c]['symbol'][ind05b][:-7]
                        strike, tradingsymbol = delta_strike(expiry, new, trade_table[c]['days_left'][ind05b])
                        order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                            int(trade_table[c]['qty'][ind05b]),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        order_id = order_id1['order_id']
                        rank = trade_table[c]['rank'][ind05b]
                        Trade = 'BUY @'
                        strategy = trade_table[c]['strategy'][ind05b]
                        order_placed = 0
                        SL_D_price = 'Nil'
                        prem = 0
                        Target1 = 2
                        SL_price = 'Nil'
                        Entry_status = 'Ordered'
                        Tgt1_status = SL_status = 'NOT EXEC'
                        order_rej = 'NO'
                        last_tgt = last_qty = 'OPEN'
                        product = 'D'
                        qty = SL_qty = trade_table[c]['qty'][ind05b]
                        days_left = trade_table[c]['days_left'][ind05b]
                        append_excel_table(c)
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][ind05b]),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        trade_table[c]['SL_id'][ind05b] = order_id1['order_id']
                        trade_table[c]['SL_status'][ind05b] = 'Closed'
                        trade_table[c]['3pm_tgt'][ind05b] = 'Closed'
                        trade_table[c]['3pm_tgt_qty'][ind05b] = 'Closed'
                        trade_table[c]['Entry_status'][ind05b] = 'Closed'
                        order = pd.DataFrame(u[c].get_order_history())
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][ind05b])].index)[0]
                        trade_table[c]['SL_price'][ind05b] = order['average_price'].iloc[index]
                        trade_table[c]['SL'][ind05b] = (trade_table[c]['SL_price'][ind05b] - trade_table[c]['Entry_price'][ind05b]) * trade_table[c]['qty'][ind05b]
                        trade_table[c]['SL_qty'][ind05b] = trade_table[c]['Profit'][ind05b] = 0
                        trade_table[c]['R.Profit'][ind05b] = trade_table[c]['SL'][ind05b]
                        order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'].iloc[-2]),
                            int(qty),OrderType.Market,ProductType.Delivery,
                            0.0,None,0,DurationType.DAY,None,None,None)
                        rank = trade_table[c]['rank'].iloc[-2]
                        Trade = 'SELL @'
                        strategy = trade_table[c]['strategy'].iloc[-2]
                        append_excel_table(c)

def short_straddle_entry():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej, fromtime1
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid, week1b, week0b
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, straddle_table_bank, fromtime0
    for c in range(len(client)):
        if client['straddle'].iloc[c] >= 1 and client['banknifty'].iloc[c] == 1:
            last_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
            last_price_0 = round(last_price/100) * 100
            flag['strad_strike'][c] = last_price_0
            Trade = 'SELL @'
            strategy = 'STRAD'
            order_placed = 0
            SL_D_price = 'Nil'
            prem = 0
            if wednesday == 7 or (wednesday == 1 and shortweek == 1):
                days_left = fromtime0
                tradingsymbol = week0b + str(last_price_0) + 'CE'
            else:
                days_left = fromtime1
                tradingsymbol = week1b + str(last_price_0) + 'CE'
            Target1 = 'Nil'
            Entry_status = 'Ordered'
            Tgt1_status = SL_status = 'NOT EXEC'
            order_rej = 'NO'
            last_tgt = last_qty = 'OPEN'
            product = 'D'
            qty = SL_qty = int(client['straddle'].iloc[c] * 15)
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            SL_price = round2(Entry_bid * 1.5)
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Limit,ProductType.Delivery,
                Entry_bid,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            tradingsymbol = tradingsymbol[:-2] + 'PE'
            data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
            Entry_bid = data['asks'][0]['price'] - 0.05
            SL_price = round2(Entry_bid * 1.5)
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                qty,OrderType.Limit,ProductType.Delivery,
                Entry_bid,None,0,DurationType.DAY,None,None,None)
            order_id = order_id1['order_id']
            append_excel_table(c)
            display_trade()

def close_and_fresh(c):
    if trade_table[c]['strategy'][0] == 'D20ironfly' or trade_table[c]['strategy'][2] == 'D20ironfly':
        print('Closing all open positions for', c)
        for i in range(len(trade_table[c])):
            if (trade_table[c]['3pm_tgt'][i] == 'OPEN' and trade_table[c]['Entry_status'][i] == 'Executed' and time(9, 20) <= datetime.now().time() and trade_table[c]['strategy'][i] != 'RSI' and trade_table[c]['strategy'][i] != 'EMA') or (trade_table[c]['order_rej'][i] == 'NO' and trade_table[c]['Entry_status'][i] == 'Ordered'):
                # if datetime.now().date() == datetime.strptime(trade_table[c]['days_left'][i].split()[0], '%d-%m-%Y').date():
                if trade_table[c]['trade_type'][i] == 'SELL @' and trade_table[c]['strategy'][i] != 'FUT':
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][i]),
                        int(trade_table[c]['qty'][i]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    trade_table[c]['SL_id'][i] = int(order_id)
                    trade_table[c]['SL_status'][i] = 'Closed'
                    trade_table[c]['3pm_tgt'][i] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][i] = 'Closed'
                    trade_table[c]['Entry_status'][i] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    try:
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                        trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
                    except Exception as e:
                        print(e)
                        trade_table[c]['SL_price'][i] = 0
                    trade_table[c]['SL'][i] = (trade_table[c]['Entry_price'][i] - trade_table[c]['SL_price'][i]) * trade_table[c]['qty'][i]
                    trade_table[c]['SL_qty'][i] = trade_table[c]['Profit'][i] = 0
                    trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]
        for i in range(len(trade_table[c])):
            if trade_table[c]['3pm_tgt'][i] == 'OPEN' and time(9, 20) <= datetime.now().time() and trade_table[c]['strategy'][i] != 'RSI' and trade_table[c]['strategy'][i] != 'EMA':
                if trade_table[c]['trade_type'][i] == 'BUY @' and trade_table[c]['strategy'][i] != 'FUT':
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][i]),
                        int(trade_table[c]['qty'][i]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    trade_table[c]['SL_id'][i] = int(order_id)
                    trade_table[c]['SL_status'][i] = 'Closed'
                    trade_table[c]['3pm_tgt'][i] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][i] = 'Closed'
                    trade_table[c]['Entry_status'][i] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    try:
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                        trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
                    except Exception as e:
                        print(e)
                        trade_table[c]['SL_price'][i] = 0
                    trade_table[c]['SL'][i] = (trade_table[c]['SL_price'][i] - trade_table[c]['Entry_price'][i]) * trade_table[c]['qty'][i]
                    trade_table[c]['SL_qty'][i] = trade_table[c]['Profit'][i] = 0
                    trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]
        flag['double_put'][c] = 0
        flag['double_call'][c] = 0

def close_intra_trade():
    for c in range(len(client)):
        if client['intraday'].iloc[c] == 1:
            closing(c)

def closing(c):
    for i in range(len(trade_table[c])):
        try:
            if trade_table[c]['trade_type'][i] == 'SELL @' and trade_table[c]['strategy'][i] != 'FUT':
                if trade_table[c]['3pm_tgt'][i] == 'OPEN' and trade_table[c]['Entry_status'][i] == 'Executed' and time(9, 20) <= datetime.now().time() and (trade_table[c]['strategy'][i] != 'EMA' or (trade_table[c]['strategy'][i] == 'EMA' and client['ema_exit'].iloc[c] == 1 and trade_table[c]['3pm_tgt'][i] == 'OPEN')):
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][i]),
                        int(trade_table[c]['qty'][i]),OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    trade_table[c]['SL_id'][i] = int(order_id)
                    trade_table[c]['SL_status'][i] = 'Closed'
                    trade_table[c]['3pm_tgt'][i] = 'Closed'
                    trade_table[c]['3pm_tgt_qty'][i] = 'Closed'
                    trade_table[c]['Entry_status'][i] = 'Closed'
                    order = pd.DataFrame(u[c].get_order_history())
                    try:
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                        trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
                    except Exception as e:
                        print(e, c, i)
                        trade_table[c]['SL_price'][i] = 0
                    trade_table[c]['SL'][i] = (trade_table[c]['Entry_price'][i] - trade_table[c]['SL_price'][i]) * trade_table[c]['qty'][i]
                    trade_table[c]['SL_qty'][i] = trade_table[c]['Profit'][i] = 0
                    trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]
        except Exception as e:
            print(e, c, i)            
    for i in range(len(trade_table[c])):
        if trade_table[c]['3pm_tgt'][i] == 'OPEN' and trade_table[c]['Entry_status'][i] == 'Executed' and time(9, 20) <= datetime.now().time() and trade_table[c]['strategy'][i] != 'RSI' and (trade_table[c]['strategy'][i] != 'EMA' or (trade_table[c]['strategy'][i] == 'EMA' and client['ema_exit'].iloc[c] == 1 and trade_table[c]['3pm_tgt'][i] == 'OPEN')):
            if trade_table[c]['trade_type'][i] == 'BUY @' and trade_table[c]['strategy'][i] != 'FUT':
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][i]),
                    int(trade_table[c]['qty'][i]),OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                trade_table[c]['SL_id'][i] = int(order_id)
                trade_table[c]['SL_status'][i] = 'Closed'
                trade_table[c]['3pm_tgt'][i] = 'Closed'
                trade_table[c]['3pm_tgt_qty'][i] = 'Closed'
                trade_table[c]['Entry_status'][i] = 'Closed'
                order = pd.DataFrame(u[c].get_order_history())
                try:
                    index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                    trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
                except Exception as e:
                    print(e, c, i)
                    trade_table[c]['SL_price'][i] = 0
                trade_table[c]['SL'][i] = (trade_table[c]['SL_price'][i] - trade_table[c]['Entry_price'][i]) * trade_table[c]['qty'][i]
                trade_table[c]['SL_qty'][i] = trade_table[c]['Profit'][i] = 0
                trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]

def trade_update():
    global trade_table, exchange, tradingsymbol, data, order1, flag, order
    y = 0
    z = []
    try:
        last_price_bank = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
    except Exception as e:
        print(e)
        try:
            data_bank = s.get_ohlc(
                s.get_instrument_by_symbol(
                    'NSE_INDEX', 'NIFTY_BANK'
                    ),
                OHLCInterval.Minute_1, datetime.strptime(
                    '{}'.format(to_date), '%d/%m/%Y'
                    ).date(), datetime.strptime(
                        '{}'.format(to_date), '%d/%m/%Y'
                        ).date())
            data_bank = pd.DataFrame(data_bank)
            data_bank = data_bank.astype(
                {'open': float, 'high': float, 'low': float, 'close': float, 'volume': float})
            last_price_bank = data_bank['close'].iloc[-1]
        except Exception as e:
            print(e)
            print('W a r n i n g !!!   L o s t  C o n n e c t i o n')
            return
    # last_price_nifty = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_50'), LiveFeedType.LTP)['ltp']
    for c in range(len(client)):
        z += trade_table[c]['symbol'].to_list()
    z = set(z)
    for y in z:
        tradingsymbol = y
        for c in range(len(client)):
            ind = list(trade_table[c][trade_table[c]['symbol'] == tradingsymbol].index)
            try:
                data=u[c].get_live_feed(u[c].get_instrument_by_symbol(exchange,tradingsymbol), LiveFeedType.Full)
            except Exception as e:
                sleep(1)
                print('live feed error in trade update for:',c, y, e)
                continue
            for i in ind:
                print(tradingsymbol, c, data['ltp'])
                trade_table[c]['LTP'][i] = data['ltp']
                if trade_table[c]['Entry_status'][i] == 'Ordered' and trade_table[c]['order_rej'][i] == 'NO':
                    order = pd.DataFrame(u[c].get_order_history())
                    try:
                        index = order[order['order_id'] == int(trade_table[c]['order_id'][i])].index[0]
                    except Exception as e:
                            print(e)
                            continue
                    if order['status'].iloc[index] == 'complete':
                        trade_table[c]['Entry_price'][i] = order['average_price'].iloc[index]
                        add_SL(c, i, order, index)
                    elif order['status'].iloc[index] == 'open':
                        trade_table[c]['order_placed'][i] += 1
                        try:
                            print('Entry Price modified for', trade_table[c]['symbol'][i], c)
                            if trade_table[c]['trade_type'][i] == 'SELL @':
                                u[c].modify_order(int(trade_table[c]['order_id'][i]), price=(data['asks'][0]['price'] - 0.05))
                            else:
                                u[c].modify_order(int(trade_table[c]['order_id'][i]), price=(data['bids'][0]['price'] + 0.05))
                        except Exception as e:
                            print(e)
                    elif order['status'].iloc[index] == 'rejected':
                        trade_table[c]['order_rej'][i] = 'YES'
                        print('Order rejected for', trade_table[c]['strategy'][i])
                if trade_table[c]['order_placed'][i] == 'YES' and trade_table[c]['order_rej'][i] == 'NO' and time(9, 16) <= datetime.now().time():
                    if trade_table[c]['strategy'][i] != '3IRONFLY' and trade_table[c]['strategy'][i] != 'D20ironfly':
                        update_target_SL(c, i)
                    if "BANK" in trade_table[c]['symbol'][i]:
                        underlying = last_price_bank
                    if trade_table[c]['strategy'][i] != 'FUT':
                        totime = datetime.now()
                        t1 = trade_table[c]['days_left'][i] - totime
                        a = t1/timedelta(days=1)
                        tg = float(a/365)
                        trade_table[c]['iv'][i] = iv(trade_table[c]['symbol'][i], trade_table[c]['strike'][i], trade_table[c]['LTP'][i], underlying, tg)
                        d1, d2 = d(trade_table[c]['iv'][i], underlying, trade_table[c]['strike'][i], 0.1, tg)
                        trade_table[c]['delta'][i] = delta(d1, trade_table[c]['symbol'][i])
                    if (trade_table[c]['strategy'][i] == '3IRONFLY' or trade_table[c]['strategy'][i] == 'D20ironfly') and (trade_table[c]['3pm_tgt'][i] == 'OPEN'):
                        delta_shift(c, i)
                if (trade_table[c]['trade_type'][i] == 'BUY ABOVE' or trade_table[c]['trade_type'][i] == 'BUY @'):
                    trade_table[c]['Profit'][i] = (trade_table[c]['LTP'][i] - trade_table[c]['Entry_price'][i]) * trade_table[c]['SL_qty'][i]
                elif (trade_table[c]['trade_type'][i] == 'SELL BELOW' or trade_table[c]['trade_type'][i] == 'SELL @'):
                    if trade_table[c]['Entry_status'][i] == 'Executed' or trade_table[c]['Entry_status'][i] == 'Shifted':
                        trade_table[c]['Profit'][i] = (trade_table[c]['Entry_price'][i] - trade_table[c]['LTP'][i]) * trade_table[c]['SL_qty'][i]
    print('update done')

def update():
    if time(9, 16) <= datetime.now().time() < time(15, 32):
        print('update start', datetime.now().time())
        if time(12, 47) <= datetime.now().time() and (wednesday == 7 or (wednesday == 1 and shortweek == 1)):
            expiry_trade()
            if time(15, 00) <= datetime.now().time():
                expiry_3pm()
        trade_update()
        double()
        # ema_entry()
        # supertrend()
        display_trade()
        if time(9, 16) <= datetime.now().time():
            # display_trade_book()
            display_trade_postion()
            display_order()
            balance_status()
        sheet.range("D1").value = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
        int(datetime.now().strftime("%S"))
        sleep(abs(35 - int(datetime.now().strftime("%S"))))
    else:
        print('timeout', datetime.now().time())
        sleep(abs(35 - int(datetime.now().strftime("%S"))))

def position_holding_SL():
    for c in range(len(client)):
        for y in range(len(trade_table[c])):
            if trade_table[c]['SL_id'].isna()[y] and trade_table[c]['trade_type'][y] == 'SELL @' and trade_table[c]['SL_status'][y] == 'NOT EXEC' and trade_table[c]['Entry_status'][y] == 'Executed':
                print('SL added in', c, trade_table[c]['symbol'][y])
                order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,trade_table[c]['symbol'][y]),
                    int(trade_table[c]['qty'][y]),OrderType.StopLossMarket,ProductType.Delivery,
                    0.0,float(trade_table[c]['SL_D_price'][y]),0,DurationType.DAY,None,None,None)
                trade_table[c]['SL_id'][y] = order_id['order_id']

def expiry_3pm():
    global trade_table, flag, shortweek, Trade, strategy, SL_price, Target1, qty, SL_qty, order_rej, CE_symbol_low, PE_symbol_low
    global order_id, tradingsymbol, rank, strike, days_left, order_placed, SL_D_price, Entry_bid, week0b, strike_high, strike_low
    global prem, Entry_status, Tgt1_status, SL_status, product, last_tgt, last_qty, fromtime0, CE_symbol_high, PE_symbol_high
    if time(15, 0) < datetime.now().time() < time(15, 10):
        print('Expiry trade start')
        last_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_INDEX', 'NIFTY_BANK'), LiveFeedType.LTP)['ltp']
        last_price_0 = int(round(last_price/100) * 100 + 100)
        symbol_CE = week0b + str(last_price_0) + 'CE'
        CE_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_FO', symbol_CE), LiveFeedType.LTP)['ltp']
        symbol_PE = week0b + str(last_price_0) + 'PE'
        PE_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_FO', symbol_PE), LiveFeedType.LTP)['ltp']
        Trade = 'BUY @'
        strategy = '3pm'
        order_placed = 0
        SL_D_price = 'Nil'
        prem = 0
        rank = 'E07c'
        Target1 = 'Nil'
        SL_price = 'Nil'
        Entry_status = 'Ordered'
        Tgt1_status = SL_status = 'NOT EXEC'
        order_rej = 'NO'
        last_tgt = last_qty = 'OPEN'
        product = 'D'
        if PE_price > 3.5 * CE_price and CE_price > 10:
            for c in range(len(client)):
                flag['closing_profit'][c] = 0
                if client['expiry3pm'].iloc[c] > 0 and flag['expiry_bank_last_leg_ce'][c] == 0:
                    strike = last_price_0 + 200
                    tradingsymbol = week0b + str(strike) + 'CE'
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['bids'][0]['price'] + 0.05
                    rank = 'E07c'
                    Trade = 'BUY @'
                    qty = SL_qty = int(client['expiry3pm'].iloc[c] * 15)
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    Trade = 'SELL @'
                    rank = 'E40c'
                    strike -= 200
                    strike_high = strike
                    CE_symbol_high = tradingsymbol = week0b + str(strike) + 'CE'
                    PE_symbol_high = week0b + str(strike) + 'PE'
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['asks'][0]['price'] - 0.05
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    flag['expiry_bank_last_leg_ce'][c] = 1
        else:
            print('Condition not satisfied for downside', CE_price, PE_price)
        last_price_0 -= 200
        symbol_CE = week0b + str(last_price_0) + 'CE'
        CE_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_FO', symbol_CE), LiveFeedType.LTP)['ltp']
        symbol_PE = week0b + str(last_price_0) + 'PE'
        PE_price = s.get_live_feed(s.get_instrument_by_symbol('NSE_FO', symbol_PE), LiveFeedType.LTP)['ltp']
        if CE_price > 3.5 * PE_price and PE_price > 10:
            for c in range(len(client)):
                flag['closing_profit'][c] = 0
                if client['expiry3pm'].iloc[c] > 0 and flag['expiry_bank_last_leg_pe'][c] == 0:
                    strike = last_price_0 - 200
                    tradingsymbol = week0b + str(strike) + 'PE'
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['bids'][0]['price'] + 0.05
                    rank = 'E07p'
                    Trade = 'BUY @'
                    qty = SL_qty = int(client['expiry3pm'].iloc[c] * 15)
                    order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    Trade = 'SELL @'
                    rank = 'E40p'
                    strike += 200
                    strike_low = strike
                    PE_symbol_low = tradingsymbol = week0b + str(strike) + 'PE'
                    CE_symbol_low = week0b + str(strike) + 'CE'
                    data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                    Entry_bid = data['asks'][0]['price'] - 0.05
                    order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                        qty,OrderType.Market,ProductType.Delivery,
                        0.0,None,0,DurationType.DAY,None,None,None)
                    order_id = order_id1['order_id']
                    append_excel_table(c)
                    flag['expiry_bank_last_leg_pe'][c] = 1
        else:
            print('Condition not satisfied for upside', CE_price, PE_price)
    for c in range(len(client)):
        if flag['expiry_bank_last_leg_pe'][c] == 1:
            CE_price_low = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', CE_symbol_low), LiveFeedType.LTP)['ltp']
            PE_price_low = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', PE_symbol_low), LiveFeedType.LTP)['ltp']
            if CE_price_low <= PE_price_low:
                strike = strike_low + 200
                tradingsymbol = week0b + str(strike) + 'CE'
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['bids'][0]['price'] + 0.05
                rank = 'E07c'
                Trade = 'BUY @'
                qty = SL_qty = int(client['expiry3pm'].iloc[c] * 15)
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                Trade = 'SELL @'
                rank = 'E40c'
                strike -= 200
                CE_symbol = tradingsymbol = week0b + str(strike) + 'CE'
                PE_symbol = week0b + str(strike) + 'PE'
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                flag['expiry_bank_last_leg_pe'][c] = 2
        if flag['expiry_bank_last_leg_ce'][c] == 1:
            CE_price_high = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', CE_symbol_high), LiveFeedType.LTP)['ltp']
            PE_price_high = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', PE_symbol_high), LiveFeedType.LTP)['ltp']
            if PE_price_high <= CE_price_high:
                strike = strike_high - 200
                tradingsymbol = week0b + str(strike) + 'PE'
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['bids'][0]['price'] + 0.05
                rank = 'E07p'
                Trade = 'BUY @'
                qty = SL_qty = int(client['expiry3pm'].iloc[c] * 15)
                order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                Trade = 'SELL @'
                rank = 'E40p'
                strike += 200
                PE_symbol = tradingsymbol = week0b + str(strike) + 'PE'
                CE_symbol = week0b + str(strike) + 'CE'
                data = u[c].get_live_feed(u[c].get_instrument_by_symbol('NSE_FO', tradingsymbol), LiveFeedType.Full)
                Entry_bid = data['asks'][0]['price'] - 0.05
                order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange,tradingsymbol),
                    qty,OrderType.Market,ProductType.Delivery,
                    0.0,None,0,DurationType.DAY,None,None,None)
                order_id = order_id1['order_id']
                append_excel_table(c)
                flag['expiry_bank_last_leg_ce'][c] = 2

def new_position():
    for c in range(len(client)):
        if len(trade_table[c]) <= 10:
            if client['entry'].iloc[c] == 1 and client['D20ironfly'].iloc[c] >= 1:
                fresh_setup_delta_ironfly(c)

def take_profit_max():
    for c in range(len(client)):
        if flag['profit'][c] > client['take_profit'].iloc[c] and client['take_profit'].iloc[c] != 0:
            if flag['close'][c] == 0:
                closing(c)
                flag['close'][c] = 1

def close_position():
    global order
    print('Closing positions')
    for c in range(len(client)):
        if client['ema_exit'].iloc[c] == 1 or (client['ema_exit'].iloc[c] == 0 and (wednesday == 7 or (wednesday == 1 and shortweek == 1))):
            position_book[c] = pd.DataFrame(u[c].get_positions())
            for i in range (len(position_book[c])):
                if position_book[c]['unrealized_profit'][i] != '' and position_book[c]['trading_symbol'][i][-3:] != 'FUT':
                    try:
                        if position_book[c]['net_quantity'][i] < 0 and (week1b == position_book[c]['symbol'][i][:-7] or week0b == position_book[c]['symbol'][i][:-7]):
                            order_id=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(position_book[c]['exchange'][i],position_book[c]['symbol'][i]),
                                abs(int(position_book[c]['net_quantity'][i])),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            print('manual closing position in ', c , position_book[c]['symbol'][i], 'for qty ', position_book[c]['net_quantity'][i])
                    except Exception as e:
                        print(e, c, i)
            for i in range (len(position_book[c])):
                if position_book[c]['unrealized_profit'][i] != '' and position_book[c]['trading_symbol'][i][-3:] != 'FUT':
                    try:
                        if position_book[c]['net_quantity'][i] > 0 and (week1b == position_book[c]['symbol'][i][:-7] or week0b == position_book[c]['symbol'][i][:-7]):
                            order_id=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(position_book[c]['exchange'][i],position_book[c]['symbol'][i]),
                                int(position_book[c]['net_quantity'][i]),OrderType.Market,ProductType.Delivery,
                                0.0,None,0,DurationType.DAY,None,None,None)
                            print('manual closing position in ', c , position_book[c]['symbol'][i], 'for qty ', position_book[c]['net_quantity'][i])
                    except Exception as e:
                        print(e, c, i)

def close_stbt():
    print('Closing STBT')
    for c in range(len(client)):
        if client['stbt'].iloc[c] >= 1:
            close_strategy(c,'STBT')

def close_sstngle():
    print('Closing SSTNGLE')
    for c in range(len(client)):
        if client['sstrgle'].iloc[c] >= 1:
            close_strategy(c,'SSTNGLE')

def close_strad():
    print('Closing STRAD')
    for c in range(len(client)):
        if client['stbt'].iloc[c] >= 1:
            close_strategy(c,'STRAD')

def close_strategy(c, d):
    for i in range(len(trade_table[c])):
        if trade_table[c]['trade_type'][i] == 'SELL @' and trade_table[c]['strategy'][i] == d:
            print(trade_table[c]['symbol'][i])
            order_id1=u[c].place_order(TransactionType.Buy,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][i]),
                int(trade_table[c]['qty'][i]),OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            print('schedule close position for ', c , trade_table[c]['symbol'][i])
            order_id = order_id1['order_id']
            trade_table[c]['SL_id'][i] = int(order_id)
            trade_table[c]['SL_status'][i] = 'Closed'
            trade_table[c]['3pm_tgt'][i] = 'Closed'
            trade_table[c]['3pm_tgt_qty'][i] = 'Closed'
            trade_table[c]['Entry_status'][i] = 'Closed'
            order = pd.DataFrame(u[c].get_order_history())
            try:
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
            except Exception as e:
                print(e, c, i)
                trade_table[c]['SL_price'][i] = 0
            trade_table[c]['SL'][i] = (trade_table[c]['Entry_price'][i] - trade_table[c]['SL_price'][i]) * trade_table[c]['qty'][i]
            trade_table[c]['SL_qty'][i] = trade_table[c]['Profit'][i] = 0
            trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]
    for i in range(len(trade_table[c])):
        if trade_table[c]['trade_type'][i] == 'BUY @' and trade_table[c]['strategy'][i] == d:
            order_id1=u[c].place_order(TransactionType.Sell,u[c].get_instrument_by_symbol(exchange, trade_table[c]['symbol'][i]),
                int(trade_table[c]['qty'][i]),OrderType.Market,ProductType.Delivery,
                0.0,None,0,DurationType.DAY,None,None,None)
            print('schedule close position for ', c , trade_table[c]['symbol'][i])
            order_id = order_id1['order_id']
            trade_table[c]['SL_id'][i] = int(order_id)
            trade_table[c]['SL_status'][i] = 'Closed'
            trade_table[c]['3pm_tgt'][i] = 'Closed'
            trade_table[c]['3pm_tgt_qty'][i] = 'Closed'
            trade_table[c]['Entry_status'][i] = 'Closed'
            order = pd.DataFrame(u[c].get_order_history())
            try:
                index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
            except Exception as e:
                print(e, c, i)
                trade_table[c]['SL_price'][i] = 0
            trade_table[c]['SL'][i] = (trade_table[c]['SL_price'][i] - trade_table[c]['Entry_price'][i]) * trade_table[c]['qty'][i]
            trade_table[c]['SL_qty'][i] = trade_table[c]['Profit'][i] = 0
            trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]

def iv(idendtifier, sp, ltp, underlying, t):
    try:
        flag = 'c'
        if "CE" in idendtifier:
            flag = 'c'
        if "PE" in idendtifier:
            flag = 'p'
        iv = implied_volatility(ltp, underlying, sp, t, 0.1, flag)
        return round(iv*100, 2)
    except BelowIntrinsicException:
        return 0
    except Exception as error:
        return -1

def new_expiry_entry():
    for c in range(len(client)):
        if client['expiry'].iloc[c] >= 1 and client['week0'].iloc[c] == 1 and (wednesday == 7 or (wednesday == 1 and shortweek == 1)):
            if client['D20ironfly'].iloc[c] >= 1:
                flag['call_delta'][c] = flag['put_delta'][c] = 0.01
                fresh_setup_delta_ironfly(c)

def import_dataframe(book: str, sheet: str):
    sheet = xw.Book(book).sheets[sheet]
    DataFrames = []
    for index, value in enumerate(sheet.range('A1:A1000').value):
        if value == 'time':
            df = sheet.range(
                    'A' + str(index + 1)).options(pd.DataFrame, expand='table'
                ).value
            df.insert(0, 'time', df.index)
            df.index = range(len(df))
            DataFrames.append(df)
            print(df)
    return DataFrames

def update_missing_details():
    for c in range(len(client)):
        order = pd.DataFrame(u[c].get_order_history())
        for i in range(len(trade_table[c])):
            try:
                if trade_table[c]['3pm_tgt'][i] != 'OPEN' and trade_table[c]['Entry_status'][i] != 'Executed':
                    print('Updating closing data for', c, i)
                    if trade_table[c]['SL_price'][i] == 0:
                        index = list(order[order['order_id'] == int(trade_table[c]['SL_id'][i])].index)[0]
                        trade_table[c]['SL_price'][i] = order['average_price'].iloc[index]
                        if trade_table[c]['trade_type'][i] == 'SELL @':
                            trade_table[c]['SL'][i] = (trade_table[c]['Entry_price'][i] - trade_table[c]['SL_price'][i]) * trade_table[c]['qty'][i]
                            trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]
                        elif trade_table[c]['trade_type'][i] == 'BUY @':
                            trade_table[c]['SL'][i] = (trade_table[c]['SL_price'][i] - trade_table[c]['Entry_price'][i]) * trade_table[c]['qty'][i]
                            trade_table[c]['R.Profit'][i] = trade_table[c]['SL'][i]
                    elif trade_table[c]['Tgt1_price'][i] == 0:
                        index = list(order[order['order_id'] == int(trade_table[c]['order_id_Sft'][i])].index)[0]
                        trade_table[c]['Tgt1_price'][i] = order['average_price'].iloc[index]
                        if trade_table[c]['trade_type'][i] == 'SELL @':
                            trade_table[c]['Tgt1'][i] = (trade_table[c]['Entry_price'][i] - trade_table[c]['Tgt1_price'][i]) * trade_table[c]['qty'][i]
                            trade_table[c]['R.Profit'][i] = trade_table[c]['Tgt1'][i]
                        elif trade_table[c]['trade_type'][i] == 'BUY @':
                            trade_table[c]['Tgt1'][i] = (trade_table[c]['Tgt1_price'][i] - trade_table[c]['Entry_price'][i]) * trade_table[c]['qty'][i]
                            trade_table[c]['R.Profit'][i] = trade_table[c]['Tgt1'][i]
            except Exception as e:
                print('No closing data available for', c, i, e)

def flag_restore():
    for c in range(len(client)):
        flag['1day'][c] = flag1['1day'][c]
        flag['60min'][c] = flag1['60min'][c]
        flag['15min'][c] = flag1['15min'][c]
        flag['5min'][c] = flag1['5min'][c]

# sched = BlockingScheduler()
# sched.add_job(rsi_update, 'interval', minutes=5, start_date=start, end_date=end, jitter=55)
# sched.add_job(update, 'interval', minutes=1, start_date=start, end_date=end, jitter=55)
# if thursday == 7:
#     start_ironfly = datetime(YYYY, MM, DD, 15, 20)
#     sched.add_job(fresh_setup_delta_ironfly, 'date', run_date=start_ironfly, args=None)
# sched.start()

question = input('Do you want to start fresh or continue from where stopped?(F/C): ')

if question.lower() == 'c':
    question1 = input('Any short week? n for No, 1 for this week: ')
    if question1.lower() == 'n':
        shortweek = 0
    elif question1.lower() == '1':
        shortweek = 1
    elif question1.lower() == '2':
        shortweek = 2
    question2 = input('Automatic or manual?(A/M): ')
    if question2.lower() == 'a':
        trade_table = import_dataframe('Optionpair.xlsx', 'Trade')
    else:
        for q in range(len(client)):
            row = input(f'Row number of header of {q}:')
            trade_table[q] = pd.read_excel ('Optionpair.xlsx', sheet_name='Trade', header=int(row)-1)
            length = input(f'Number of lines in {q}:')
            trade_table[q] = trade_table[q][:int(length)]
            print(trade_table[q])
    if time(9, 15) < datetime.now().time():
        flag = pd.read_excel ('Optionpair.xlsx', sheet_name='flag', header=1)
    else:
        flag1 = pd.read_excel ('Optionpair.xlsx', sheet_name='flag', header=1)
        for p in range(len(client)):
            flag['max_profit'][p] = 0
            print(flag['max_profit'][p])
            flag['max_loss'][p] = 0
            print(flag['max_loss'][p])
    display_trade_postion()
    if time(6, 16) < datetime.now().time() < time(16, 35):
        display_order()
        weeks()
        display_trade_postion()
        display_trade()
        for p in range(len(client)):
            print(flag['max_profit'][p])
            print(flag['max_loss'][p])
        # closing(1)
        # fresh_setup_delta_ironfly(1)
        # schedule.every().day.at("09:25:01").do(close_position)
        schedule.every(25).seconds.do(update)
        schedule.every().day.at("09:14:55").do(flag_restore)
        schedule.every().day.at("09:33:02").do(close_stbt)
        schedule.every().day.at("09:17:02").do(short_straddle_entry)
        schedule.every().day.at("09:17:10").do(bankfuture_5)
        schedule.every().day.at("09:17:11").do(bankfuture_15)
        schedule.every().day.at("09:17:12").do(bankfuture_60)
        schedule.every().day.at("09:17:13").do(bankfuture_1D)
        schedule.every().day.at("09:34:02").do(new_position)
        schedule.every().day.at("09:17:23").do(single_strangle_entry)
        schedule.every().day.at("09:20:10").do(rsi_update)
        schedule.every().day.at("09:25:10").do(rsi_update)
        schedule.every().day.at("09:30:10").do(rsi_update)
        schedule.every().day.at("09:30:11").do(bankfuture_15)
        schedule.every().day.at("09:35:10").do(rsi_update)
        schedule.every().day.at("09:40:10").do(rsi_update)
        schedule.every().day.at("09:45:10").do(rsi_update)
        schedule.every().day.at("09:45:11").do(bankfuture_15)
        schedule.every().day.at("09:50:10").do(rsi_update)
        schedule.every().day.at("09:55:10").do(rsi_update)
        schedule.every().day.at("10:00:10").do(rsi_update)
        schedule.every().day.at("10:00:11").do(bankfuture_15)
        schedule.every().day.at("10:05:10").do(rsi_update)
        schedule.every().day.at("10:10:10").do(rsi_update)
        schedule.every().day.at("10:15:10").do(rsi_update)
        schedule.every().day.at("10:15:11").do(bankfuture_15)
        schedule.every().day.at("10:15:12").do(bankfuture_60)
        schedule.every().day.at("10:20:10").do(rsi_update)
        schedule.every().day.at("10:25:10").do(rsi_update)
        schedule.every().day.at("10:30:10").do(rsi_update)
        schedule.every().day.at("10:30:11").do(bankfuture_15)
        schedule.every().day.at("10:35:10").do(rsi_update)
        schedule.every().day.at("10:40:10").do(rsi_update)
        schedule.every().day.at("10:45:10").do(rsi_update)
        schedule.every().day.at("10:45:11").do(bankfuture_15)
        schedule.every().day.at("10:50:10").do(rsi_update)
        schedule.every().day.at("10:55:10").do(rsi_update)
        schedule.every().day.at("11:00:10").do(rsi_update)
        schedule.every().day.at("11:00:11").do(bankfuture_15)
        schedule.every().day.at("11:05:10").do(rsi_update)
        schedule.every().day.at("11:10:10").do(rsi_update)
        schedule.every().day.at("11:15:10").do(rsi_update)
        schedule.every().day.at("11:15:11").do(bankfuture_15)
        schedule.every().day.at("11:15:12").do(bankfuture_60)
        schedule.every().day.at("11:20:10").do(rsi_update)
        schedule.every().day.at("11:25:10").do(rsi_update)
        schedule.every().day.at("11:30:10").do(rsi_update)
        schedule.every().day.at("11:30:11").do(bankfuture_15)
        schedule.every().day.at("11:35:10").do(rsi_update)
        schedule.every().day.at("11:40:10").do(rsi_update)
        schedule.every().day.at("11:45:10").do(rsi_update)
        schedule.every().day.at("11:45:11").do(bankfuture_15)
        schedule.every().day.at("11:50:10").do(rsi_update)
        schedule.every().day.at("11:55:10").do(rsi_update)
        schedule.every().day.at("12:00:10").do(rsi_update)
        schedule.every().day.at("12:00:11").do(bankfuture_15)
        schedule.every().day.at("12:05:10").do(rsi_update)
        schedule.every().day.at("12:10:10").do(rsi_update)
        schedule.every().day.at("12:15:10").do(rsi_update)
        schedule.every().day.at("12:15:11").do(bankfuture_15)
        schedule.every().day.at("12:15:12").do(bankfuture_60)
        schedule.every().day.at("12:20:10").do(rsi_update)
        schedule.every().day.at("12:25:10").do(rsi_update)
        schedule.every().day.at("12:30:10").do(rsi_update)
        schedule.every().day.at("12:30:11").do(bankfuture_15)
        schedule.every().day.at("12:35:10").do(rsi_update)
        schedule.every().day.at("12:40:10").do(rsi_update)
        schedule.every().day.at("12:45:10").do(rsi_update)
        schedule.every().day.at("12:45:11").do(bankfuture_15)
        schedule.every().day.at("12:50:10").do(rsi_update)
        schedule.every().day.at("12:55:10").do(rsi_update)
        schedule.every().day.at("13:00:10").do(rsi_update)
        schedule.every().day.at("13:00:11").do(bankfuture_15)
        schedule.every().day.at("13:05:10").do(rsi_update)
        schedule.every().day.at("13:10:10").do(rsi_update)
        schedule.every().day.at("13:15:10").do(rsi_update)
        schedule.every().day.at("13:15:11").do(bankfuture_15)
        schedule.every().day.at("13:15:11").do(bankfuture_60)
        schedule.every().day.at("13:20:10").do(rsi_update)
        schedule.every().day.at("13:25:10").do(rsi_update)
        schedule.every().day.at("13:30:10").do(rsi_update)
        schedule.every().day.at("13:30:11").do(bankfuture_15)
        schedule.every().day.at("13:35:10").do(rsi_update)
        schedule.every().day.at("13:40:10").do(rsi_update)
        schedule.every().day.at("13:45:10").do(rsi_update)
        schedule.every().day.at("13:45:11").do(bankfuture_15)
        schedule.every().day.at("13:50:10").do(rsi_update)
        schedule.every().day.at("13:55:10").do(rsi_update)
        schedule.every().day.at("14:00:10").do(rsi_update)
        schedule.every().day.at("14:00:11").do(bankfuture_15)
        schedule.every().day.at("14:05:10").do(rsi_update)
        schedule.every().day.at("14:10:10").do(rsi_update)
        schedule.every().day.at("14:15:10").do(rsi_update)
        schedule.every().day.at("14:15:11").do(bankfuture_15)
        schedule.every().day.at("14:15:12").do(bankfuture_60)
        schedule.every().day.at("14:20:10").do(rsi_update)
        schedule.every().day.at("14:25:10").do(rsi_update)
        schedule.every().day.at("14:30:10").do(rsi_update)
        schedule.every().day.at("14:30:11").do(bankfuture_15)
        schedule.every().day.at("14:35:10").do(rsi_update)
        schedule.every().day.at("14:40:10").do(rsi_update)
        schedule.every().day.at("14:45:10").do(rsi_update)
        schedule.every().day.at("14:45:11").do(bankfuture_15)
        schedule.every().day.at("14:50:10").do(rsi_update)
        schedule.every().day.at("14:55:10").do(rsi_update)
        schedule.every().day.at("15:00:10").do(rsi_update)
        schedule.every().day.at("15:00:11").do(bankfuture_15)
        schedule.every().day.at("15:05:10").do(rsi_update)
        schedule.every().day.at("15:10:10").do(rsi_update)
        schedule.every().day.at("15:15:10").do(rsi_update)
        schedule.every().day.at("15:15:11").do(bankfuture_15)
        schedule.every().day.at("15:15:12").do(bankfuture_60)
        schedule.every().day.at("15:20:10").do(rsi_update)
        schedule.every().day.at("15:25:10").do(rsi_update)
        schedule.every().day.at("15:30:10").do(update_missing_details)
        if wednesday == 7 or (wednesday == 1 and shortweek == 1):
            schedule.every().day.at("14:39:01").do(close_intra_trade)
            schedule.every().day.at("14:59:02").do(close_sstngle)
            schedule.every().day.at("14:59:03").do(close_strad)
            schedule.every().day.at("15:27:01").do(close_position)
            schedule.every().day.at("15:27:02").do(stbt)
        else:
            schedule.every().day.at("15:26:01").do(close_intra_trade)
            schedule.every().day.at("15:26:02").do(close_sstngle)
            schedule.every().day.at("15:26:03").do(close_strad)
            schedule.every().day.at("15:27:01").do(close_position)
            schedule.every().day.at("15:27:02").do(stbt)
    while 1:
        schedule.run_pending()
        sleep(1)

elif question.lower() == 'f':
    question1 = input('Any short week? n for No, 1 for this week: ')
    if question1.lower() == 'n':
        shortweek = 0
    elif question1.lower() == '1':
        shortweek = 1
    elif question1.lower() == '2':
        shortweek = 2

    if time(5, 35) < datetime.now().time() < time(15, 35):
        display_trade()
        weeks()
        # fresh_setup_delta_ironfly(0)
        # fresh_setup_delta_ironfly(1)
        # fresh_setup_delta_ironfly(2)
        # schedule.every().day.at("12:45:00").do(new_expiry_entry)
        # schedule.every().day.at("14:17:01").do(new_entry)
        # schedule.every().day.at("09:15:03").do(position_holding_SL)
        # schedule.every().day.at("09:20:10").do(fresh_setup_delta_ironfly)
        # schedule.every().day.at("09:15:02").do(short_straddle_entry)
        schedule.every().day.at("09:17:02").do(short_straddle_entry)
        schedule.every().day.at("09:17:10").do(bankfuture_5)
        schedule.every().day.at("09:17:11").do(bankfuture_15)
        schedule.every().day.at("09:17:12").do(bankfuture_60)
        schedule.every().day.at("09:17:13").do(bankfuture_1D)
        schedule.every().day.at("09:18:01").do(new_position)
        schedule.every().day.at("09:18:03").do(single_strangle_entry)
        schedule.every(25).seconds.do(update)
        # schedule.every(5).minutes.do(rsi_update)
        schedule.every().day.at("09:20:10").do(rsi_update)
        schedule.every().day.at("09:25:10").do(rsi_update)
        schedule.every().day.at("09:30:10").do(rsi_update)
        schedule.every().day.at("09:30:11").do(bankfuture_15)
        schedule.every().day.at("09:35:10").do(rsi_update)
        schedule.every().day.at("09:40:10").do(rsi_update)
        schedule.every().day.at("09:45:10").do(rsi_update)
        schedule.every().day.at("09:45:11").do(bankfuture_15)
        schedule.every().day.at("09:50:10").do(rsi_update)
        schedule.every().day.at("09:55:10").do(rsi_update)
        schedule.every().day.at("10:00:10").do(rsi_update)
        schedule.every().day.at("10:00:11").do(bankfuture_15)
        schedule.every().day.at("10:05:10").do(rsi_update)
        schedule.every().day.at("10:10:10").do(rsi_update)
        schedule.every().day.at("10:15:10").do(rsi_update)
        schedule.every().day.at("10:15:11").do(bankfuture_15)
        schedule.every().day.at("10:15:12").do(bankfuture_60)
        schedule.every().day.at("10:20:10").do(rsi_update)
        schedule.every().day.at("10:25:10").do(rsi_update)
        schedule.every().day.at("10:30:10").do(rsi_update)
        schedule.every().day.at("10:30:11").do(bankfuture_15)
        schedule.every().day.at("10:35:10").do(rsi_update)
        schedule.every().day.at("10:40:10").do(rsi_update)
        schedule.every().day.at("10:45:10").do(rsi_update)
        schedule.every().day.at("10:45:11").do(bankfuture_15)
        schedule.every().day.at("10:50:10").do(rsi_update)
        schedule.every().day.at("10:55:10").do(rsi_update)
        schedule.every().day.at("11:00:10").do(rsi_update)
        schedule.every().day.at("11:00:11").do(bankfuture_15)
        schedule.every().day.at("11:05:10").do(rsi_update)
        schedule.every().day.at("11:10:10").do(rsi_update)
        schedule.every().day.at("11:15:10").do(rsi_update)
        schedule.every().day.at("11:15:11").do(bankfuture_15)
        schedule.every().day.at("11:15:12").do(bankfuture_60)
        schedule.every().day.at("11:20:10").do(rsi_update)
        schedule.every().day.at("11:25:10").do(rsi_update)
        schedule.every().day.at("11:30:10").do(rsi_update)
        schedule.every().day.at("11:30:11").do(bankfuture_15)
        schedule.every().day.at("11:35:10").do(rsi_update)
        schedule.every().day.at("11:40:10").do(rsi_update)
        schedule.every().day.at("11:45:10").do(rsi_update)
        schedule.every().day.at("11:45:11").do(bankfuture_15)
        schedule.every().day.at("11:50:10").do(rsi_update)
        schedule.every().day.at("11:55:10").do(rsi_update)
        schedule.every().day.at("12:00:10").do(rsi_update)
        schedule.every().day.at("12:00:11").do(bankfuture_15)
        schedule.every().day.at("12:05:10").do(rsi_update)
        schedule.every().day.at("12:10:10").do(rsi_update)
        schedule.every().day.at("12:15:10").do(rsi_update)
        schedule.every().day.at("12:15:11").do(bankfuture_15)
        schedule.every().day.at("12:25:12").do(bankfuture_60)
        schedule.every().day.at("12:20:10").do(rsi_update)
        schedule.every().day.at("12:25:10").do(rsi_update)
        schedule.every().day.at("12:30:10").do(rsi_update)
        schedule.every().day.at("12:30:11").do(bankfuture_15)
        schedule.every().day.at("12:35:10").do(rsi_update)
        schedule.every().day.at("12:40:10").do(rsi_update)
        schedule.every().day.at("12:45:10").do(rsi_update)
        schedule.every().day.at("12:45:11").do(bankfuture_15)
        schedule.every().day.at("12:50:10").do(rsi_update)
        schedule.every().day.at("12:55:10").do(rsi_update)
        schedule.every().day.at("13:00:10").do(rsi_update)
        schedule.every().day.at("13:00:11").do(bankfuture_15)
        schedule.every().day.at("13:05:10").do(rsi_update)
        schedule.every().day.at("13:10:10").do(rsi_update)
        schedule.every().day.at("13:15:10").do(rsi_update)
        schedule.every().day.at("13:15:11").do(bankfuture_15)
        schedule.every().day.at("13:15:11").do(bankfuture_60)
        schedule.every().day.at("13:20:10").do(rsi_update)
        schedule.every().day.at("13:25:10").do(rsi_update)
        schedule.every().day.at("13:30:10").do(rsi_update)
        schedule.every().day.at("13:30:11").do(bankfuture_15)
        schedule.every().day.at("13:35:10").do(rsi_update)
        schedule.every().day.at("13:40:10").do(rsi_update)
        schedule.every().day.at("13:45:10").do(rsi_update)
        schedule.every().day.at("13:45:11").do(bankfuture_15)
        schedule.every().day.at("13:50:10").do(rsi_update)
        schedule.every().day.at("13:55:10").do(rsi_update)
        schedule.every().day.at("14:00:10").do(rsi_update)
        schedule.every().day.at("14:00:11").do(bankfuture_15)
        schedule.every().day.at("14:05:10").do(rsi_update)
        schedule.every().day.at("14:10:10").do(rsi_update)
        schedule.every().day.at("14:15:10").do(rsi_update)
        schedule.every().day.at("14:15:11").do(bankfuture_15)
        schedule.every().day.at("14:15:12").do(bankfuture_60)
        schedule.every().day.at("14:20:10").do(rsi_update)
        schedule.every().day.at("14:25:10").do(rsi_update)
        schedule.every().day.at("14:30:10").do(rsi_update)
        schedule.every().day.at("14:30:11").do(bankfuture_15)
        schedule.every().day.at("14:35:10").do(rsi_update)
        schedule.every().day.at("14:40:10").do(rsi_update)
        schedule.every().day.at("14:45:10").do(rsi_update)
        schedule.every().day.at("14:45:11").do(bankfuture_15)
        schedule.every().day.at("14:50:10").do(rsi_update)
        schedule.every().day.at("14:55:10").do(rsi_update)
        schedule.every().day.at("15:00:10").do(rsi_update)
        schedule.every().day.at("15:00:11").do(bankfuture_15)
        schedule.every().day.at("15:05:10").do(rsi_update)
        schedule.every().day.at("15:10:10").do(rsi_update)
        schedule.every().day.at("15:15:10").do(rsi_update)
        schedule.every().day.at("15:15:11").do(bankfuture_15)
        schedule.every().day.at("15:15:12").do(bankfuture_60)
        schedule.every().day.at("15:20:10").do(rsi_update)
        schedule.every().day.at("15:25:10").do(rsi_update)
        schedule.every().day.at("15:30:10").do(update_missing_details)
        if wednesday == 7 or (wednesday == 1 and shortweek == 1):
            schedule.every().day.at("14:39:01").do(close_intra_trade)
            schedule.every().day.at("14:59:02").do(close_sstngle)
            schedule.every().day.at("14:59:03").do(close_strad)
            schedule.every().day.at("15:27:01").do(close_position)
            schedule.every().day.at("15:27:02").do(stbt)
        else:
            schedule.every().day.at("15:26:01").do(close_intra_trade)
            schedule.every().day.at("15:26:02").do(close_sstngle)
            schedule.every().day.at("15:26:03").do(close_strad)
            schedule.every().day.at("15:27:01").do(close_position)
            schedule.every().day.at("15:27:02").do(stbt)
        # sched.start()
    while True:
        schedule.run_pending()
        sleep(1)