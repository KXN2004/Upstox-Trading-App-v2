from random import randint
from copy import deepcopy
from upstox_client.rest import ApiException
from datetime import datetime
from dateutil.relativedelta import relativedelta, TH
from models import * 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

engine = create_engine('sqlite:///database.db')
schema = declarative_base().metadata
Session = sessionmaker(bind=engine)
session = Session()

API_VERSION = '2.0'
NO = 0
YES = 1
NOT_APPLICABLE = 'NA'
PUT = 'Put',
CALL = 'Call',
BANK_INDEX = 'NSE_INDEX|Nifty Bank'

active_clients = list()

for _ in session.query(Credentials).filter_by(is_active=YES):
    active_clients.append(Client(_.client_id, _.access_token, session))


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
    return active_clients[0].market_quote_api.ltp(
        get_token(tradingsymbol), API_VERSION
    ).to_dict()['data']['NSE_FO:' + tradingsymbol]['last_price']


def get_banknifty_ltp() -> float:
    """Return the last traded price of the Bank Nifty Index"""
    return active_clients[0].market_quote_api.ltp(
        'NSE_INDEX|Nifty Bank', API_VERSION
    ).to_dict()['data']['NSE_INDEX:Nifty Bank']['last_price']

def get_trades() -> list:
    """Return all the trades in the database"""
    return session.query(Trades).all()


last_price = get_banknifty_ltp()

last_price_0 = round(last_price / 100) * 100

strike_ce = [(last_price_0 + 100 * factor) for factor in range(32)]
strike_ce = [(last_price_0 - 100)] + strike_ce
strike_pe = [(last_price_0 - 100 * factor) for factor in range(37)]
strike_pe = [(last_price_0 + 100)] + strike_pe

shortweek = 0


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
    now = datetime.now()
    todate = datetime.today().date().day
    thursday1 = datetime.strftime(now, '%d/%m/%Y')
    thursday1 = datetime.strptime(thursday1, '%d/%m/%Y')
    thursday1 = thursday1 + relativedelta(days=thursday)
    wednesday1 = datetime.strftime(now, '%d/%m/%Y')
    wednesday1 = datetime.strptime(wednesday1, '%d/%m/%Y')
    wednesday1 = wednesday1 + relativedelta(days=wednesday)
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
        print('Doing this on comming week for monthly expiry')
        wednesday1 = wednesday1 - relativedelta(days=6)
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
        wednesday1 = wednesday1 - relativedelta(days=1)
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
    days_left = fromtime1 = datetime(YY1, MM1, DD1, 15, 30)  # expiry date (YYYY, MM, DD, HR, MIN)
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


def price_strike(expiry: str, price, option):

    print('Inside price_strike')

    buff2 = 0
    
    if option.lower() == 'call':
        print('for new call')
        for strike in strike_ce:
            symbol = expiry + str(strike) + 'CE'
            ltp = get_ltp(symbol)
            print(ltp, 'is price for', symbol)
            if price > ltp:
                buff1 = ltp
                if buff2 - price > price - buff1:
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
                buff2 = ltp
    elif option.lower() == 'put':
        print('for new put')
        for strike in strike_pe:
            symbol = expiry + str(strike) + 'PE'
            print(symbol)
            ltp = get_ltp(symbol)
            print(ltp, 'is price for', symbol)
            if price > ltp:
                buff1 = ltp
                if buff2 - price > price - buff1:
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
                buff2 = ltp


def fixed_profit_entry() -> None:
    """Fixed profit entry strategy"""
    # Properties common to all trades in fixed profit entry strategy
    new_trade = Trades()  # Create a new trade object
    new_trade.strategy = Strategy.FIXED_PROFIT.value
    new_trade.trade_type = TransactionType.SELL.value
    new_trade.entry_status = new_trade.status = TradeStatus.ORDERED.value
    new_trade.days_left = fromtime1
    new_trade.date_time = datetime.now().time()
    new_trade.exit_price = -1
    new_trade.exit_status = NOT_APPLICABLE
    new_trade.profit_loss = 0

    # Common for all clients
    _, put_symbol = price_strike(week1b, 60, PUT)
    _, call_symbol = price_strike(week1b, 60, CALL)

    for client in active_clients:
        new_trade.client_id = client.client_id
        if not client.strategy.fixed_profit:  # If client parameters is zero, skip the client
            continue
        new_trade.quantity = client.strategy.fixed_profit * 15

        # Proceed if client has an open order in fixed profit strategy
        proceed = not client.get_trades().filter(
            Trades.strategy == Strategy.FIXED_PROFIT.value,
            Trades.status != TradeStatus.LIVE.value
        ).all()

        # If fixed profit and bank nifty flags are enabled for the client
        if client.strategy.fixed_profit and client.strategy.bank_nifty and proceed:

            # For Call
            new_trade.order_id = randint(10, 99)
            new_trade.rank = 'Call 0'
            parameters = client.market_quote_api.get_full_market_quote(get_token(call_symbol), API_VERSION).to_dict()
            new_trade.entry_price = parameters['data'][f'NSE_FO:{call_symbol}']['depth']['sell'][0]['price'] - 0.05
            try:
                order = client.place_order(
                    quantity=new_trade.quantity,
                    price=new_trade.entry_price,
                    tradingsymbol=call_symbol,
                    order_type=OrderType.LIMIT,
                    transaction_type=TransactionType.SELL
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
            new_trade.rank = 'Put 0'
            parameters = client.market_quote_api.get_full_market_quote(get_token(put_symbol), API_VERSION).to_dict()
            new_trade.entry_price = parameters['data'][f'NSE_FO:{put_symbol}']['depth']['sell'][0]['price'] - 0.05
            try:
                order = client.place_order(
                    quantity=new_trade.quantity,
                    price=new_trade.entry_price,
                    tradingsymbol=put_symbol,
                    order_type=OrderType.LIMIT,
                    transaction_type=TransactionType.SELL
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


def update() -> None:
    """Update the Trades table"""
    for client in active_clients:
        for trade in client.get_trades():
            current_ltp = get_ltp(trade.symbol)
            if 30 < current_ltp < 120 and not client.get_flags().first_leg:
                trade.LTP = current_ltp
            elif current_ltp < 30:
                match trade.rank:
                    case 'Call 0' | 'Put 0':  # For if Call 0 or Put 0
                        trade.close_trade(client)
                        session.commit()
                    case 'Call 1' | 'Put 1':  # For if Call 1 or Put 1
                        pass
                    case _:
                        raise ValueError('Invalid rank')


weeks()

# fixed_profit_entry()

update()

session.close()

print('Done!')
