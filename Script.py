from time import sleep
import dateutil
import pandas as pd
import pandas_ta as ta
import schedule
from random import randint
from copy import deepcopy
from datetime import datetime, time
from dateutil.relativedelta import relativedelta, TH
from models import *
from models import Clients
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pandas import DataFrame as df
from sqlalchemy.exc import NoResultFound
engine = create_engine('sqlite:///database.db')
schema = declarative_base().metadata
Session = sessionmaker(bind=engine)
session = Session()

API_VERSION = '2.0'
NO = 0
YES = 1
NOT_APPLICABLE = 'NA'
PUT = 'Put'
CALL = 'Call'
BANK_INDEX = 'NSE_INDEX|Nifty Bank'

active_clients = list()

no_of_requests = 0
no_of_clients = 0

for _ in session.query(Credentials).filter_by(is_active=YES):
    active_clients.append(Client(_.client_id, _.access_token, session))
    no_of_clients += 1

def get_symbol(tradingsymbol: str):
    if len(tradingsymbol) == 21:
        month = datetime.strptime("0" + tradingsymbol[11], "%m").strftime("%b").upper()
    else:
        month = datetime.strptime(tradingsymbol[11:13], "%m").strftime("%b").upper()
    return " ".join([ tradingsymbol[:9],  tradingsymbol[-7: -2],  tradingsymbol[-2:],  tradingsymbol[-9:-7],  month, tradingsymbol[9:11]])



def get_token(tradingsymbol: str) -> str:
    """Return the token of the given tradingsymbol"""
    return (session
        .query(Instruments)
        .filter_by(trading_symbol=tradingsymbol)
        .first()
        .instrument_key
    )


def get_ltp(tradingsymbol: str) -> float:
    """Return the last traded price of the given tradingsymbol"""
    global no_of_requests
    try:
        # {'NSE_FO:BANKNIFTY 44400 PE 22 MAY 24': {'last_price': 5.05, 'instrument_token': 'NSE_FO|39855'}}
        ltp = list(active_clients[no_of_requests % no_of_clients].market_quote_api.ltp(
            get_token(tradingsymbol), API_VERSION
        ).to_dict()['data'].values())[0]['last_price']
        no_of_requests += 1
    except ApiException as e:
        print("Exception when calling MarketDataApi->ltp: %s\n" % e)
        ltp = 0
    return ltp

get_ltp(tradingsymbol="BANKNIFTY2452244400PE")

def get_banknifty_ltp() -> float:
    """Return the last traded price of the Bank Nifty Index"""
    global no_of_requests

    ltp = active_clients[no_of_requests % no_of_clients].market_quote_api.ltp(
        'NSE_INDEX|Nifty Bank', API_VERSION
    ).to_dict()['data']['NSE_INDEX:Nifty Bank']['last_price']
    no_of_requests += 1
    return ltp


def get_trades() -> list:
    """Return all the trades in the database"""
    return session.query(Trades).all()


last_price = get_banknifty_ltp()

last_price_0 = round(last_price / 100) * 100

strike_ce = [(last_price_0 + 100 * factor) for factor in range(69)]
strike_ce = [(last_price_0 - 100)] + strike_ce
strike_pe = [(last_price_0 - 100 * factor) for factor in range(69)]
strike_pe = [(last_price_0 + 100)] + strike_pe

shortweek = 0

to_date = todays_date = datetime.strftime(datetime.now(), '%Y-%m-%d')
from_date = datetime.strptime(to_date, '%Y-%m-%d')
to_date = from_date + dateutil.relativedelta.relativedelta(days=1)
to_date = datetime.strftime(to_date, '%Y-%m-%d')
print('to_date is', to_date)
from_date = from_date - dateutil.relativedelta.relativedelta(days=5)
from_date = datetime.strftime(from_date, '%Y-%m-%d')
print('from_date is', from_date)


def supertrend(period: int = 10, multiplier: int = 4) -> float:
    global trend
    # Download historical data
    api_instance = upstox_client.HistoryApi()
    instrument_key = 'NSE_FO|46923'  # str |
    interval = '1minute'  # str |
    api_version = '2.0'  # str | API Version Header

    try:
        intraday = api_instance.get_intra_day_candle_data(instrument_key, interval, api_version)
        print("Intrday successful")
        historical = api_instance.get_historical_candle_data1(instrument_key, interval, todays_date, from_date, api_version)
        print("historical + intraday successful")
        ohlc_data = df(
            data=intraday.data.candles + historical.data.candles,
            index=[candle_data[0] for candle_data in intraday.data.candles] + [candle_data[0] for candle_data in historical.data.candles],
            columns=['TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'OI']
        )
        data = ohlc_data[['Open', 'High', 'Low', 'Close']][::-1]

    except ApiException as e:
        print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)

    def something(multiplier: int):
        global profit1, profit2, profit3, profit4, profit5
        sti = ta.supertrend(data['High'], data['Low'], data['Close'], 10, multiplier)
        count = -1
        profit = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        # 0th = last trend profit
        # 1st = Previous to last trend profit
        # 2nd = Current trend - 3 profit
        # 3rd = Current trend - 4 profit
        # 4th = Current trend direction
        # 5th = no. of candles in current trend
        # 6th = SL of the current trend
        # 7th = no. of candles in last 4 cycle + current trend
        # 8th = profit points of current trend
        profit[4] = sti[f'SUPERTd_10_{multiplier}.0'].iloc[-1]
        profit[6] = round(sti[f'SUPERT_10_{multiplier}.0'].iloc[-1], 2)
        close_value = last_value = data['Close'].iloc[-1]
        for j in range(1, 400):
            if sti[f'SUPERTd_10_{multiplier}.0'].iloc[-j] != sti[f'SUPERTd_10_{multiplier}.0'].iloc[-j - 1]:
                if count == -1:
                    last_value = data['Close'].iloc[-j]
                    profit[5] = j
                    if profit[4] == 1:
                        profit[8] = round(close_value - last_value, 2)
                    else:
                        profit[8] = round(last_value - close_value, 2)
                    count += 1
                    continue
                if sti[f'SUPERTd_10_{multiplier}.0'].iloc[-j-1] == 1:
                    profit[count] = round(data['Close'].iloc[-j] - last_value, 2)
                    count += 1
                    last_value = data['Close'].iloc[-j]
                elif sti[f'SUPERTd_10_{multiplier}.0'].iloc[-j - 1] == -1:
                    profit[count] = round(last_value - data['Close'].iloc[-j], 2)
                    count += 1
                    last_value = data['Close'].iloc[-j]
                if count == 4:
                    profit[7] = j
                    break
        return profit

    profit1 = something(1)
    profit2 = something(2)
    profit3 = something(3)
    profit4 = something(4)
    profit5 = something(5)
    print('Analysis', datetime.now().time())
    print(profit1)
    print(profit2)
    print(profit3)
    print(profit4)
    print(profit5)

    client = active_clients[0]
    if profit5[8] > 10:
        if profit5[4] == 1:
            if profit4[8] > 10:
                if profit4[4] == 1:
                    if profit3[8] > 10:
                        return micro_trend(profit1, profit2, profit3, profit4, profit5)
                    else:
                        print('Trend is not defined in 3.0')
                        print('+5^, +4^, -3')
                else:
                    if profit3[8] > 10:
                        if profit3[4] == 1:
                            print('Trend is not defined in 3.0')
                            print('+5^, +4v, +3^')
                        else:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
                    else:
                        if profit3[4] == 1:
                            print('Trend is not defined in 3.0')
                            print('+5^, -4v, -3^')
                        else:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)

            else:
                if profit4[4] == 1:
                    if profit3[8] > 10:
                        if profit3[4] == 1:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
                        else:
                            print('Trend is not defined in 3.0')
                            print('+5^, -4^, +3v')
                    else:
                        print('Trend is not defined in 3.0')
                        print('+5^, -4^, -3')
                else:
                    if profit3[8] > 10:
                        if profit3[4] == 1:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
                        else:
                            print('Trend is not defined in 3.0')
                            print('+5^, -4v, +3v')
                    else:
                        print('Trend is not defined in 3.0')
                        print('+5^, -4v, -3')
        else:
            if profit4[8] > 10:
                if profit4[4] == 1:
                    if profit3[8] > 10:
                        if profit3[4] == 1:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
                        else:
                            print('Trend is not defined in 3.0')
                            print('+5v, +4^, +3v')
                    else:
                        print('Trend is not defined in 3.0')
                        print('+5v, +4^, -3')
                else:
                    return micro_trend(profit1, profit2, profit3, profit4, profit5)
            else:
                if profit4[4] == 1:
                    if profit3[8] > 10:
                        if profit3[4] == 1:
                            print('Trend is not defined in 3.0')
                            print('+5v, -4^, +3^')
                        else:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
                    else:
                        if profit3[4] == 1:
                            print('Trend is not defined in 3.0')
                            print('+5v, -4^, -3^')
                        else:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
                else:
                    if profit3[8] > 10:
                        if profit3[4] == 1:
                            print('Trend is not defined in 3.0')
                            print('+5v, -4v, +3^')
                        else:
                            return micro_trend(profit1, profit2, profit3, profit4, profit5)
    elif profit4[8] > 10:
        if profit4[4] == 1:
            if profit3[8] > 10:
                if profit3[4] == 1:
                    return micro_trend(profit1, profit2, profit3, profit4, profit5)
                else:
                    print('Trend is not defined in 3.0')
                    print('-5, +4^, +3v')
            else:
                if profit3[4] == 1:
                    return micro_trend(profit1, profit2, profit3, profit4, profit5)
                else:
                    print('Trend is not defined in 3.0')
                    print('-5, +4^, -3v')
        else:
            if profit3[8] > 10:
                if profit3[4] == 1:
                    print('Trend is not defined in 3.0')
                    print('-5, +4v, +3^')
                else:
                    return micro_trend(profit1, profit2, profit3, profit4, profit5)
            else:
                if profit3[4] == 1:
                    print('Trend is not defined in 3.0')
                    print('-5, +4v, -3^')
                else:
                    return micro_trend(profit1, profit2, profit3, profit4, profit5)
    elif profit3[8] > 10:
        return micro_trend(profit1, profit2, profit3, profit4, profit5)
    else:
        print('Trend is not defined in any case')

def micro_trend(profit1, profit2, profit3, profit4, profit5):
    global trend
    if profit1[0] > 20 and profit1[1] > 10 or profit1[0] > 80:
        if profit1[5] != 1 and profit1[4] == trend:
            print(f'Trend is same as before {trend} for 1.0 and SL is', profit1[6], profit1[4])
            return profit1[6]
        else:
            trend = profit1[4]
            print(f'Trend is {profit1[4]} as per 1.0')
            return profit1[4]
    elif (profit1[0] > 20 or profit1[1] > 10) and profit1[4] == profit3[4] and profit1[7] > 40:
        if profit1[5] != 1 and profit1[4] == trend:
            print(f'Trend is same as before {trend} for 1.0 and SL is', profit1[6], profit1[5])
            return profit1[6]
        else:
            trend = profit1[4]
            print(f'Trend is {profit1[4]} as per 1.0')
            return profit1[4]
    elif profit1[0] < 10 and profit1[4] == profit3[4] == profit4[4] and profit1[7] > 45:
        if profit1[5] != 1 and profit1[4] == trend:
            print(f'Trend is same as before {trend} for 1.0 and SL is', profit1[6], profit1[5])
            return profit1[6]
        else:
            trend = profit1[4]
            print(f'Trend is {profit1[4]} as per 1.0')
            return profit1[4]
    elif profit1[0] < 0 and profit1[4] != profit2[4]:
        if profit2[5] != 1 and profit2[4] == trend:
            print(f'Trend is same as before {trend} for 2.0 and SL is', profit2[6], profit2[5])
            return profit2[6]
        else:
            trend = profit2[4]
            print(f'Trend is {profit2[4]} as per 2.0')
            return profit2[4]
    elif profit2[0] > 10 and profit2[1] > 10:
        if profit2[5] != 1 and profit2[4] == trend:
            print(f'Trend is same as before {trend} for 2.0 and SL is', profit2[6], profit2[5])
            return profit2[6]
        else:
            trend = profit2[4]
            print(f'Trend is {profit2[4]} as per 2.0')
            return profit2[4]
    elif (profit2[0] > 10 or profit2[1] > 10) and profit3[4] == profit4[4]:
        if profit2[5] != 1 and profit2[4] == trend:
            print(f'Trend is same as before {trend} for 2.0 and SL is', profit2[6], profit2[5])
            return profit2[6]
        else:
            trend = profit2[4]
            print(f'Trend is {profit2[4]} as per 1.0')
            return profit2[4]
    elif profit2[0] < 10 and profit2[4] != profit3[4]:
        if profit3[5] != 1 and profit3[4] == trend:
            print(f'Trend is same as before {trend} for 3.0 and SL is', profit3[6], profit3[5])
            return profit3[6]
        else:
            trend = profit3[4]
            print(f'Trend is {profit3[4]} as per 3.0')
            return profit3[4]
    elif profit3[0] > 10 and profit3[1] > 10:
        if profit3[5] != 1 and profit2[4] == trend:
            print(f'Trend is same as before {trend} for 3.0 and SL is', profit3[6], profit3[5])
            return profit3[6]
        else:
            trend = profit3[4]
            print(f'Trend is {profit3[4]} as per 3.0')
            return profit3[4]
    elif profit3[0] < 10 and profit3[4] != profit4[4]:
        if profit4[5] != 1 and profit4[4] == trend:
            print(f'Trend is same as before {trend} for 4.0 and SL is', profit4[6], profit4[5])
            return profit4[6]
        else:
            trend = profit4[4]
            print(f'Trend is {profit4[4]} as per 4.0')
            return profit4[4]
    elif profit4[0] > 10 and profit4[1] > 10:
        if profit4[5] != 1 and profit4[4] == trend:
            print(f'Trend is same as before {trend} for 4.0 and SL is ', profit4[6], profit4[5])
            return profit4[6]
        else:
            trend = profit4[4]
            print(f'Trend is {profit4[4]} as per 4.0')
            return profit4[4]

    elif profit1[0] > 10 or profit1[1] > 10:
        if profit1[5] != 1 and profit1[4] == trend:
            print(f'Trend is same as before {trend} for 1.0 and SL is ', profit1[6], profit1[5])
            return profit1[6]
        else:
            trend = profit1[4]
            print(f'Trend is {profit1[4]} as per 1.0 with any one profit')
            return profit1[4]

    elif profit2[0] > 10 or profit2[1] > 10:
        if profit2[5] != 1 and profit2[4] == trend:
            print(f'Trend is same as before {trend} for 2.0 and SL is ', profit2[6], profit2[5])
            return profit2[6]
        else:
            trend = profit2[4]
            print(f'Trend is {profit2[4]} as per 2.0 with any one profit')
            return profit2[4]

    elif profit3[0] > 10 or profit3[1] > 10:
        if profit3[5] != 1 and profit3[4] == trend:
            print(f'Trend is same as before {trend} for 3.0 and SL is ', profit3[6], profit3[5])
            return profit3[6]
        else:
            trend = profit3[4]
            print(f'Trend is {profit3[4]} as per 3.0 with any one profit')
            return profit3[4]

    else:
        print('Trend is not defined for any multiplier')
        return 0

def optionbuy(client, option):
    global trend
    if option[-2:] == 'CE':
        strike = int(option[-7:-2]) - 200
        buyoption = option[:-7] + str(strike) +'CE'
    else:
        strike = int(option[-7:-2]) + 200
        buyoption = option[:-7] + str(strike) +'PE'
    
    api_instance = upstox_client.HistoryApi()
    instrument_key = get_token(buyoption) # str |
    interval = '1minute'  # str |
    api_version = '2.0'  # str | API Version Header

    try:
        intraday = api_instance.get_intra_day_candle_data(instrument_key, interval, api_version)
        print("Intrday successful")
        historical = api_instance.get_historical_candle_data1(instrument_key, interval, todays_date, from_date, api_version)
        print("historical + intraday successful")
        ohlc_data = df(
            data=intraday.data.candles + historical.data.candles,
            index=[candle_data[0] for candle_data in intraday.data.candles] + [candle_data[0] for candle_data in historical.data.candles],
            columns=['TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'OI']
        )
        data = ohlc_data[['Open', 'High', 'Low', 'Close']][::-1]

    except ApiException as e:
        print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)
    sti = ta.supertrend(data['High'], data['Low'], data['Close'], 10, 2)
    direction = sti['SUPERTd_10_2.0'].iloc[-1]
    print('Direction for buying is', direction)
    trend = direction
    if trend == 1:
        flags = session.query(Flags).filter_by(client_id=client.client_id).one()
        if option[-2:] == 'CE':
            flags.optionbuy = 1
        else:
            flags.optionbuy = -1
        new_trade = Trades()
        new_trade.client_id = client.client_id
        new_trade.strategy = Strategy.OPTIONBUY.value
        new_trade.quantity = client.strategy.optionbuy * 15
        new_trade.days_left = fromtime1
        new_trade.trade_type = 'BUY'
        new_trade.rank = 'trending'
        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
        new_trade.date_time = datetime.now().time()
        new_trade.exit_price = -1
        new_trade.exit_status = NOT_APPLICABLE
        new_trade.profit_loss = 0
        new_trade.symbol = buyoption
        print(buyoption)
        new_trade.ltp = get_ltp(buyoption)
        new_trade.order_id = randint(10, 99)
        parameters = client.market_quote_api.get_full_market_quote(get_token(buyoption),
                                                                    API_VERSION).to_dict()
        new_trade.entry_price = parameters['data'][get_symbol(buyoption)]['depth']['sell'][0][
                                    'price']
        try:
            order = client.place_order(
                quantity=new_trade.quantity,
                price=0,
                tradingsymbol=new_trade.symbol,
                order_type=OrderType.MARKET,
                transaction_type=TransactionType.BUY.value
            )
            order_id = order['data']['order_id']  # Extract the order_id
            new_trade.order_id = order_id
        except ApiException as e:
            print("Exception when calling OrderApi->place_order: %s\n" % e)
        session.add(deepcopy(new_trade))
        session.commit()  

def close_future_hedge():
    super_trend = supertrend()
    print(super_trend)
    for client in active_clients:
        if client.strategy.futures > 0:
            print('Checking for future hedge for closing', client)
            if super_trend == -1 or super_trend == 1:
                # checking for calls
                try:
                    put_ltp = client.get_trades().filter(
                        Trades.rank.startswith('Put'),
                        Trades.status == TradeStatus.LIVE.value,
                        Trades.trade_type == TransactionType.SELL.value,
                        Trades.strategy == Strategy.FIXED_PROFIT.value
                    ).one().ltp
                except Exception as e:
                    print(e)
                    try:
                        put_ltp = client.get_trades().filter(
                            Trades.rank.startswith('Put'),
                            Trades.status == TradeStatus.ORDERED.value,
                            Trades.trade_type == TransactionType.SELL.value,
                            Trades.strategy == Strategy.FIXED_PROFIT.value
                        ).one().ltp
                    except Exception as e:
                        print(e)
                        continue
                print('Put LTP is', put_ltp)
                try:
                    call_ltp = client.get_trades().filter(
                        Trades.rank.startswith('Call'),
                        Trades.status == TradeStatus.LIVE.value,
                        Trades.trade_type == TransactionType.SELL.value,
                        Trades.strategy == Strategy.FIXED_PROFIT.value
                    ).one().ltp
                except Exception as e:
                    print(e)
                    try:
                        call_ltp = client.get_trades().filter(
                            Trades.rank.startswith('Call'),
                            Trades.status == TradeStatus.ORDERED.value,
                            Trades.trade_type == TransactionType.SELL.value,
                            Trades.strategy == Strategy.FIXED_PROFIT.value
                        ).one().ltp
                    except Exception as e:
                        print(e)
                        continue
                print('Call LTP is', call_ltp)
                if call_ltp == 0 or put_ltp == 0:
                    print('Not doing anything since 0')
                    continue
                elif call_ltp > 95 and put_ltp > 95:
                    if super_trend == -1:
                        if client.get_flags().future == 1.:
                            print('Selling future double')
                            qty: int = client.strategy.futures * 15 * 2
                            trade_to_exit = client.get_trades().filter(
                                Trades.status == TradeStatus.LIVE.value,
                                Trades.strategy == Strategy.FUT_HEDGE.value
                            ).first()
                            trade_to_exit.status = TradeStatus.CLOSING.value
                        elif client.get_flags().future == 0:
                            print('Selling future single')
                            qty: int = client.strategy.futures * 15
                        else:
                            print('Not doing anything')
                            continue
                        client.get_flags().future = -1
                        # Sell double
                        print('Selling now')
                        new_trade = Trades()  # Create a new trade object
                        new_trade.strategy = Strategy.FUT_HEDGE.value
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.days_left = fromtime1
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0
                        new_trade.client_id = client.client_id
                        new_trade.quantity = client.strategy.futures * 15
                        new_trade.rank = 'Trend'
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.symbol = month1b + 'FUT'
                        new_trade.trade_type = TransactionType.SELL.value
                        new_trade.ltp = get_ltp(new_trade.symbol)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(new_trade.symbol), API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][get_symbol(new_trade.symbol)]['depth']['sell'][0]['price'] - 0.05
                        try:
                            order = client.place_order(
                                quantity=qty,
                                price=0,
                                tradingsymbol=new_trade.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=TransactionType.SELL.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                        # Use deepcopy to add the current state of new trade to Trades Table
                        session.add(deepcopy(new_trade))
                        if qty == client.strategy.futures * 15 * 2:
                            trade_to_exit = client.get_trades().filter(
                                Trades.status == TradeStatus.LIVE.value,
                                Trades.strategy == Strategy.FUT_HEDGE.value
                            ).first()
                            try:
                                order_details = client.order_api.get_order_details(
                                    api_version=API_VERSION, order_id=new_trade.order_id
                                )
                                trade_to_exit.exit_status = order_details.data[-1].status
                                trade_to_exit.exit_order_id = new_trade.order_id
                            except ApiException:
                                print('Unable to find order details, passing for now')
                            trade_to_exit.status = TradeStatus.CLOSING.value
                        # save the changes to the database
                        session.commit()
                    elif super_trend == 1.:
                        if client.get_flags().future == -1:
                            qty: int = client.strategy.futures * 15 * 2
                            print('Buying future double')
                        elif client.get_flags().future == 0:
                            qty: int = client.strategy.futures * 15
                            print('Buying future single')
                        else:
                            print('Not doing anything')
                            continue
                        client.get_flags().future = 1
                        # Buy double
                        print('Buying now')
                        new_trade = Trades()  # Create a new trade object
                        new_trade.strategy = Strategy.FUT_HEDGE.value
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.days_left = fromtime1
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0
                        new_trade.client_id = client.client_id
                        new_trade.quantity = client.strategy.futures * 15
                        new_trade.rank = 'Trend'
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.symbol = month1b + 'FUT'
                        new_trade.trade_type = TransactionType.BUY.value
                        new_trade.ltp = get_ltp(new_trade.symbol)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(new_trade.symbol),
                                                                                   API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][get_symbol(new_trade.symbol)]['depth']['sell'][0][
                                                    'price'] - 0.05
                        try:
                            order = client.place_order(
                                quantity=qty,
                                price=0,
                                tradingsymbol=new_trade.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=TransactionType.BUY.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                        # Use deepcopy to add the current state of new trade to Trades Table
                        session.add(deepcopy(new_trade))

                        trade_to_exit = client.get_trades().filter(
                            Trades.status == TradeStatus.LIVE.value,
                            Trades.strategy == Strategy.FUT_HEDGE.value
                        ).first()
                        try:
                            order_details = client.order_api.get_order_details(
                                api_version=API_VERSION, order_id=new_trade.order_id
                            )
                            trade_to_exit.exit_status = order_details.data[-1].status
                            trade_to_exit.exit_order_id = new_trade.order_id
                        except ApiException:
                            print('Unable to find order details, passing for now')
                        trade_to_exit.status = TradeStatus.CLOSING.value
                        # save the changes to the database
                        session.commit()
                elif call_ltp > 95 > put_ltp:
                    if super_trend == -1.:
                        if client.get_flags().future == 1:
                            qty: int = client.strategy.futures * 15
                        else:
                            print('Not doing anything')
                            continue
                        client.get_flags().future = 0
                        # Sell single
                        print('Closing future long')
                        trade_to_exit = client.get_trades().filter(
                            Trades.status == TradeStatus.LIVE.value,
                            Trades.strategy == Strategy.FUT_HEDGE.value
                        ).first()

                        close_trade_type = TransactionType.SELL

                        order = client.place_order(
                            quantity=qty,
                            price=0,
                            tradingsymbol=trade_to_exit.symbol,
                            order_type=OrderType.MARKET,
                            transaction_type=close_trade_type
                        )
                        order_id = order['data']['order_id']  # Extract the order_id


                        trade_to_exit.exit_status = 'Closing'
                        trade_to_exit.status = TradeStatus.CLOSING.value
                        trade_to_exit.exit_order_id = order_id

                        # save the changes to the database
                        session.commit()
                        try:
                            order_details = client.order_api.get_order_details(
                                api_version=API_VERSION, order_id=order_id
                            )
                            trade_to_exit.exit_status = order_details.data[-1].status
                            session.commit()
                        except ApiException:
                            print('Unable to find order details, passing for now')
                    elif super_trend == 1.:
                        if client.get_flags().future == -1:
                            qty: int = client.strategy.futures * 15 * 2
                        elif client.get_flags().future == 0:
                            qty: int = client.strategy.futures * 15
                        else:
                            print('Not doing anything')
                            continue
                        client.get_flags().future = 1
                        # Buy single new
                        print('Buying future long')
                        new_trade = Trades()  # Create a new trade object
                        new_trade.strategy = Strategy.FUT_HEDGE.value
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.days_left = fromtime1
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0
                        new_trade.client_id = client.client_id
                        new_trade.quantity = client.strategy.futures * 15
                        new_trade.rank = 'Trend'
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.symbol = month1b + 'FUT'
                        new_trade.trade_type = TransactionType.BUY.value
                        new_trade.ltp = get_ltp(new_trade.symbol)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(new_trade.symbol),
                                                                                   API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][get_symbol(new_trade.symbol)]['depth']['sell'][0][
                                                    'price'] - 0.05
                        try:
                            order = client.place_order(
                                quantity=qty,
                                price=0,
                                tradingsymbol=new_trade.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=TransactionType.BUY.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                        # Use deepcopy to add the current state of new trade to Trades Table
                        session.add(deepcopy(new_trade))

                        # save the changes to the database
                        session.commit()
                elif call_ltp < 95 < put_ltp:
                    if super_trend == -1.:
                        if client.get_flags().future == 1:
                            print('Selling future double')
                            qty: int = client.strategy.futures * 15 * 2
                        elif client.get_flags().future == 0:
                            print('Selling future single')
                            qty: int = client.strategy.futures * 15
                        else:
                            print('Not doing anything')
                            continue
                        client.get_flags().future = -1
                        session.commit()
                        print('Future flag is', client.get_flags().future)
                        print('Selling now')
                        new_trade = Trades()  # Create a new trade object
                        new_trade.strategy = Strategy.FUT_HEDGE.value
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.days_left = fromtime1
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0
                        new_trade.client_id = client.client_id
                        new_trade.quantity = client.strategy.futures * 15
                        new_trade.rank = 'Trend'
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.symbol = month1b + 'FUT'
                        new_trade.trade_type = TransactionType.SELL.value
                        new_trade.ltp = get_ltp(new_trade.symbol)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(new_trade.symbol),
                                                                                   API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][get_symbol(new_trade.symbol)]['depth']['sell'][0][
                                                    'price'] - 0.05
                        try:
                            order = client.place_order(
                                quantity=qty,
                                price=0,
                                tradingsymbol=new_trade.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=TransactionType.SELL.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                        # Use deepcopy to add the current state of new trade to Trades Table
                        session.add(deepcopy(new_trade))

                        # save the changes to the database
                        session.commit()
                    elif super_trend == 1.:
                        if client.get_flags().future == -1:
                            qty: int = client.strategy.futures * 15
                        else:
                            print('Not doing anything')
                            continue

                        client.get_flags().future = 0
                        # Buy single to close
                        trade_to_exit = client.get_trades().filter(
                            Trades.status == TradeStatus.LIVE.value,
                            Trades.strategy == Strategy.FUT_HEDGE.value
                        ).first()

                        close_trade_type = TransactionType.BUY
                        try:
                            order = client.place_order(
                                quantity=trade_to_exit.quantity,
                                price=0,
                                tradingsymbol=trade_to_exit.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=close_trade_type
                            )
                        except ApiException:
                            print('guessing the missing qty')
                            order = client.place_order(
                                quantity=client.strategy.fixed_profit,
                                price=0,
                                tradingsymbol=trade_to_exit.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=close_trade_type
                            )
                        order_id = order['data']['order_id']  # Extract the order_id
                        try:
                            order_details = client.order_api.get_order_details(
                                api_version=API_VERSION, order_id=order_id
                            )
                            trade_to_exit.exit_status = order_details.data[-1].status
                            trade_to_exit.exit_order_id = order_id
                        except ApiException:
                            print('Unable to find order details, passing for now')
                        trade_to_exit.status = TradeStatus.CLOSING.value
                        # save the changes to the database
                        session.commit()
                elif call_ltp < 95 and put_ltp < 95:
                    if super_trend == -1.:
                        if client.get_flags().future == 1:
                            print('Selling future single')
                            client.get_flags().future = 0
                            # Sell Single to close
                            trade_to_exit = client.get_trades().filter(
                                Trades.status == TradeStatus.LIVE.value,
                                Trades.strategy == Strategy.FUT_HEDGE.value
                            ).first()

                            if trade_to_exit.trade_type == TransactionType.BUY.value:
                                close_trade_type = TransactionType.SELL
                            else:
                                close_trade_type = TransactionType.BUY
                            try:
                                order = client.place_order(
                                    quantity=trade_to_exit.quantity,
                                    price=0,
                                    tradingsymbol=trade_to_exit.symbol,
                                    order_type=OrderType.MARKET,
                                    transaction_type=close_trade_type
                                )
                            except ApiException:
                                print('guessing the missing qty')
                                order = client.place_order(
                                    quantity=client.strategy.fixed_profit,
                                    price=0,
                                    tradingsymbol=trade_to_exit.symbol,
                                    order_type=OrderType.MARKET,
                                    transaction_type=close_trade_type
                                )
                            order_id = order['data']['order_id']  # Extract the order_id
                            try:
                                order_details = client.order_api.get_order_details(
                                    api_version=API_VERSION, order_id=order_id
                                )
                                trade_to_exit.exit_order_id = order_id
                                trade_to_exit.exit_status = order_details.data[-1].status
                            except ApiException:
                                print('Unable to find order details, passing for now')
                            trade_to_exit.status = TradeStatus.CLOSING.value

                            # save the changes to the database
                            session.commit()
                    elif super_trend == 1.:
                        if client.get_flags().future == -1:
                            print('Buying future single')
                            client.get_flags().future = 0
                            # Buy Single to close
                            trade_to_exit = client.get_trades().filter(
                                Trades.status == TradeStatus.LIVE.value,
                                Trades.strategy == Strategy.FUT_HEDGE.value
                            ).first()

                            if trade_to_exit.trade_type == TransactionType.BUY.value:
                                close_trade_type = TransactionType.SELL
                            else:
                                close_trade_type = TransactionType.BUY

                            order = client.place_order(
                                quantity=trade_to_exit.quantity,
                                price=0,
                                tradingsymbol=trade_to_exit.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=close_trade_type
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            try:
                                order_details = client.order_api.get_order_details(
                                    api_version=API_VERSION, order_id=order_id
                                )
                                trade_to_exit.exit_status = order_details.data[-1].status
                                trade_to_exit.exit_order_id = order_id
                            except ApiException:
                                print('Unable to find order details, passing for now')
                            trade_to_exit.status = TradeStatus.CLOSING.value
                            # save the changes to the database
                            session.commit()

def weeks():
    global week0b, week1b, week2b, fromtime0, fromtime1, fromtime2, thursday, days_left, month0b, month1b, wednesday, wednesday2, week0n, week1n, fromtime0n, fromtime1n, days_leftn, shortweek, trend
    today = datetime.today().weekday()
    todayte = datetime.today()
    cmon = todayte.month
    thursday = 10 - today
    if thursday > 7:
        thursday -= 7
    wednesday = 9 - today
    if wednesday > 7:
        wednesday -= 7
    now = datetime.now()
    todate = datetime.today().date().day
    thursday1 = datetime.strftime(now, '%d/%m/%Y')
    thursday1 = datetime.strptime(thursday1, '%d/%m/%Y')
    thursday1 = thursday1 + relativedelta(days=thursday)
    wednesday1 = datetime.strftime(now, '%d/%m/%Y')
    wednesday1 = datetime.strptime(wednesday1, '%d/%m/%Y')
    wednesday1 = wednesday1 + relativedelta(days=wednesday)
    wednesday2 = wednesday1 + relativedelta(days=7)
    last_thursday = 1
    for i in range(1, 7):
        t = todayte + relativedelta(weekday=TH(i))
        if t.month != cmon:
            t = t + relativedelta(weekday=TH(-2))
            last_thursday = t.day
            print('last thurday of month is', last_thursday)
            break
    if last_thursday == wednesday1.day + 1:
        wednesday1 = wednesday1 + relativedelta(days=1)
    elif last_thursday == wednesday1.day - 6:
        print('Doing this on coming week after monthly expiry')
        # wednesday1 = wednesday1 - relativedelta(days=6)
    elif last_thursday == wednesday2.day + 1:
        wednesday2 = wednesday2 + relativedelta(days=1)
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
        wednesday0 = wednesday1 - relativedelta(days=6)
        if wednesday == 1 and shortweek == 1:
            print('Should do on short week')
            wednesday0 = wednesday1 - relativedelta(days=1)
            wednesday1 = wednesday1 + relativedelta(days=7)
        elif last_thursday == wednesday0.day:
            print('Should be doing on last week of the monthly expiry')
        else:
            if last_thursday == wednesday1.day:
                wednesday0 = wednesday1 - relativedelta(days=8)
            else:
                wednesday0 = wednesday1 - relativedelta(days=7)
            print('Today Banknifty weekly expiry')
        YY0 = wednesday0.year
        YY0 -= 2000
        MM0 = wednesday0.month
        DD0 = wednesday0.day
        print('Next week expiry date', DD1)
        print('Today expiry date', DD0)
        if DD1 != DD0 + 1:
            print('Bank Expiry today on', DD0)
            if DD0 < 10:
                DD0 = '0' + str(DD0)
        # else:
        #     DD0 = DD1
        #     wednesday0 = wednesday1-relativedelta(days=6)
    elif shortweek == 1:
        print('Next week Bank short week')
        wednesday1 = wednesday1 - relativedelta(days=1)
    elif shortweek == 2:
        wednesday2 = wednesday2 - relativedelta(days=1)
    YY1 = wednesday1.year
    YY1 -= 2000
    MM1 = wednesday1.month
    DD1 = wednesday1.day
    YY2 = wednesday2.year
    YY2 -= 2000
    MM2 = wednesday2.month
    DD2 = wednesday2.day
    if DD1 < 10:
        DD1 = '0' + str(DD1)
    print('Next Bank Expiry on', DD1)
    if DD2 < 10:
        DD2 = '0' + str(DD2)
    print('2weeks Bank Expiry on', DD2)
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
    elif shortweek == 2 and last_thursday - 1 != wednesday2.day:
        week2b = 'BANKNIFTY' + str(YY2) + str(MM2) + str(DD2)
        fromtime2 = datetime(YY2, MM2, int(DD2), 15, 30)
        print('Week2 Bank is', week2b)
    elif shortweek == 2 and last_thursday - 1 == wednesday2.day:
        if DD2 == last_thursday - 2 or DD2 == last_thursday - 1:
            MM2 = datetime.now().strftime('%h')
            week2b = 'BANKNIFTY' + str(YY2) + str(MM2.upper())
            fromtime2 = datetime(YY2, MM2, int(DD2), 15, 30)
            print('Week2 for Bank is', week2b)
    if wednesday == 6:
        thursday0 = thursday1 - relativedelta(days=7)
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
                MM1 = datetime.now().replace(month=MMM0 + 1)
                print(MM1)
            MM1 = MM1.strftime('%h')
            month1b = 'BANKNIFTY' + str(YY1) + str(MM1.upper())
    print(DD1)
    print(last_thursday)
    if DD1 == last_thursday:  # - 2 or DD1 == last_thursday - 1 or DD1 == last_thursday - 3 or DD1 == last_thursday - 6:
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
                    MM1 = datetime.now().replace(month=MM0 + 1)
                MM1 = MM1.strftime('%h')
                month1b = 'BANKNIFTY' + str(YY1) + str(MM1.upper())
    if datetime.now().strftime('%h') != thursday1.month:
        month1b = 'BANKNIFTY' + str(YY1) + str(thursday1.strftime('%h').upper())
    YY1 += 2000
    MM1 = thursday1.month
    DD1 = int(DD1)
    print(YY1, MM1, DD1)
    days_left = fromtime1 = datetime(YY1, MM1, 29, 15, 30)  # expiry date (YYYY, MM, DD, HR, MIN)
    if last_thursday != wednesday2.day:
        week2b = 'BANKNIFTY' + str(YY2) + str(MM2) + str(DD2)
        fromtime2 = datetime(YY2, MM2, int(DD2), 15, 30)
    else:
        week2b = 'BANKNIFTY' + str(YY2) + str(thursday1.strftime('%h').upper())
        fromtime2 = datetime(YY2, MM2, int(DD2), 15, 30)
    if wednesday == 7 or (wednesday == 1 and shortweek == 1):
        YY0 += 2000
        MM0 = wednesday0.month
        DD0 = int(DD0)
        fromtime0 = datetime(YY0, MM0, DD0, 15, 30)
        days_left = fromtime0
    # week1b = 'BANKNIFTY24430'
    print('Week2 Bank is', week2b)
    print('Week1 bank is', week1b)
    print('Month1 bank is', month1b)
    print('Time to expiry for bank0 is', days_left)
    if thursday == 7 or (thursday == 1 and shortweek == 1):
        if thursday == 1 and shortweek == 1:
            thursday0 = thursday1 - relativedelta(days=1)
            thursday1 = thursday1 + relativedelta(days=7)
        else:
            thursday0 = thursday1 - relativedelta(days=7)
        YY0 = thursday0.year
        YY0 -= 2000
        MM0 = thursday0.month
        DD0 = thursday0.day
        print('Expiry today on', DD0)
        if DD0 < 10:
            DD0 = '0' + str(DD0)
    elif shortweek == 1:
        thursday1 = thursday1 - relativedelta(days=1)
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
                    MM1 = datetime.now().replace(month=MM0 + 1)
                MM1 = MM1.strftime('%h')
                month1n = 'NIFTY' + str(YY1) + str(MM1.upper())
    if datetime.now().strftime('%h') != thursday1.month:
        month1n = 'NIFTY' + str(YY1) + str(thursday1.strftime('%h').upper())
    YY1 += 2000
    MM1 = thursday1.month
    DD1 = int(DD1)
    days_leftn = fromtime1n = datetime(YY1, MM1, DD1, 15, 30)  # expiry date (YYYY, MM, DD, HR, MIN)
    if thursday == 7 or (thursday == 1 and shortweek == 1):
        YY0 += 2000
        MM0 = thursday0.month
        DD0 = int(DD0)
        fromtime0n = datetime(YY0, MM0, DD0, 15, 30)
        days_leftn = fromtime0n

    print('Week1 for Nifty is', week1n)
    print('Month1 for Nifty is', month1n)
    print('Time to expiry for Nifty is', days_leftn)


    # data = yf.download("^NSEBANK", start=from_date, end=to_date, interval='5m')
    #
    # # Extract 5-minute interval OHLC data
    # ohlc_data = data[['Open', 'High', 'Low', 'Close']]

    api_instance = upstox_client.HistoryApi()
    instrument_key = 'NSE_FO|46923'  # str |
    interval = '1minute'  # str |
    api_version = '2.0'  # str | API Version Header

    try:
        intraday = api_instance.get_intra_day_candle_data(instrument_key, interval, api_version)
        historical = api_instance.get_historical_candle_data1(instrument_key, interval, todays_date, from_date,
                                                              api_version)
        ohlc_data = df(
            data=intraday.data.candles + historical.data.candles,
            index=[candle_data[0] for candle_data in intraday.data.candles] + [candle_data[0] for candle_data in
                                                                               historical.data.candles],
            columns=['TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'OI']
        )
        data = ohlc_data[['Open', 'High', 'Low', 'Close']][::-1]
        print(data)
        sti = ta.supertrend(data['High'], data['Low'], data['Close'], 10, 4)
        trend = sti['SUPERTd_10_4.0'].iloc[-1]
        print('Trend is', trend)
    except ApiException as e:
        print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)
        trend = 0


def price_strike(expiry: str, price, option):

    print('Inside price_strike')

    buff2 = 0
    strikebuff = 0
    if option.lower() == 'call':
        print('for new call')
        count = 0
        for strike in strike_ce:
            count += 1
            if count > 10:
                sleep(1)
                count = 0
            symbol = expiry + str(strike) + 'CE'
            try:
                ltp = get_ltp(symbol)
                print(ltp, 'is price for', symbol)
            except:
                print('Error in fetching price for', symbol)
                continue
            if price > ltp:
                buff1 = ltp
                if buff2 - price > price - buff1:
                    return strike, symbol
                else:
                    symbol = expiry + str(strikebuff) + 'CE'
                    strike = strikebuff
                    return strike, symbol
            else:
                buff2 = ltp
                strikebuff = strike
    elif option.lower() == 'put':
        print('for new put')
        for strike in strike_pe:
            symbol = expiry + str(strike) + 'PE'
            print(symbol)
            try:
                ltp = get_ltp(symbol)
                print(ltp, 'is price for', symbol)
            except:
                print('Error in fetching price for', symbol)
                continue
            if price > ltp:
                buff1 = ltp
                if buff2 - price > price - buff1:
                    print(symbol)
                    return strike, symbol
                else:
                    symbol = expiry + str(strikebuff) + 'PE'
                    strike = strikebuff
                    print(symbol)
                    return strike, symbol
            else:
                buff2 = ltp
                strikebuff = strike

def close_old_insurance():
    for client in active_clients:
        for current_trade in client.get_trades():
            if current_trade.status == TradeStatus.CLOSED.value:
                continue
            else:
                current_ltp = get_ltp(current_trade.symbol)
                print('LTP now is ', current_trade.ltp)
                if current_ltp <= 2 and current_trade.status == TradeStatus.LIVE.value:
                    if current_trade.rank in ('Call 1i', 'Put 1i'):
                        print('closing trade', current_trade.symbol, client)
                        rank = current_trade.rank.split()[0]
                        strike, symbol = price_strike(week1b, 8, rank)
                        new_trade = Trades()
                        new_trade.client_id = current_trade.client_id
                        new_trade.strategy = current_trade.strategy
                        if client.strategy.option_selling == 1:
                            new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                        else:
                            new_trade.quantity = client.strategy.fixed_profit * 15
                        new_trade.rank = current_trade.rank
                        new_trade.days_left = fromtime1
                        new_trade.trade_type = current_trade.trade_type
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0
                        new_trade.symbol = symbol
                        new_trade.ltp = get_ltp(symbol)
                        new_trade.order_id = randint(10, 99)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(symbol),
                                                                                   API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0][
                                                    'price']
                        try:
                            order = client.place_order(
                                quantity=new_trade.quantity,
                                price=0,
                                tradingsymbol=new_trade.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=TransactionType.BUY.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)
                        session.add(deepcopy(new_trade))

                        client.close_trade(current_trade)

                        # save the changes to the database
                        session.commit()

def fixed_profit_entry(week1b: str) -> None:
    """Fixed profit entry strategy"""
    print('Inside fixed Profit entry')

    # Properties common to all trades in fixed profit entry strategy
    new_trade = Trades()  # Create a new trade object
    new_trade.strategy = Strategy.FIXED_PROFIT.value
    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
    new_trade.days_left = fromtime1
    new_trade.date_time = datetime.now().time()
    new_trade.exit_price = -1
    new_trade.exit_status = NOT_APPLICABLE
    new_trade.profit_loss = 0

    # Common for all clients
    if (wednesday == 1 or (wednesday == 2 and shortweek == 1)) and datetime.now().time() > time(11, 30):
        week1b = week2b

    _, put_symbol = price_strike(week1b, 60, PUT)
    _, call_symbol = price_strike(week1b, 60, CALL)

    print('call symbol is ', call_symbol)

    for client in active_clients:
        if client.strategy.option_selling == 1:
            client.get_flags().first_leg = 0
        elif client.strategy.option_selling == 2:
            client.get_flags().first_leg = 1
        new_trade.client_id = client.client_id
        if not client.strategy.fixed_profit:  # Fixed profit flag should be non zero
            continue
        new_trade.quantity = client.strategy.fixed_profit * 15

        # Proceed if client has no open order in fixed profit strategy
        proceed = not client.get_trades().filter(
            Trades.strategy == Strategy.FIXED_PROFIT.value,
            Trades.status == TradeStatus.LIVE.value
        ).all()

        # If fixed profit and bank nifty flags are enabled for the client
        if client.strategy.bank_nifty and proceed:

            if client.get_flags().first_leg == 1:
                # Buying insurance 'CALL'
                strike, symbol = price_strike(week1b, 11, 'Call')

                new_trade.client_id = client.client_id
                if client.strategy.option_selling == 2:
                    new_trade.quantity = client.strategy.fixed_profit * 15
                else:
                    new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                new_trade.rank = 'Call 1i'
                new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                new_trade.date_time = datetime.now().time()
                new_trade.symbol = symbol
                new_trade.trade_type = TransactionType.BUY.value
                new_trade.ltp = get_ltp(symbol)
                parameters = client.market_quote_api.get_full_market_quote(get_token(symbol), API_VERSION).to_dict()
                new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0]['price'] - 0.05
                try:
                    order = client.place_order(
                        quantity=new_trade.quantity,
                        price=0,
                        tradingsymbol=new_trade.symbol,
                        order_type=OrderType.MARKET,
                        transaction_type=TransactionType.BUY.value
                    )
                    order_id = order['data']['order_id']  # Extract the order_id
                    new_trade.order_id = order_id
                except ApiException as e:
                    print("Exception when calling OrderApi->place_order: %s\n" % e)

                # Use deepcopy to add the current state of new trade to Trades Table
                session.add(deepcopy(new_trade))

                # save the changes to the database
                session.commit()

                # Buying insurance PUT
                strike, symbol = price_strike(week1b, 11, 'Put')
                new_trade.rank = 'Put 1i'
                new_trade.symbol = symbol
                new_trade.ltp = new_trade.entry_price = get_ltp(symbol)
                try:
                    order = client.place_order(
                        quantity=new_trade.quantity,
                        price=0,
                        tradingsymbol=new_trade.symbol,
                        order_type=OrderType.MARKET,
                        transaction_type=TransactionType.BUY.value
                    )
                    order_id = order['data']['order_id']  # Extract the order_id
                    new_trade.order_id = order_id
                except ApiException as e:
                    print("Exception when calling OrderApi->place_order: %s\n" % e)

                # Use deepcopy to add the current state of new trade to Trades Table
                session.add(deepcopy(new_trade))

                # save the changes to the database
                session.commit()


            # For Call
            new_trade.trade_type = TransactionType.SELL.value
            new_trade.order_id = randint(10, 99)
            if client.strategy.option_selling == 2:
                new_trade.rank = 'Call 1'
            else:
                new_trade.rank = 'Call 0'
            parameters = client.market_quote_api.get_full_market_quote(get_token(call_symbol), API_VERSION).to_dict()
            new_trade.entry_price = parameters['data'][get_symbol(call_symbol)]['depth']['sell'][0]['price'] - 0.05
            try:
                order = client.place_order(
                    quantity=new_trade.quantity,
                    price=new_trade.entry_price,
                    product=Product.DELIVERY,
                    tradingsymbol=call_symbol,
                    order_type=OrderType.LIMIT,
                    transaction_type=TransactionType.SELL.value
                )
                order_id = order['data']['order_id']  # Extract the order_id
                new_trade.order_id = order_id
            except ApiException as e:
                print("Exception when calling OrderApi->place_order: %s\n" % e)

            new_trade.symbol = call_symbol
            new_trade.ltp = get_ltp(call_symbol)

            # Use deepcopy to add the current state of new trade to Trades Table
            session.add(deepcopy(new_trade))

            # For Put

            new_trade.order_id = randint(10, 99)
            if client.strategy.option_selling == 2:
                new_trade.rank = 'Put 1'
            else:
                new_trade.rank = 'Put 0'
            parameters = client.market_quote_api.get_full_market_quote(get_token(put_symbol), API_VERSION).to_dict()
            new_trade.entry_price = parameters['data'][get_symbol(put_symbol)]['depth']['sell'][0]['price'] - 0.05
            try:
                order = client.place_order(
                    quantity=new_trade.quantity,
                    price=new_trade.entry_price,
                    product=Product.DELIVERY,
                    tradingsymbol=put_symbol,
                    order_type=OrderType.LIMIT,
                    transaction_type=TransactionType.SELL.value
                )
                order_id = order['data']['order_id']  # Extract the order_id
                new_trade.order_id = order_id
            except ApiException as e:
                print("Exception when calling OrderApi->place_order: %s\n" % e)

            new_trade.symbol = put_symbol
            new_trade.ltp = get_ltp(put_symbol)

            # Use deepcopy to add the current state of new trade to Trades Table
            session.add(deepcopy(new_trade))

            # save the changes to the database
            session.commit()


def next_expiry(client, current_trade) -> None:
    global week2b, week1b
    print('Executing next week trade')
    # client.close_trade(current_trade)
    if 'week0b' in globals():
        next_week = week1b
        days_left = fromtime1
    else:
        next_week = week2b
        days_left = fromtime2

    rank = current_trade.rank.split()[0]
    if client.strategy.option_selling == 1:
        client.get_flags().first_leg = 0
    new_trade = Trades()  # Create a new trade object
    new_trade.strategy = Strategy.FIXED_PROFIT.value
    new_trade.trade_type = TransactionType.SELL.value
    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
    new_trade.days_left = days_left
    new_trade.date_time = datetime.now().time()
    new_trade.exit_price = -1
    new_trade.exit_status = NOT_APPLICABLE
    new_trade.profit_loss = 0

    # Common for all clients
    _, symbol = price_strike(next_week, 60, rank)

    new_trade.client_id = client.client_id
    new_trade.quantity = client.strategy.fixed_profit * 15

    # Proceed if client has an open order in fixed profit strategy
    # proceed = not client.get_trades().filter(
    #     Trades.strategy == Strategy.FIXED_PROFIT.value,
    #     Trades.status != TradeStatus.LIVE.value
    # ).all()

    # If fixed profit and bank nifty flags are enabled for the client
    if client.strategy.fixed_profit and client.strategy.bank_nifty:

        # For Call
        new_trade.order_id = randint(10, 99)
        new_trade.rank = rank +' 1'
        parameters = client.market_quote_api.get_full_market_quote(
            get_token(symbol), API_VERSION
        ).to_dict()
        new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0]['price'] - 0.05
        try:
            order = client.place_order(
                quantity=new_trade.quantity,
                price=new_trade.entry_price,
                tradingsymbol=symbol,
                order_type=OrderType.LIMIT,
                transaction_type=TransactionType.SELL.value
            )
            order_id = order['data']['order_id']  # Extract the order_id
            new_trade.order_id = order_id
        except ApiException as e:
            print("Exception when calling OrderApi->place_order: %s\n" % e)

        new_trade.symbol = symbol
        new_trade.ltp = get_ltp(symbol)

        # Use deepcopy to add the current state of new trade to Trades Table
        session.add(deepcopy(new_trade))

        session.commit()

def stop_loss_entry(client: Client, current_trade: Trades):
    tradingsymbol = current_trade.symbol
    current_ltp = get_ltp(tradingsymbol=tradingsymbol)
    if current_ltp < 119:
        try:
            order = client.place_order(
                quantity=current_trade.quantity,
                price=130.0,
                tradingsymbol=tradingsymbol,
                order_type=OrderType.STOPLOSS_LIMIT,
                trigger_price=121.0,
                transaction_type=TransactionType.BUY.value
            )
            current_trade.exit_order_id = order['data']['order_id']
            current_trade.status = TradeStatus.LIVED.value
            session.commit()
        except ApiException as e:
            print("Exception when calling OrderApi->place_order: %s\n" % e)

    
def stop_loss_exit(client: Client, current_trade: Trades):
    if current_trade.status == TradeStatus.LIVED:
        try:
            api_response = client.order_api.cancel_order(current_trade.order_id, API_VERSION)
            print(api_response)
            current_trade.status = TradeStatus.LIVE
            current_trade.exit_order_id = 'NA'
            session.commit()
        except ApiException as e:
            print("Exception when calling OrderApi->cancel_order: %s\n" % e)
        

def update() -> None:
    global week1b, week2b, trend
    """Update the Trades table"""
    if datetime.now().time() < time(9, 16) or datetime.now().time() > time(15, 30):
        print("Time out")
        return

    print("Refreshing data", datetime.now().time())
    for client in active_clients:
        for current_trade in client.get_trades():
            if current_trade.status == TradeStatus.CLOSED.value:
                continue
            else:
                current_ltp = get_ltp(current_trade.symbol)
                current_trade.ltp = current_ltp
            session.commit()
            print('LTP now is ', current_trade.ltp)
            if current_ltp == 0:
                print('LTP not found')
                continue
            elif current_ltp < 30 and (current_trade.status == TradeStatus.LIVE.value or current_trade.status == TradeStatus.LIVED.value):
                print('LTP below 30')
                # If rank of current trade is Call 1 or Put 1
                if current_trade.rank in ('Call 1', 'Put 1'):
                    if current_trade.status == TradeStatus.LIVED.value:
                        stop_loss_exit(client, current_trade)
                    if ((wednesday == 1 and shortweek == 0) or (wednesday == 2 and shortweek == 1)) and datetime.now().time() > time(11, 30):
                        week1b = week2b
                    print('Selling to be changed', current_trade.symbol)
                    print(current_trade.rank)
                    # Filter out all the live trades with ranks ending with an `i`
                    insurance_trade = client.get_trades().filter(
                        Trades.rank == current_trade.rank + 'i',
                        Trades.status == TradeStatus.LIVE.value
                    ).first()

                    # If there is no insurance trade
                    if not insurance_trade:
                        print('No insurance trade')
                        # Continue to the next iteration
                        continue

                    if insurance_trade.ltp < 7:
                        rank = insurance_trade.rank.split()[0]
                        strike, symbol = price_strike(week1b, 8, rank)

                        if strike != int(insurance_trade.symbol[-7:-2]):
                            new_trade = Trades()
                            new_trade.client_id = insurance_trade.client_id
                            new_trade.strategy = insurance_trade.strategy
                            if client.strategy.option_selling == 1:
                                new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                            else:
                                new_trade.quantity = client.strategy.fixed_profit * 15
                            new_trade.rank = insurance_trade.rank
                            new_trade.days_left = insurance_trade.days_left
                            new_trade.trade_type = insurance_trade.trade_type
                            new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                            new_trade.date_time = datetime.now().time()
                            new_trade.exit_price = -1
                            new_trade.exit_status = NOT_APPLICABLE
                            new_trade.profit_loss = 0
                            new_trade.symbol = symbol
                            new_trade.ltp = get_ltp(symbol)
                            new_trade.order_id = randint(10, 99)
                            parameters = client.market_quote_api.get_full_market_quote(get_token(symbol), API_VERSION).to_dict()
                            print(parameters['data'])
                            new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0]['price'] - 0.05                            
                            try:
                                order = client.place_order(
                                    quantity=new_trade.quantity,
                                    price=0,
                                    tradingsymbol=new_trade.symbol,
                                    order_type=OrderType.MARKET,
                                    transaction_type=TransactionType.BUY.value
                                )
                                order_id = order['data']['order_id']  # Extract the order_id
                                new_trade.order_id = order_id
                            except ApiException as e:
                                print("Exception when calling OrderApi->place_order: %s\n" % e)

                            # Use deepcopy to add the current state of new trade to Trades Table
                            session.add(deepcopy(new_trade))

                            client.close_trade(insurance_trade)

                            # save the changes to the database
                            session.commit()

                if current_trade.rank in ('Call 0', 'Put 0', 'Call 1', 'Put 1'):
                    current_trade.status = TradeStatus.CLOSING.value
                    rank = current_trade.rank.split()[0]
                    strike, symbol = price_strike(week1b, 50, rank)

                    client.close_trade(current_trade)
                    print(symbol)
                    if strike == int(current_trade.symbol[-7:-2]) or not (42 < get_ltp(symbol) < 60):
                        next_expiry(client, current_trade)
                    elif (wednesday == 1 or (wednesday == 2 and shortweek == 1)) and datetime.now().time() > time( 12, 30):
                        next_expiry(client, current_trade)
                    else:
                        # Duplicate the current trade
                        new_trade = Trades()
                        new_trade.client_id = current_trade.client_id
                        new_trade.strategy = current_trade.strategy
                        if current_trade.rank in ('Call 1', 'Put 1') and client.strategy.option_selling == 1:
                            new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                        else:
                            new_trade.quantity = client.strategy.fixed_profit * 15
                        new_trade.rank = current_trade.rank
                        new_trade.days_left = current_trade.days_left
                        new_trade.trade_type = current_trade.trade_type
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0


                        new_trade.order_id = randint(10, 99)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(symbol), API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0]['price'] - 0.05
                        try:
                            order = client.place_order(
                                quantity=new_trade.quantity,
                                price=new_trade.entry_price,
                                tradingsymbol=symbol,
                                order_type=OrderType.LIMIT,
                                transaction_type=TransactionType.SELL.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                        new_trade.symbol = symbol
                        new_trade.ltp = get_ltp(symbol)

                        # Use deepcopy to add the current state of new trade to Trades Table
                        session.add(deepcopy(new_trade))

                        # save the changes to the database
                        session.commit()
            elif current_ltp > 120 and (current_trade.status == TradeStatus.LIVE.value or current_trade.status == TradeStatus.LIVED.value) and current_trade.strategy == Strategy.FIXED_PROFIT.value:
                print("Current LTP is: ", current_ltp)
                print("Current LTP greater than 120")
                if ((wednesday == 1 and shortweek == 0) or (wednesday == 2 and shortweek == 1)) and datetime.now().time() > time(11, 30):
                    week1b = week2b
                if current_trade.rank in ('Call 0', 'Put 0'):
                    client.close_trade(current_trade)
                    current_trade.status = TradeStatus.CLOSING.value
                    rank = current_trade.rank.split()[0]
                    strike, symbol = price_strike(week1b, 8, rank)

                    # Buying insurance with quantity 2 times
                    new_trade = Trades()  # Makes a new row in the table
                    new_trade.client_id = current_trade.client_id
                    new_trade.strategy = current_trade.strategy
                    new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                    new_trade.rank = rank + ' 1i'
                    new_trade.days_left = current_trade.days_left
                    new_trade.trade_type = TransactionType.BUY.value
                    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                    new_trade.date_time = datetime.now().time()
                    new_trade.exit_price = -1
                    new_trade.exit_status = NOT_APPLICABLE
                    new_trade.profit_loss = 0
                    new_trade.symbol = symbol
                    new_trade.ltp = get_ltp(symbol)
                    new_trade.order_id = randint(10, 99)
                    parameters = client.market_quote_api.get_full_market_quote(get_token(symbol), API_VERSION).to_dict()
                    new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0]['price'] - 0.05
                    try:
                        order = client.place_order(
                            quantity=new_trade.quantity,
                            price=0,
                            tradingsymbol=new_trade.symbol,
                            order_type=OrderType.MARKET,
                            transaction_type=TransactionType.BUY.value
                        )
                        order_id = order['data']['order_id']  # Extract the order_id
                        new_trade.order_id = order_id
                    except ApiException as e:
                        print("Exception when calling OrderApi->place_order: %s\n" % e)

                    # Use deepcopy to add the current state of new trade to Trades Table
                    session.add(deepcopy(new_trade))

                    # save the changes to the database
                    session.commit()

                    # Sell with half ltp and quantity 2 times
                    strike, symbol = price_strike(
                        week1b,
                        current_trade.exit_price / 2,
                        rank
                    )

                    new_trade = Trades()  # Makes a new row in the table
                    new_trade.client_id = current_trade.client_id
                    new_trade.strategy = current_trade.strategy
                    new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                    new_trade.rank = rank + ' 1'
                    new_trade.days_left = current_trade.days_left
                    new_trade.trade_type = TransactionType.SELL.value
                    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                    new_trade.date_time = datetime.now().time()
                    new_trade.exit_price = -1
                    new_trade.exit_status = NOT_APPLICABLE
                    new_trade.profit_loss = 0
                    new_trade.symbol = symbol
                    new_trade.ltp = get_ltp(symbol)
                    new_trade.order_id = randint(10, 99)
                    parameters = client.market_quote_api.get_full_market_quote(get_token(symbol), API_VERSION).to_dict()
                    new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0]['price'] - 0.05
                    try:
                        order = client.place_order(
                            quantity=new_trade.quantity,
                            price=0,
                            tradingsymbol=new_trade.symbol,
                            order_type=OrderType.MARKET,
                            transaction_type=TransactionType.SELL.value
                        )
                        order_id = order['data']['order_id']  # Extract the order_id
                        new_trade.order_id = order_id
                    except ApiException as e:
                        print("Exception when calling OrderApi->place_order: %s\n" % e)

                    # Use deepcopy to add the current state of new trade to Trades Table
                    session.add(deepcopy(new_trade))

                    # save the changes to the database
                    session.commit()

                    # Buy insurance of opposite rank
                    if rank == 'Put':
                        rank = 'Call'
                    else:
                        rank = 'Put'

                    strike, symbol = price_strike(week1b, 8, rank)

                    # Buying insurance of opposite rank with quantity 2 times
                    new_trade = Trades()  # Makes a new row in the table
                    new_trade.client_id = current_trade.client_id
                    new_trade.strategy = current_trade.strategy
                    new_trade.quantity = 2 * client.strategy.fixed_profit * 15
                    new_trade.rank = rank + ' 1i'
                    new_trade.days_left = current_trade.days_left
                    new_trade.trade_type = TransactionType.BUY.value
                    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                    new_trade.date_time = datetime.now().time()
                    new_trade.exit_price = -1
                    new_trade.exit_status = NOT_APPLICABLE
                    new_trade.profit_loss = 0
                    new_trade.symbol = symbol
                    new_trade.ltp = get_ltp(symbol)
                    new_trade.order_id = randint(10, 99)
                    parameters = client.market_quote_api.get_full_market_quote(get_token(symbol),
                                                                               API_VERSION).to_dict()
                    new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0][
                                                'price'] - 0.05
                    try:
                        order = client.place_order(
                            quantity=new_trade.quantity,
                            price=0,
                            tradingsymbol=new_trade.symbol,
                            order_type=OrderType.MARKET,
                            transaction_type=TransactionType.BUY.value
                        )
                        order_id = order['data']['order_id']  # Extract the order_id
                        new_trade.order_id = order_id
                    except ApiException as e:
                        print("Exception when calling OrderApi->place_order: %s\n" % e)

                    # Use deepcopy to add the current state of new trade to Trades Table
                    session.add(deepcopy(new_trade))

                    # save the changes to the database
                    session.commit()

                    current_trade = client.get_trades().filter(
                        Trades.rank == rank + ' 0',
                        Trades.status == TradeStatus.LIVE.value
                    ).first()

                    # Selling opposite rank with 1 quantity
                    current_trade.symbol = client.get_trades().filter_by(rank=rank + ' 0', status='live').first().symbol
                    current_trade.rank = rank + ' 1'
                    new_quantity = 2 * client.strategy.fixed_profit * 15 - current_trade.quantity
                    current_trade.quantity = 2 * current_trade.quantity

                    try:
                        order = client.place_order(
                            quantity=new_quantity,
                            price=0,
                            tradingsymbol=current_trade.symbol,
                            order_type=OrderType.MARKET,
                            transaction_type=TransactionType.SELL.value
                        )
                        order_id = order['data']['order_id']
                        print(f'{datetime.now()}: {order_id} order checking1')  # Extract the order_id
                        order_details = client.order_api.get_order_details(
                            api_version=API_VERSION, order_id=order_id
                        )
                        price = order_details.data[-1].average_price
                        current_trade.entry_price = (price + current_trade.entry_price) / 2
                    except ApiException as e:
                        print("Exception when calling OrderApi->place_order: %s\n" % e)

                    client.get_flags().first_leg = 1

                    # save the changes to the database
                    session.commit()

                elif current_trade.rank in ('Call 1', 'Put 1'):
                    if current_trade.status == TradeStatus.LIVED.value:
                        try:
                            order_details = client.order_api.get_order_details(
                                api_version=API_VERSION, order_id=current_trade.exit_order_id
                            )
                            current_trade.exit_status = order_details.data[-1].status
                            current_trade.exit_price = order_details.data[-1].average_price
                        except:
                            print("Order Id not found, skipping")
                            current_trade.exit_price = 0
                        if current_trade.exit_status == TradeStatus.COMPLETE.value:
                            current_trade.status = TradeStatus.CLOSED.value
                            # current_trade.entry_status = TradeStatus.COMPLETE.value
                            if current_trade.trade_type == TransactionType.SELL.value:
                                current_trade.profit_loss = round(current_trade.entry_price - current_trade.exit_price, 2) * current_trade.quantity
                            else:
                                current_trade.profit_loss = round(current_trade.exit_price - current_trade.entry_price, 2) * current_trade.quantity
                        elif current_trade.exit_status == TradeStatus.REJECTED.value:
                            current_trade.exit_status = TradeStatus.REJECTED.value
                            current_trade.status = TradeStatus.NOT_CLOSED.value
                            client.close_trade(current_trade)
                        elif current_trade.exit_status == TradeStatus.OPEN_PENDGING.value:
                            order_details = client.order_api.get_order_details(
                                api_version=API_VERSION, order_id=current_trade.exit_order_id
                            )
                            if order_details.data[-1].status != TradeStatus.COMPLETE.value:
                                body = upstox_client.ModifyOrderRequest(
                                    validity=Validity.DAY.value,
                                    price=0,
                                    order_id=current_trade.order_id,
                                    order_type=OrderType.MARKET.value,
                                    trigger_price=0
                                )
                                modified_order = client.order_api.modify_order(body=body, api_key=API_VERSION)
                                current_trade.exit_order_id = modified_order.data.order_id
                    else:
                        client.close_trade(current_trade)
                    rank = current_trade.rank.split()[0]
                    strike, symbol = price_strike(week1b, 100, rank)
                    print('New symbol is', symbol)


                    if strike == int(current_trade.symbol[-7:-2]) or not (85 < get_ltp(symbol) < 110):
                        insurance_trade = client.get_trades().filter(
                            Trades.rank == current_trade.rank + 'i',
                            Trades.status == TradeStatus.LIVE.value
                        ).first()

                        client.close_trade(insurance_trade)
                        next_expiry(client, current_trade)
                    else:
                        # Duplicate the current trade
                        new_trade = Trades()
                        new_trade.client_id = current_trade.client_id
                        new_trade.strategy = current_trade.strategy
                        new_trade.quantity = current_trade.quantity
                        new_trade.rank = current_trade.rank
                        new_trade.days_left = current_trade.days_left
                        new_trade.trade_type = current_trade.trade_type
                        new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                        new_trade.date_time = datetime.now().time()
                        new_trade.exit_price = -1
                        new_trade.exit_status = NOT_APPLICABLE
                        new_trade.profit_loss = 0

                        new_trade.order_id = randint(10, 99)
                        parameters = client.market_quote_api.get_full_market_quote(get_token(symbol),
                                                                                   API_VERSION).to_dict()
                        new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0][
                                                    'price'] - 0.05
                        try:
                            order = client.place_order(
                                quantity=new_trade.quantity,
                                price=new_trade.entry_price,
                                tradingsymbol=symbol,
                                order_type=OrderType.LIMIT,
                                transaction_type=TransactionType.SELL.value
                            )
                            order_id = order['data']['order_id']  # Extract the order_id
                            new_trade.order_id = order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                        new_trade.symbol = symbol
                        new_trade.ltp = get_ltp(symbol)

                        # Use deepcopy to add the current state of new trade to Trades Table
                        session.add(deepcopy(new_trade))

                        # save the changes to the database
                        session.commit()

            elif (current_ltp > 100 and current_trade.status == TradeStatus.LIVE.value or current_trade.status == TradeStatus.LIVED.value) and current_trade.strategy == Strategy.FIXED_PROFIT.value:
                flags = session.query(Flags).filter_by(client_id=client.client_id).one()
                if flags.optionbuy == 0 and client.strategy.optionbuy > 0:
                    print("Executing optionbuy for client", client.client_id)
                    optionbuy(client, current_trade.symbol)
                if current_trade.status == TradeStatus.LIVE.value:
                    stop_loss_entry(client, current_trade)
                else:
                    try:
                        order_details = client.order_api.get_order_details(
                            api_version=API_VERSION, order_id=current_trade.exit_order_id
                        )
                        current_trade.exit_status = order_details.data[-1].status
                        current_trade.exit_price = order_details.data[-1].average_price
                    except:
                        print("Order Id not found, skipping")
                        current_trade.exit_price = 0
                    if current_trade.exit_status == TradeStatus.COMPLETE.value:
                        current_trade.status = TradeStatus.CLOSED.value
                        # current_trade.entry_status = TradeStatus.COMPLETE.value
                        if current_trade.trade_type == TransactionType.SELL.value:
                            current_trade.profit_loss = round(current_trade.entry_price - current_trade.exit_price, 2) * current_trade.quantity
                        else:
                            current_trade.profit_loss = round(current_trade.exit_price - current_trade.entry_price, 2) * current_trade.quantity
                        rank = current_trade.rank.split()[0]
                        strike, symbol = price_strike(week1b, 100, rank)
                        print('New symbol is', symbol)


                        if strike == int(current_trade.symbol[-7:-2]) or not (85 < get_ltp(symbol) < 110):
                            insurance_trade = client.get_trades().filter(
                                Trades.rank == current_trade.rank + 'i',
                                Trades.status == TradeStatus.LIVE.value
                            ).first()

                            client.close_trade(insurance_trade)
                            next_expiry(client, current_trade)
                        else:
                            # Duplicate the current trade
                            new_trade = Trades()
                            new_trade.client_id = current_trade.client_id
                            new_trade.strategy = current_trade.strategy
                            new_trade.quantity = current_trade.quantity
                            new_trade.rank = current_trade.rank
                            new_trade.days_left = current_trade.days_left
                            new_trade.trade_type = current_trade.trade_type
                            new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                            new_trade.date_time = datetime.now().time()
                            new_trade.exit_price = -1
                            new_trade.exit_status = NOT_APPLICABLE
                            new_trade.profit_loss = 0

                            new_trade.order_id = randint(10, 99)
                            parameters = client.market_quote_api.get_full_market_quote(get_token(symbol),
                                                                                    API_VERSION).to_dict()
                            new_trade.entry_price = parameters['data'][f"NSE_FO:{symbol}"]['depth']['sell'][0][
                                                        'price'] - 0.05
                            try:
                                order = client.place_order(
                                    quantity=new_trade.quantity,
                                    price=new_trade.entry_price,
                                    tradingsymbol=symbol,
                                    order_type=OrderType.LIMIT,
                                    transaction_type=TransactionType.SELL.value
                                )
                                order_id = order['data']['order_id']  # Extract the order_id
                                new_trade.order_id = order_id
                            except ApiException as e:
                                print("Exception when calling OrderApi->place_order: %s\n" % e)

                            new_trade.symbol = symbol
                            new_trade.ltp = get_ltp(symbol)

                            # Use deepcopy to add the current state of new trade to Trades Table
                            session.add(deepcopy(new_trade))

                            # save the changes to the database
                            session.commit()

                print('Trend is', trend)
                if current_trade.rank.split()[0] == 'Call' and trend == 1 and client.get_flags().future < 1 and client.strategy.futures != 0:
                    new_trade = Trades()  # Create a new trade object
                    if client.get_flags().future == -1:
                        new_trade.quantity = client.strategy.futures * 15
                        qty = client.strategy.futures * 15 * 2
                        trade_to_close = client.get_trades().filter_by(
                            status=TradeStatus.LIVE.value,
                            strategy=Strategy.FUT_HEDGE.value
                        ).first()

                        trade_to_close.status = TradeStatus.CLOSING.value
                    elif client.get_flags().future == 0:
                        new_trade.quantity = qty = client.strategy.futures * 15
                    elif client.get_flags().future == 1:
                        continue

                    new_trade.strategy = Strategy.FUT_HEDGE.value
                    new_trade.trade_type = TransactionType.BUY.value
                    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                    new_trade.days_left = fromtime1
                    new_trade.date_time = datetime.now().time()
                    new_trade.exit_price = -1
                    new_trade.exit_status = NOT_APPLICABLE
                    new_trade.profit_loss = 0
                    new_trade.client_id = client.client_id
                    new_trade.symbol = month1b + 'FUT'
                    new_trade.rank = 'Trend'
                    parameters = client.market_quote_api.get_full_market_quote(
                        get_token(new_trade.symbol), API_VERSION
                    ).to_dict()
                    new_trade.entry_price = parameters['data'][get_symbol(new_trade.symbol)]['depth']['sell'][0]['price'] - 0.05
                    try:
                        order = client.place_order(
                            quantity=qty,
                            price=new_trade.entry_price,
                            product=Product.DELIVERY,
                            tradingsymbol=new_trade.symbol,
                            order_type=OrderType.LIMIT,
                            transaction_type=TransactionType.BUY.value
                        )
                        order_id = order['data']['order_id']  # Extract the order_id
                        new_trade.order_id = order_id
                    except ApiException as e:
                        print("Exception when calling OrderApi->place_order: %s\n" % e)
                    new_trade.ltp = get_ltp(current_trade.symbol)
                    if client.get_flags().future == -1:
                        trade_to_close.exit_order_id = order_id
                    client.get_flags().future = 1

                    # Use deepcopy to add the current state of new trade to Trades Table
                    session.add(deepcopy(new_trade))

                    session.commit()
                elif current_trade.rank.split()[0] == 'Put' and trend == -1 and client.get_flags().future > -1 and client.strategy.futures != 0:
                    new_trade = Trades()  # Create a new trade object
                    print('Future is', client.get_flags().future)
                    if client.get_flags().future == 1:
                        new_trade.quantity = client.strategy.futures * 15
                        qty = client.strategy.futures * 15 * 2
                        trade_to_close = client.get_trades().filter_by(
                            status=TradeStatus.LIVE.value,
                            strategy=Strategy.FUT_HEDGE.value
                        ).first()
                    elif client.get_flags().future == 0:
                        new_trade.quantity = qty = client.strategy.futures * 15
                    elif client.get_flags().future == -1:
                        continue

                    new_trade.strategy = Strategy.FUT_HEDGE.value
                    new_trade.trade_type = TransactionType.SELL.value
                    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
                    new_trade.days_left = fromtime1
                    new_trade.date_time = datetime.now().time()
                    new_trade.exit_price = -1
                    new_trade.exit_status = NOT_APPLICABLE
                    new_trade.profit_loss = 0
                    new_trade.client_id = client.client_id
                    new_trade.symbol = month1b + 'FUT'
                    new_trade.rank = 'Trend'
                    parameters = client.market_quote_api.get_full_market_quote(
                        get_token(new_trade.symbol), API_VERSION
                    ).to_dict()
                    new_trade.entry_price = parameters['data'][get_symbol(new_trade.symbol)]['depth']['sell'][0]['price'] - 0.05
                    try:
                        order = client.place_order(
                            quantity=qty,
                            price=new_trade.entry_price,
                            product=Product.DELIVERY,
                            tradingsymbol=new_trade.symbol,
                            order_type=OrderType.LIMIT,
                            transaction_type=TransactionType.SELL.value
                        )
                        order_id = order['data']['order_id']  # Extract the order_id
                        new_trade.order_id = order_id
                    except ApiException as e:
                        print("Exception when calling OrderApi->place_order: %s\n" % e)

                    new_trade.ltp = get_ltp(current_trade.symbol)
                    if client.get_flags().future == 1:
                        trade_to_close.exit_order_id = order_id
                    client.get_flags().future = -1
                    # Use deepcopy to add the current state of new trade to Trades Table
                    session.add(deepcopy(new_trade))

                    session.commit()
            elif current_ltp < 90 and (current_trade.status == TradeStatus.LIVE.value or current_trade.status == TradeStatus.LIVED.value) and current_trade.strategy == Strategy.FIXED_PROFIT.value:
                print("Symbol is", current_trade.symbol)
                flags = session.query(Flags).filter_by(client_id=client.client_id).one()
                print("Client is", client.client_id, "Strategy is", client.strategy.optionbuy)
                if flags.optionbuy != 0 and client.strategy.optionbuy > 0:
                    try:
                        print("optionbuy is", flags.optionbuy, "and rank is", current_trade.rank, "symbol is", current_trade.symbol)
                        if (flags.optionbuy == 1 and current_trade.rank == 'Call 1') or (flags.optionbuy == -1 and current_trade.rank == 'Put 1'):
                            print("ghx")
                            flags.optionbuy = 0
                            trade_to_close = client.get_trades().filter_by(
                                strategy=Strategy.OPTIONBUY.value,
                                status=TradeStatus.LIVE.value
                            ).first()
                            client.close_trade(trade_to_close)
                            session.commit()
                    except Exception as e:
                        print(e)
            elif current_trade.status == TradeStatus.ORDERED.value:
                print('Updating new orders')
                print("Order details for", current_trade.order_id)
                order_details = client.order_api.get_order_details(
                    api_version=API_VERSION, order_id=current_trade.order_id
                )
                current_trade.entry_status = order_details.data[-1].status

                if current_trade.entry_status == TradeStatus.COMPLETE.value:
                    current_trade.status = TradeStatus.LIVE.value
                    current_trade.entry_status = TradeStatus.COMPLETE.value
                    current_trade.entry_price = order_details.data[-1].average_price
                elif current_trade.entry_status == TradeStatus.REJECTED.value:
                    current_trade.status = current_trade.entry_status = TradeStatus.REJECTED.value
                elif current_trade.entry_status == TradeStatus.OPEN.value:
                    parameters = client.market_quote_api.get_full_market_quote(
                        get_token(current_trade.symbol), API_VERSION
                    ).to_dict()
                    current_trade.entry_price = parameters['data'][get_symbol(current_trade.symbol)]['depth']['sell'][0]['price'] - 0.05
                    body = upstox_client.ModifyOrderRequest(
                        validity=Validity.DAY.value,
                        price=current_trade.entry_price,
                        order_id=current_trade.order_id,
                        order_type=OrderType.LIMIT.value,
                        trigger_price=0
                    )
                    modified_order = client.order_api.modify_order(body=body, api_version=API_VERSION)
                    current_trade.order_id = modified_order.data.order_id  # if not working, use ['order_id']
                elif current_trade.entry_status == TradeStatus.CANCELLED.value:
                    order_details = client.order_api.get_order_details(
                        api_version=API_VERSION, order_id=current_trade.order_id
                    )
                    traded = order_details.data[-1].quantity
                    print(traded, 'qty traded before cancel')
                    if traded > 0:
                        try:
                            order = client.place_order(
                                quantity=current_trade.quantity - traded,
                                price=0,
                                product=Product.DELIVERY,
                                tradingsymbol=current_trade.symbol,
                                order_type=OrderType.MARKET,
                                transaction_type=current_trade.trade_type
                            )
                            current_trade.order_id = order['data']['order_id']  # Extract the order_id
                        except ApiException as e:
                            print("Exception when calling OrderApi->place_order: %s\n" % e)

                session.commit()
            elif current_trade.exit_status == TradeStatus.ORDERED.value:
                print('Exit status is {}'.format(current_trade))
                order_details = client.order_api.get_order_details(
                    api_version=API_VERSION, order_id=current_trade.exit_order_id
                )
                current_trade.exit_status = order_details.data[-1].status

                if current_trade.exit_status == TradeStatus.COMPLETE.value:
                    current_trade.status = 'CLOSED'
                    current_trade.entry_status = TradeStatus.COMPLETE.value
                    current_trade.exit_price = order_details.data[-1].average_price
                    if current_trade.trade_type == 'BUY':
                        current_trade.profit_loss = round((current_trade.exit_price - current_trade.entry_price), 2) * current_trade.quantity
                    else:
                        current_trade.profit_loss = round((current_trade.entry_price - current_trade.exit_price), 2) * current_trade.quantity
                elif current_trade.exit_status == TradeStatus.REJECTED.value:
                    current_trade.status = 'Manually Close'
                session.commit()
            elif current_trade.status == TradeStatus.CLOSING.value:
                print('Updating closing orders')
                try:
                    order_details = client.order_api.get_order_details(
                        api_version=API_VERSION, order_id=current_trade.exit_order_id
                    )
                    current_trade.exit_status = order_details.data[-1].status
                    current_trade.exit_price = order_details.data[-1].average_price
                except:
                    print("Order Id not found, skipping")
                    current_trade.exit_price = 0
                if current_trade.exit_status == TradeStatus.COMPLETE.value:
                    current_trade.status = TradeStatus.CLOSED.value
                    # current_trade.entry_status = TradeStatus.COMPLETE.value
                    if current_trade.trade_type == TransactionType.SELL.value:
                        current_trade.profit_loss = round(current_trade.entry_price - current_trade.exit_price, 2) * current_trade.quantity
                    else:
                        current_trade.profit_loss = round(current_trade.exit_price - current_trade.entry_price, 2) * current_trade.quantity

                elif current_trade.exit_status == TradeStatus.REJECTED.value:
                    current_trade.status = TradeStatus.NOT_CLOSED.value
                elif current_trade.exit_status == TradeStatus.OPEN_PENDGING.value:
                    order_details = client.order_api.get_order_details(
                        api_version=API_VERSION, order_id=current_trade.exit_order_id
                    )
                    if order_details.data[-1].status != TradeStatus.COMPLETE.value:
                        body = upstox_client.ModifyOrderRequest(
                            validity=Validity.DAY.value,
                            price=0,
                            order_id=current_trade.order_id,
                            order_type=OrderType.MARKET.value,
                            trigger_price=0
                        )
                        modified_order = client.order_api.modify_order(body=body, api_key=API_VERSION)
                        current_trade.exit_order_id = modified_order.data.order_id  # if not working, use ['order_id']
                    else:
                        current_trade.exit_status = TradeStatus.COMPLETE.value
                        current_trade.status = TradeStatus.CLOSED.value
                        if current_trade.trade_type == TransactionType.SELL.value:
                            current_trade.profit_loss = round(current_trade.entry_price - current_trade.exit_price,
                                                              2) * current_trade.quantity
                        else:
                            current_trade.profit_loss = round(current_trade.exit_price - current_trade.entry_price,
                                                              2) * current_trade.quantity
                session.commit()
            if current_trade.trade_type == TransactionType.SELL.value and current_trade.status == TradeStatus.LIVE.value:
                current_trade.profit_loss = round(current_trade.entry_price - current_trade.ltp, 2) * current_trade.quantity
            elif current_trade.trade_type == TransactionType.BUY.value and current_trade.status == TradeStatus.LIVE.value:
                current_trade.profit_loss = round(current_trade.ltp - current_trade.entry_price, 2) * current_trade.quantity
            if current_trade.status == TradeStatus.LIVE.value and current_trade.rank == 'trending':
                api_instance = upstox_client.HistoryApi()
                instrument_key = get_token(current_trade.symbol) # str |
                interval = '1minute'  # str |
                api_version = '2.0'  # str | API Version Header

                try:
                    intraday = api_instance.get_intra_day_candle_data(instrument_key, interval, api_version)
                    print("Intrday successful")
                    historical = api_instance.get_historical_candle_data1(instrument_key, interval, todays_date, from_date, api_version)
                    print("historical + intraday successful")
                    ohlc_data = df(
                        data=intraday.data.candles + historical.data.candles,
                        index=[candle_data[0] for candle_data in intraday.data.candles] + [candle_data[0] for candle_data in historical.data.candles],
                        columns=['TimeStamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'OI']
                    )
                    data = ohlc_data[['Open', 'High', 'Low', 'Close']][::-1]

                except ApiException as e:
                    print("Exception when calling HistoryApi->get_historical_candle_data: %s\n" % e)
                sti = ta.supertrend(data['High'], data['Low'], data['Close'], 10, 2)
                direction = sti['SUPERTd_10_2.0'].iloc[-1]
                print('Direction is', direction)
                trend = direction
                if direction == -1:
                    client.close_trade(current_trade)
                    flags = session.query(Flags).filter_by(client_id=client.client_id).one()
                    flags.optionbuy = 0
                    session.commit()
        # session.query(Clients).filter_by(client_id=client.client_id).first()
        try:
            api_instance = upstox_client.UserApi(client.api_client)
            used_margin = api_instance.get_user_fund_margin(API_VERSION).data['equity'].used_margin
            available_margin = api_instance.get_user_fund_margin(API_VERSION).data['equity'].available_margin
            row = session.query(Clients).filter_by(client_id=client.client_id).first()
            total_sum = 0
            for record in upstox_client.PortfolioApi(client.api_client).get_positions(API_VERSION).data:
                if record.unrealised != '':
                    total_sum += record.unrealised
                if record.realised != '':
                    total_sum += record.realised

            row.m_to_m = total_sum
            row.used = used_margin
            row.available = available_margin
            if available_margin < 60000:
                print(f'Low margin in {client.client_id}, Rs. {available_margin}')
        except ApiException as e:
            print("Exception when calling UserApi->get_user_fund_margin or portfolio: %s\n" % e)
        session.commit()
        # api_instance = upstox_client.PortfolioApi(client.api_client)
        # for trade in api_instance.get_positions(API_VERSION).data:
        #     if trade.realised = '':
        #         client.get_trades().query()

def remove_SL():
    for client in active_clients:
        print('Removing SL')
        for current_trade in client.get_trades():
            if current_trade.status == TradeStatus.LIVED:
                stop_loss_exit(client, current_trade)

question = input('Do you want to start fresh or continue from where stopped?(F/C): ')

if question.lower() == 'c':

    question1 = input('Any short week? n for No, 1 for this week: ')
    if question1.lower() == 'n':
        shortweek = 0
    elif question1.lower() == '1':
        shortweek = 1
    elif question1.lower() == '2':
        shortweek = 2
    if time(9, 15) > datetime.now().time():
        for client in active_clients:
            try:
                flags = session.query(Flags).filter_by(client_id=client.client_id).one()
                flags.max_profit = flags.max_loss = 0
                print('Updated flags')
                session.commit()
            except NoResultFound:
                print(f"No flags found for Client: {client.client_id}")
    if time(0, 10) < datetime.now().time() < time(23, 35):
        weeks()

        def fixed_profit_entry_with_arguments():
            fixed_profit_entry(week1b)

        schedule.every(20).seconds.do(update)

        # schedule.every().day.at("09:15:01").do(close_future_hedge)
        # schedule.every().day.at("09:16:01").do(close_future_hedge)
        # schedule.every().day.at("09:17:01").do(close_future_hedge)
        # schedule.every().day.at("09:18:01").do(close_future_hedge)
        # schedule.every().day.at("09:19:01").do(close_future_hedge)
        # schedule.every().day.at("09:20:01").do(close_future_hedge)
        # schedule.every().day.at("09:21:01").do(close_future_hedge)
        # schedule.every().day.at("09:22:01").do(close_future_hedge)
        # schedule.every().day.at("09:23:01").do(close_future_hedge)
        # schedule.every().day.at("09:24:01").do(close_future_hedge)
        # schedule.every().day.at("09:25:01").do(close_future_hedge)
        # schedule.every().day.at("09:26:01").do(close_future_hedge)
        # schedule.every().day.at("09:27:01").do(close_future_hedge)
        # schedule.every().day.at("09:28:01").do(close_future_hedge)
        # schedule.every().day.at("09:29:01").do(close_future_hedge)
        # schedule.every().day.at("09:30:01").do(close_future_hedge)
        # schedule.every().day.at("09:31:01").do(close_future_hedge)
        # schedule.every().day.at("09:32:01").do(close_future_hedge)
        # schedule.every().day.at("09:33:01").do(close_future_hedge)
        # schedule.every().day.at("09:34:01").do(close_future_hedge)
        # schedule.every().day.at("09:35:01").do(close_future_hedge)
        # schedule.every().day.at("09:36:01").do(close_future_hedge)
        # schedule.every().day.at("09:37:01").do(close_future_hedge)
        # schedule.every().day.at("09:38:01").do(close_future_hedge)
        # schedule.every().day.at("09:39:01").do(close_future_hedge)
        # schedule.every().day.at("09:40:01").do(close_future_hedge)
        # schedule.every().day.at("09:41:01").do(close_future_hedge)
        # schedule.every().day.at("09:42:01").do(close_future_hedge)
        # schedule.every().day.at("09:43:01").do(close_future_hedge)
        # schedule.every().day.at("09:44:01").do(close_future_hedge)
        # schedule.every().day.at("09:45:01").do(close_future_hedge)
        # schedule.every().day.at("09:46:01").do(close_future_hedge)
        # schedule.every().day.at("09:47:01").do(close_future_hedge)
        # schedule.every().day.at("09:48:01").do(close_future_hedge)
        # schedule.every().day.at("09:49:01").do(close_future_hedge)
        # schedule.every().day.at("09:50:01").do(close_future_hedge)
        # schedule.every().day.at("09:51:01").do(close_future_hedge)
        # schedule.every().day.at("09:52:01").do(close_future_hedge)
        # schedule.every().day.at("09:53:01").do(close_future_hedge)
        # schedule.every().day.at("09:54:01").do(close_future_hedge)
        # schedule.every().day.at("09:55:01").do(close_future_hedge)
        # schedule.every().day.at("09:56:01").do(close_future_hedge)
        # schedule.every().day.at("09:57:01").do(close_future_hedge)
        # schedule.every().day.at("09:58:01").do(close_future_hedge)
        # schedule.every().day.at("09:59:01").do(close_future_hedge)
        # schedule.every().day.at("10:00:01").do(close_future_hedge)
        # schedule.every().day.at("10:01:01").do(close_future_hedge)
        # schedule.every().day.at("10:02:01").do(close_future_hedge)
        # schedule.every().day.at("10:03:01").do(close_future_hedge)
        # schedule.every().day.at("10:04:01").do(close_future_hedge)
        # schedule.every().day.at("10:05:01").do(close_future_hedge)
        # schedule.every().day.at("10:06:01").do(close_future_hedge)
        # schedule.every().day.at("10:07:01").do(close_future_hedge)
        # schedule.every().day.at("10:08:01").do(close_future_hedge)
        # schedule.every().day.at("10:09:01").do(close_future_hedge)
        # schedule.every().day.at("10:10:01").do(close_future_hedge)
        # schedule.every().day.at("10:11:01").do(close_future_hedge)
        # schedule.every().day.at("10:12:01").do(close_future_hedge)
        # schedule.every().day.at("10:13:01").do(close_future_hedge)
        # schedule.every().day.at("10:14:01").do(close_future_hedge)
        # schedule.every().day.at("10:15:01").do(close_future_hedge)
        # schedule.every().day.at("10:16:01").do(close_future_hedge)
        # schedule.every().day.at("10:17:01").do(close_future_hedge)
        # schedule.every().day.at("10:18:01").do(close_future_hedge)
        # schedule.every().day.at("10:19:01").do(close_future_hedge)
        # schedule.every().day.at("10:20:01").do(close_future_hedge)
        # schedule.every().day.at("10:21:01").do(close_future_hedge)
        # schedule.every().day.at("10:22:01").do(close_future_hedge)
        # schedule.every().day.at("10:23:01").do(close_future_hedge)
        # schedule.every().day.at("10:24:01").do(close_future_hedge)
        # schedule.every().day.at("10:25:01").do(close_future_hedge)
        # schedule.every().day.at("10:26:01").do(close_future_hedge)
        # schedule.every().day.at("10:27:01").do(close_future_hedge)
        # schedule.every().day.at("10:28:01").do(close_future_hedge)
        # schedule.every().day.at("10:29:01").do(close_future_hedge)
        # schedule.every().day.at("10:30:01").do(close_future_hedge)
        # schedule.every().day.at("10:31:01").do(close_future_hedge)
        # schedule.every().day.at("10:32:01").do(close_future_hedge)
        # schedule.every().day.at("10:33:01").do(close_future_hedge)
        # schedule.every().day.at("10:34:01").do(close_future_hedge)
        # schedule.every().day.at("10:35:01").do(close_future_hedge)
        # schedule.every().day.at("10:36:01").do(close_future_hedge)
        # schedule.every().day.at("10:37:01").do(close_future_hedge)
        # schedule.every().day.at("10:38:01").do(close_future_hedge)
        # schedule.every().day.at("10:39:01").do(close_future_hedge)
        # schedule.every().day.at("10:40:01").do(close_future_hedge)
        # schedule.every().day.at("10:41:01").do(close_future_hedge)
        # schedule.every().day.at("10:42:01").do(close_future_hedge)
        # schedule.every().day.at("10:43:01").do(close_future_hedge)
        # schedule.every().day.at("10:44:01").do(close_future_hedge)
        # schedule.every().day.at("10:45:01").do(close_future_hedge)
        # schedule.every().day.at("10:46:01").do(close_future_hedge)
        # schedule.every().day.at("10:47:01").do(close_future_hedge)
        # schedule.every().day.at("10:48:01").do(close_future_hedge)
        # schedule.every().day.at("10:49:01").do(close_future_hedge)
        # schedule.every().day.at("10:50:01").do(close_future_hedge)
        # schedule.every().day.at("10:51:01").do(close_future_hedge)
        # schedule.every().day.at("10:52:01").do(close_future_hedge)
        # schedule.every().day.at("10:53:01").do(close_future_hedge)
        # schedule.every().day.at("10:54:01").do(close_future_hedge)
        # schedule.every().day.at("10:55:01").do(close_future_hedge)
        # schedule.every().day.at("10:56:01").do(close_future_hedge)
        # schedule.every().day.at("10:57:01").do(close_future_hedge)
        # schedule.every().day.at("10:58:01").do(close_future_hedge)
        # schedule.every().day.at("10:59:01").do(close_future_hedge)
        # schedule.every().day.at("11:00:01").do(close_future_hedge)
        # schedule.every().day.at("11:01:01").do(close_future_hedge)
        # schedule.every().day.at("11:02:01").do(close_future_hedge)
        # schedule.every().day.at("11:03:01").do(close_future_hedge)
        # schedule.every().day.at("11:04:01").do(close_future_hedge)
        # schedule.every().day.at("11:05:01").do(close_future_hedge)
        # schedule.every().day.at("11:06:01").do(close_future_hedge)
        # schedule.every().day.at("11:07:01").do(close_future_hedge)
        # schedule.every().day.at("11:08:01").do(close_future_hedge)
        # schedule.every().day.at("11:09:01").do(close_future_hedge)
        # schedule.every().day.at("11:10:01").do(close_future_hedge)
        # schedule.every().day.at("11:11:01").do(close_future_hedge)
        # schedule.every().day.at("11:12:01").do(close_future_hedge)
        # schedule.every().day.at("11:13:01").do(close_future_hedge)
        # schedule.every().day.at("11:14:01").do(close_future_hedge)
        # schedule.every().day.at("11:15:01").do(close_future_hedge)
        # schedule.every().day.at("11:16:01").do(close_future_hedge)
        # schedule.every().day.at("11:17:01").do(close_future_hedge)
        # schedule.every().day.at("11:18:01").do(close_future_hedge)
        # schedule.every().day.at("11:19:01").do(close_future_hedge)
        # schedule.every().day.at("11:20:01").do(close_future_hedge)
        # schedule.every().day.at("11:21:01").do(close_future_hedge)
        # schedule.every().day.at("11:22:01").do(close_future_hedge)
        # schedule.every().day.at("11:23:01").do(close_future_hedge)
        # schedule.every().day.at("11:24:01").do(close_future_hedge)
        # schedule.every().day.at("11:25:01").do(close_future_hedge)
        # schedule.every().day.at("11:26:01").do(close_future_hedge)
        # schedule.every().day.at("11:27:01").do(close_future_hedge)
        # schedule.every().day.at("11:28:01").do(close_future_hedge)
        # schedule.every().day.at("11:29:01").do(close_future_hedge)
        # schedule.every().day.at("11:30:01").do(close_future_hedge)
        # schedule.every().day.at("11:31:01").do(close_future_hedge)
        # schedule.every().day.at("11:32:01").do(close_future_hedge)
        # schedule.every().day.at("11:33:01").do(close_future_hedge)
        # schedule.every().day.at("11:34:01").do(close_future_hedge)
        # schedule.every().day.at("11:35:01").do(close_future_hedge)
        # schedule.every().day.at("11:36:01").do(close_future_hedge)
        # schedule.every().day.at("11:37:01").do(close_future_hedge)
        # schedule.every().day.at("11:38:01").do(close_future_hedge)
        # schedule.every().day.at("11:39:01").do(close_future_hedge)
        # schedule.every().day.at("11:40:01").do(close_future_hedge)
        # schedule.every().day.at("11:41:01").do(close_future_hedge)
        # schedule.every().day.at("11:42:01").do(close_future_hedge)
        # schedule.every().day.at("11:43:01").do(close_future_hedge)
        # schedule.every().day.at("11:44:01").do(close_future_hedge)
        # schedule.every().day.at("11:45:01").do(close_future_hedge)
        # schedule.every().day.at("11:46:01").do(close_future_hedge)
        # schedule.every().day.at("11:47:01").do(close_future_hedge)
        # schedule.every().day.at("11:48:01").do(close_future_hedge)
        # schedule.every().day.at("11:49:01").do(close_future_hedge)
        # schedule.every().day.at("11:50:01").do(close_future_hedge)
        # schedule.every().day.at("11:51:01").do(close_future_hedge)
        # schedule.every().day.at("11:52:01").do(close_future_hedge)
        # schedule.every().day.at("11:53:01").do(close_future_hedge)
        # schedule.every().day.at("11:54:01").do(close_future_hedge)
        # schedule.every().day.at("11:55:01").do(close_future_hedge)
        # schedule.every().day.at("11:56:01").do(close_future_hedge)
        # schedule.every().day.at("11:57:01").do(close_future_hedge)
        # schedule.every().day.at("11:58:01").do(close_future_hedge)
        # schedule.every().day.at("11:59:01").do(close_future_hedge)
        # schedule.every().day.at("12:00:01").do(close_future_hedge)
        # schedule.every().day.at("12:01:01").do(close_future_hedge)
        # schedule.every().day.at("12:02:01").do(close_future_hedge)
        # schedule.every().day.at("12:03:01").do(close_future_hedge)
        # schedule.every().day.at("12:04:01").do(close_future_hedge)
        # schedule.every().day.at("12:05:01").do(close_future_hedge)
        # schedule.every().day.at("12:06:01").do(close_future_hedge)
        # schedule.every().day.at("12:07:01").do(close_future_hedge)
        # schedule.every().day.at("12:08:01").do(close_future_hedge)
        # schedule.every().day.at("12:09:01").do(close_future_hedge)
        # schedule.every().day.at("12:10:01").do(close_future_hedge)
        # schedule.every().day.at("12:11:01").do(close_future_hedge)
        # schedule.every().day.at("12:12:01").do(close_future_hedge)
        # schedule.every().day.at("12:13:01").do(close_future_hedge)
        # schedule.every().day.at("12:14:01").do(close_future_hedge)
        # schedule.every().day.at("12:15:01").do(close_future_hedge)
        # schedule.every().day.at("12:16:01").do(close_future_hedge)
        # schedule.every().day.at("12:17:01").do(close_future_hedge)
        # schedule.every().day.at("12:18:01").do(close_future_hedge)
        # schedule.every().day.at("12:19:01").do(close_future_hedge)
        # schedule.every().day.at("12:20:01").do(close_future_hedge)
        # schedule.every().day.at("12:21:01").do(close_future_hedge)
        # schedule.every().day.at("12:22:01").do(close_future_hedge)
        # schedule.every().day.at("12:23:01").do(close_future_hedge)
        # schedule.every().day.at("12:24:01").do(close_future_hedge)
        # schedule.every().day.at("12:25:01").do(close_future_hedge)
        # schedule.every().day.at("12:26:01").do(close_future_hedge)
        # schedule.every().day.at("12:27:01").do(close_future_hedge)
        # schedule.every().day.at("12:28:01").do(close_future_hedge)
        # schedule.every().day.at("12:29:01").do(close_future_hedge)
        # schedule.every().day.at("12:30:01").do(close_future_hedge)
        # schedule.every().day.at("12:31:01").do(close_future_hedge)
        # schedule.every().day.at("12:32:01").do(close_future_hedge)
        # schedule.every().day.at("12:33:01").do(close_future_hedge)
        # schedule.every().day.at("12:34:01").do(close_future_hedge)
        # schedule.every().day.at("12:35:01").do(close_future_hedge)
        # schedule.every().day.at("12:36:01").do(close_future_hedge)
        # schedule.every().day.at("12:37:01").do(close_future_hedge)
        # schedule.every().day.at("12:38:01").do(close_future_hedge)
        # schedule.every().day.at("12:39:01").do(close_future_hedge)
        # schedule.every().day.at("12:40:01").do(close_future_hedge)
        # schedule.every().day.at("12:41:01").do(close_future_hedge)
        # schedule.every().day.at("12:42:01").do(close_future_hedge)
        # schedule.every().day.at("12:43:01").do(close_future_hedge)
        # schedule.every().day.at("12:44:01").do(close_future_hedge)
        # schedule.every().day.at("12:45:01").do(close_future_hedge)
        # schedule.every().day.at("12:46:01").do(close_future_hedge)
        # schedule.every().day.at("12:47:01").do(close_future_hedge)
        # schedule.every().day.at("12:48:01").do(close_future_hedge)
        # schedule.every().day.at("12:49:01").do(close_future_hedge)
        # schedule.every().day.at("12:50:01").do(close_future_hedge)
        # schedule.every().day.at("12:51:01").do(close_future_hedge)
        # schedule.every().day.at("12:52:01").do(close_future_hedge)
        # schedule.every().day.at("12:53:01").do(close_future_hedge)
        # schedule.every().day.at("12:54:01").do(close_future_hedge)
        # schedule.every().day.at("12:55:01").do(close_future_hedge)
        # schedule.every().day.at("12:56:01").do(close_future_hedge)
        # schedule.every().day.at("12:57:01").do(close_future_hedge)
        # schedule.every().day.at("12:58:01").do(close_future_hedge)
        # schedule.every().day.at("12:59:01").do(close_future_hedge)
        # schedule.every().day.at("13:00:01").do(close_future_hedge)
        # schedule.every().day.at("13:01:01").do(close_future_hedge)
        # schedule.every().day.at("13:02:01").do(close_future_hedge)
        # schedule.every().day.at("13:03:01").do(close_future_hedge)
        # schedule.every().day.at("13:04:01").do(close_future_hedge)
        # schedule.every().day.at("13:05:01").do(close_future_hedge)
        # schedule.every().day.at("13:06:01").do(close_future_hedge)
        # schedule.every().day.at("13:07:01").do(close_future_hedge)
        # schedule.every().day.at("13:08:01").do(close_future_hedge)
        # schedule.every().day.at("13:09:01").do(close_future_hedge)
        # schedule.every().day.at("13:10:01").do(close_future_hedge)
        # schedule.every().day.at("13:11:01").do(close_future_hedge)
        # schedule.every().day.at("13:12:01").do(close_future_hedge)
        # schedule.every().day.at("13:13:01").do(close_future_hedge)
        # schedule.every().day.at("13:14:01").do(close_future_hedge)
        # schedule.every().day.at("13:15:01").do(close_future_hedge)
        # schedule.every().day.at("13:16:01").do(close_future_hedge)
        # schedule.every().day.at("13:17:01").do(close_future_hedge)
        # schedule.every().day.at("13:18:01").do(close_future_hedge)
        # schedule.every().day.at("13:19:01").do(close_future_hedge)
        # schedule.every().day.at("13:20:01").do(close_future_hedge)
        # schedule.every().day.at("13:21:01").do(close_future_hedge)
        # schedule.every().day.at("13:22:01").do(close_future_hedge)
        # schedule.every().day.at("13:23:01").do(close_future_hedge)
        # schedule.every().day.at("13:24:01").do(close_future_hedge)
        # schedule.every().day.at("13:25:01").do(close_future_hedge)
        # schedule.every().day.at("13:26:01").do(close_future_hedge)
        # schedule.every().day.at("13:27:01").do(close_future_hedge)
        # schedule.every().day.at("13:28:01").do(close_future_hedge)
        # schedule.every().day.at("13:29:01").do(close_future_hedge)
        # schedule.every().day.at("13:30:01").do(close_future_hedge)
        # schedule.every().day.at("13:31:01").do(close_future_hedge)
        # schedule.every().day.at("13:32:01").do(close_future_hedge)
        # schedule.every().day.at("13:33:01").do(close_future_hedge)
        # schedule.every().day.at("13:34:01").do(close_future_hedge)
        # schedule.every().day.at("13:35:01").do(close_future_hedge)
        # schedule.every().day.at("13:36:01").do(close_future_hedge)
        # schedule.every().day.at("13:37:01").do(close_future_hedge)
        # schedule.every().day.at("13:38:01").do(close_future_hedge)
        # schedule.every().day.at("13:39:01").do(close_future_hedge)
        # schedule.every().day.at("13:40:01").do(close_future_hedge)
        # schedule.every().day.at("13:41:01").do(close_future_hedge)
        # schedule.every().day.at("13:42:01").do(close_future_hedge)
        # schedule.every().day.at("13:43:01").do(close_future_hedge)
        # schedule.every().day.at("13:44:01").do(close_future_hedge)
        # schedule.every().day.at("13:45:01").do(close_future_hedge)
        # schedule.every().day.at("13:46:01").do(close_future_hedge)
        # schedule.every().day.at("13:47:01").do(close_future_hedge)
        # schedule.every().day.at("13:48:01").do(close_future_hedge)
        # schedule.every().day.at("13:49:01").do(close_future_hedge)
        # schedule.every().day.at("13:50:01").do(close_future_hedge)
        # schedule.every().day.at("13:51:01").do(close_future_hedge)
        # schedule.every().day.at("13:52:01").do(close_future_hedge)
        # schedule.every().day.at("13:53:01").do(close_future_hedge)
        # schedule.every().day.at("13:54:01").do(close_future_hedge)
        # schedule.every().day.at("13:55:01").do(close_future_hedge)
        # schedule.every().day.at("13:56:01").do(close_future_hedge)
        # schedule.every().day.at("13:57:01").do(close_future_hedge)
        # schedule.every().day.at("13:58:01").do(close_future_hedge)
        # schedule.every().day.at("13:59:01").do(close_future_hedge)
        # schedule.every().day.at("14:00:01").do(close_future_hedge)
        # schedule.every().day.at("14:01:01").do(close_future_hedge)
        # schedule.every().day.at("14:02:01").do(close_future_hedge)
        # schedule.every().day.at("14:03:01").do(close_future_hedge)
        # schedule.every().day.at("14:04:01").do(close_future_hedge)
        # schedule.every().day.at("14:05:01").do(close_future_hedge)
        # schedule.every().day.at("14:06:01").do(close_future_hedge)
        # schedule.every().day.at("14:07:01").do(close_future_hedge)
        # schedule.every().day.at("14:08:01").do(close_future_hedge)
        # schedule.every().day.at("14:09:01").do(close_future_hedge)
        # schedule.every().day.at("14:10:01").do(close_future_hedge)
        # schedule.every().day.at("14:11:01").do(close_future_hedge)
        # schedule.every().day.at("14:12:01").do(close_future_hedge)
        # schedule.every().day.at("14:13:01").do(close_future_hedge)
        # schedule.every().day.at("14:14:01").do(close_future_hedge)
        # schedule.every().day.at("14:15:01").do(close_future_hedge)
        # schedule.every().day.at("14:16:01").do(close_future_hedge)
        # schedule.every().day.at("14:17:01").do(close_future_hedge)
        # schedule.every().day.at("14:18:01").do(close_future_hedge)
        # schedule.every().day.at("14:19:01").do(close_future_hedge)
        # schedule.every().day.at("14:20:01").do(close_future_hedge)
        # schedule.every().day.at("14:21:01").do(close_future_hedge)
        # schedule.every().day.at("14:22:01").do(close_future_hedge)
        # schedule.every().day.at("14:23:01").do(close_future_hedge)
        # schedule.every().day.at("14:24:01").do(close_future_hedge)
        # schedule.every().day.at("14:25:01").do(close_future_hedge)
        # schedule.every().day.at("14:26:01").do(close_future_hedge)
        # schedule.every().day.at("14:27:01").do(close_future_hedge)
        # schedule.every().day.at("14:28:01").do(close_future_hedge)
        # schedule.every().day.at("14:29:01").do(close_future_hedge)
        # schedule.every().day.at("14:30:01").do(close_future_hedge)
        # schedule.every().day.at("14:31:01").do(close_future_hedge)
        # schedule.every().day.at("14:32:01").do(close_future_hedge)
        # schedule.every().day.at("14:33:01").do(close_future_hedge)
        # schedule.every().day.at("14:34:01").do(close_future_hedge)
        # schedule.every().day.at("14:35:01").do(close_future_hedge)
        # schedule.every().day.at("14:36:01").do(close_future_hedge)
        # schedule.every().day.at("14:37:01").do(close_future_hedge)
        # schedule.every().day.at("14:38:01").do(close_future_hedge)
        # schedule.every().day.at("14:39:01").do(close_future_hedge)
        # schedule.every().day.at("14:40:01").do(close_future_hedge)
        # schedule.every().day.at("14:41:01").do(close_future_hedge)
        # schedule.every().day.at("14:42:01").do(close_future_hedge)
        # schedule.every().day.at("14:43:01").do(close_future_hedge)
        # schedule.every().day.at("14:44:01").do(close_future_hedge)
        # schedule.every().day.at("14:45:01").do(close_future_hedge)
        # schedule.every().day.at("14:46:01").do(close_future_hedge)
        # schedule.every().day.at("14:47:01").do(close_future_hedge)
        # schedule.every().day.at("14:48:01").do(close_future_hedge)
        # schedule.every().day.at("14:49:01").do(close_future_hedge)
        # schedule.every().day.at("14:50:01").do(close_future_hedge)
        # schedule.every().day.at("14:51:01").do(close_future_hedge)
        # schedule.every().day.at("14:52:01").do(close_future_hedge)
        # schedule.every().day.at("14:53:01").do(close_future_hedge)
        # schedule.every().day.at("14:54:01").do(close_future_hedge)
        # schedule.every().day.at("14:55:01").do(close_future_hedge)
        # schedule.every().day.at("14:56:01").do(close_future_hedge)
        # schedule.every().day.at("14:57:01").do(close_future_hedge)
        # schedule.every().day.at("14:58:01").do(close_future_hedge)
        # schedule.every().day.at("14:59:01").do(close_future_hedge)
        # schedule.every().day.at("15:00:01").do(close_future_hedge)
        # schedule.every().day.at("15:01:01").do(close_future_hedge)
        # schedule.every().day.at("15:02:01").do(close_future_hedge)
        # schedule.every().day.at("15:03:01").do(close_future_hedge)
        # schedule.every().day.at("15:04:01").do(close_future_hedge)
        # schedule.every().day.at("15:05:01").do(close_future_hedge)
        # schedule.every().day.at("15:06:01").do(close_future_hedge)
        # schedule.every().day.at("15:07:01").do(close_future_hedge)
        # schedule.every().day.at("15:08:01").do(close_future_hedge)
        # schedule.every().day.at("15:09:01").do(close_future_hedge)
        # schedule.every().day.at("15:10:01").do(close_future_hedge)
        # schedule.every().day.at("15:11:01").do(close_future_hedge)
        # schedule.every().day.at("15:12:01").do(close_future_hedge)
        # schedule.every().day.at("15:13:01").do(close_future_hedge)
        # schedule.every().day.at("15:14:01").do(close_future_hedge)
        # schedule.every().day.at("15:15:01").do(close_future_hedge)
        # schedule.every().day.at("15:16:01").do(close_future_hedge)
        # schedule.every().day.at("15:17:01").do(close_future_hedge)
        # schedule.every().day.at("15:18:01").do(close_future_hedge)
        # schedule.every().day.at("15:19:01").do(close_future_hedge)
        # schedule.every().day.at("15:20:01").do(close_future_hedge)
        # schedule.every().day.at("15:21:01").do(close_future_hedge)
        # schedule.every().day.at("15:22:01").do(close_future_hedge)
        # schedule.every().day.at("15:23:01").do(close_future_hedge)
        # schedule.every().day.at("15:24:01").do(close_future_hedge)
        # schedule.every().day.at("15:25:01").do(close_future_hedge)
        # schedule.every().day.at("15:26:01").do(close_future_hedge)
        # schedule.every().day.at("15:27:01").do(close_future_hedge)
        # schedule.every().day.at("15:28:01").do(close_future_hedge)
        # schedule.every().day.at("15:29:13").do(close_future_hedge)
        schedule.every().day.at("15:29:31").do(remove_SL)

        schedule.every().day.at("10:03:02").do(fixed_profit_entry_with_arguments)
        schedule.every().tuesday.at("15:26:02").do(fixed_profit_entry_with_arguments)
        schedule.every().wednesday.at("15:26:02").do(close_old_insurance)
        schedule.every().thursday.at("15:26:02").do(close_old_insurance)
        schedule.every().tuesday.at("15:26:02").do(close_old_insurance)
    while True:
        schedule.run_pending()
        sleep(1)

session.close()
