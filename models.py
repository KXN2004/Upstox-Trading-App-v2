import upstox_client
from upstox_client import ApiClient
from sqlalchemy import create_engine, Column, ForeignKey, String, Integer, Float, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from enum import Enum

class TradeStatus(Enum):
    """
    Enum to represent the status of a trade

    Possible values:
        OPEN: Trade is opened
        ORDERED: Order is placed
        PENDING: Order is pending
        LIVE: Order is live
        EXECUTED: Order is executed
        CLOSED: Trade is closed
        REJECTED: Order is rejected

    use the .value attribute to get the value of the enum
    """
    OPEN = 'Open'
    ORDERED = 'Ordered'
    PENDING = 'Pending'
    LIVE = 'Live'
    EXECUTED = 'Executed'
    CLOSED = 'Closed'
    REJECTED = 'Rejected'


class TransactionType(Enum):
    """
    Enum to represent the type of transaction

    Possible values:
        BUY: Buy the order
        SELL: Sell the order

    use the .value attribute to get the value of the enum
    """
    BUY = 'BUY'
    SELL = 'SELL'


class OrderType(Enum):
    """
    Enum to represent the type of order

    Possible values:
        MARKET: Market order
        LIMIT: Limit order
        STOPLOSS_LIMIT: Stoploss limit order
        STOPLOSS_MARKET: Stoploss market order

    use the .value attribute to get the value of the enum
    """
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOPLOSS_LIMIT = 'SL'
    STOPLOSS_MARKET = 'SL-M'


class Product(Enum):
    """
    Enum to represent the type of product

    Possible values:
        DELIVERY: Delivery order
        INTRADAY: Intraday order

    use the .value attribute to get the value of the enum
    """
    DELIVERY = 'D'
    INTRADAY = 'I'


class Validity(Enum):
    """
    Enum to represent the validity of the order

    Possible values:
        DAY: Day order
        IOC: Immediate or cancel order

    use the .value attribute to get the value of the enum
    """
    DAY = 'DAY'
    IOC = 'IOC'


class Strategy(Enum):
    """
    Enum to represent the strategy of the client

    Possible values:
        OPTION_SELLING: Option selling strategy
        FIXED_PROFIT: Fixed profit strategy
        BANK_NIFTY: Banknifty strategy
        FUTURES: Futures strategy
        AUTO_FUTURES: Auto futures strategy

    use the .value attribute to get the value of the enum
    """
    OPTION_SELLING = 'OptionSelling'
    FIXED_PROFIT = 'FixedProfit'
    BANK_NIFTY = 'BankNifty'
    FUTURES = 'Futures'
    AUTO_FUTURES = 'AutoFutures'


# Trade table: status column: OPENED|ORDERED|PENDING|EXECUTED|CLOSED|REJECTED

API_VERSION = '2.0'

class Database:
    def __init__(self, db_path: str):
        engine = create_engine(f'sqlite:///{db_path}')
        # schema = declarative_base().metadata
        # schema.reflect(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        self.connection = session
        self.table = session.query


class Client:
    """Class to represent a client"""

    def __init__(self, client_id: str, access_token: str, session):
        configuration = upstox_client.Configuration()
        configuration.access_token = access_token
        api_client = ApiClient(configuration)
        self.session = session
        self.client_id = client_id
        self.strategy = session.query(Strategies).filter_by(client_id=client_id).first()
        self.api_client = ApiClient(configuration)
        self.market_quote_api = upstox_client.MarketQuoteApi(api_client)
        self.order_api = upstox_client.OrderApi(api_client)

    def get_token(self, tradingsymbol: str) -> str:
        return (self.session
            .query(Instruments)
            .filter_by(trading_symbol=tradingsymbol)
            .first()
            .instrument_key
        )


    # TODO: Redfine tradingsymbol to token over
    def place_order(self,
            quantity: int,
            tradingsymbol: str,
            transaction_type: TransactionType,
            product: Product=Product.INTRADAY,
            validity: Validity=Validity.DAY,
            price: float=0,
            order_type: OrderType=OrderType.MARKET,
            disclosed_quantity: int=0,
            trigger_price: float=0,
            is_amo: bool=False,
        ) -> dict:
        """
        Places an order for the given tradingsymbol

        Required parameters:
            quantity: int
            tradingsymbol: str
            transaction_type: TransactionType

        Default parameters:
            product: Product.INTRADAY
            validity: Validity.DAY
            price: 0
            order_type: OrderType.MARKET
            disclosed_quantity: 0
            trigger_price: 0
            is_amo: False

        Returns:
            dict: Order details
        """
        body = upstox_client.PlaceOrderRequest(
            quantity=quantity,
            product=product.value,  # value of the enum
            validity=validity.value,
            price=price,
            instrument_token=self.get_token(tradingsymbol),
            order_type=order_type.value,
            transaction_type=transaction_type.value,
            disclosed_quantity=disclosed_quantity,
            trigger_price=trigger_price,
            is_amo=is_amo,
        )
        return self.order_api.place_order(body, API_VERSION).to_dict()


    def get_trades(self) :
        '''Return the Trades table for that client'''
        return self.session.query(Trades).filter_by(client_id=self.client_id)

    def get_ltp(self, tradingsymbol: str) -> float:
        """Returns the last traded price of the given tradingsymbol"""
        return (self.market_quote_api
            .ltp(tradingsymbol, '2.0')
            .to_dict()
            ['data']
            ['NSE_FO' + ':' + tradingsymbol]
            ['last_price']
        )
    
    def get_banknifty_ltp(self) -> float:
        """Returns the last traded price of the BankNifty index"""
        return (self.market_quote_api
            .ltp('NSE_INDEX|Nifty Bank', '2.0')
            .to_dict()
            ['data']
            ['NSE_INDEX:Nifty Bank']
            ['last_price']
        )


# Define the model
Base = declarative_base()

# Define the database
DATABASE = 'database.db'


class Instruments(Base):
    """Table contains all the coresponding instrument keys of tradingsymbols"""
    __tablename__ = 'Instruments'

    trading_symbol = Column('TradingSymbol', String, primary_key=True)
    instrument_key = Column('InstrumentKey', String, nullable=False)

    def __repr__(self):
        return f'<InstrumentKey(Tradingsymbol="{self.trading_symbol}")>'

    def __hash__(self):
        return hash(self.name)


class Credentials(Base):
    """Table contains all the authorization credentials of clients"""
    __tablename__ = 'Credentials'

    client_id = Column('ClientId', String, primary_key=True)
    is_active = Column('Active', Integer, default=0)
    api_key = Column('ApiKey', String, nullable=False)
    api_secret = Column('ApiSecret', String, nullable=False)
    access_token = Column('AccessToken', String, nullable=False)

    def __repr__(self):
        return f'<Credential(ClientId="{self.client_id}")>'


class Strategies(Base):
    """Table contains all the strategies offered to the clients"""
    __tablename__ = 'Strategies'

    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), primary_key=True)
    option_selling = Column('OptionSelling', Integer, default=0)
    fixed_profit = Column('FixedProfit', Integer, default=0)
    bank_nifty = Column('BankNifty', Integer, default=0)
    futures = Column('Futures', Integer, default=0)
    auto_futures = Column('AutoFutures', Integer, default=0)

    def __repr__(self):
        return f'<Strategie(ClientId="{self.client_id}")>'


class Flags(Base):
    """Table contains all the flags for the clients"""
    __tablename__ = 'Flags'

    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), primary_key=True)
    profit = Column('Profit', Integer, default=0)
    max_profit = Column('MaxProfit', Integer, default=0)
    max_loss = Column('MaxLoss', Integer, default=0)
    option_selling = Column('OptionSelling', Integer, default=0)
    future = Column('Future', Integer, default=0)
    first_leg = Column('FirstLeg', Integer, default=0)
    five_minutes = Column('FiveMinutes', Integer, default=0)
    sixty_minutes = Column('SixtyMinutes', Integer, default=0)

    def __repr__(self):
        return f'<Flag(ClientId="{self.client_id}")>'
    
class Clients(Base):
    """Table contains all the attributes associated with the clients"""
    __tablename__ = 'Clients'

    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), primary_key=True)
    used = Column('Used', Integer, default=0)
    available = Column('Available', Integer, default=0)
    max_profit = Column('MaxProfit', Integer, default=0)
    max_loss = Column('MaxLoss', Integer, default=0)
    m_to_m = Column('MtoM', Integer, default=0)

    def __repr__(self):
        return f'<Client(ClientId="{self.client_id}")>'



class Trades(Base):
    """Table contains all the trades executed on the clients"""
    __tablename__ = 'Trades'

    order_id = Column('OrderId', String, primary_key=True)
    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), nullable=False)
    date_time = Column('DateTime', Time, nullable=False)
    strategy = Column('Strategy', String,  nullable=False)    
    symbol = Column('Symbol', String, nullable=False)
    rank = Column('Rank', Integer, nullable=False)
    days_left = Column('DaysLeft', Date, nullable=False)
    trade_type = Column('TradeType', String, nullable=False)
    quantity = Column('Quantity', Integer, nullable=False)
    entry_price = Column('EntryPrice', Float, nullable=False)
    entry_status = Column('EntryStatus', String, nullable=False)
    exit_price = Column('ExitPrice', Float, nullable=False)
    exit_status = Column('ExitStatus', String, nullable=False)
    ltp = Column('LTP', Float, nullable=False)
    profit_loss = Column('PnL', Float, nullable=False)
    status = Column('Status', String, nullable=False)

    def __repr__(self):
        return f'<Trade(OrderId="{self.order_id}")>'


def main():
    # Create an SQLite in-memory database engine
    engine = create_engine('sqlite:///{DATABASE}', echo=True)

    # Link the database schema to metadata of the Base class
    # schema = Base.metadata

    # Bind the engine to the schema
    Base.metadata.create_all(engine, checkfirst=True)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Close the session
    session.close()

# if __name__ == '__main__':
#     main()
