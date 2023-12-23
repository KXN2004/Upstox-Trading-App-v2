from sqlalchemy import Date, create_engine, Column, ForeignKey, String, Integer, Float, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Define the model
Base = declarative_base()

class Credentials(Base):
    """Table contains all the authorization credentials of clients"""
    __tablename__ = 'Credentials'

    client_id = Column('ClientId', String, primary_key=True)
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

class Active(Base):
    """Table contains all the active clients for the day"""
    __tablename__ = 'Active'

    client_id = Column('ClientId', String, ForeignKey(Credentials.client_id), primary_key=True)
    
    def __repr__(self):
        return f'<Active(ClientId="{self.client_id}")>'


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
    engine = create_engine('sqlite:///database.db', echo=True)

    # Link the database schema to metadata of the Base class
    # schema = Base.metadata

    # Bind the engine to the schema
    Base.metadata.create_all(engine, checkfirst=True)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

if __name__ == '__main__':
    main()
