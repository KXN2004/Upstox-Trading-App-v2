from sys import exit
from os import system, getenv
from os.path import getmtime as last_modified
from datetime import datetime
from schedule import every, run_pending as run_scheduler
from requests import get as send_request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Trades, TradeStatus

token = getenv("API_TOKEN")
chats = getenv("XAVIER_ID"), getenv("KEVIN_ID")
req_url = f"https://api.telegram.org/bot{token}/sendMessage"
database = "database.db"
engine = create_engine("sqlite:///" + database)
Session = sessionmaker(bind=engine)
session = Session()


def check_algo():
    current_time = datetime.now()
    modified_time = datetime.fromtimestamp(last_modified(database))
    time_delta = round((current_time - modified_time).total_seconds())

    if time_delta > 30:
        for chat in chats:
            send_request(
                url=req_url,
                headers={"Content-Type": "application/json"},
                params={
                    "chat_id": chat,
                    "text": f"The database was last updated {time_delta} seconds ago!"
                }
            )

    system("cls")
    print("Last checked on", current_time.strftime("%A, %d %B %Y, at %I:%M:%S %p"))


def check_rejected():
    trades_rejected = session.query(Trades).filter_by(status=TradeStatus.REJECTED.value).count()

    if trades_rejected:
        for chat in chats:
            send_request(
                url=req_url,
                headers={"Content-Type": "application/json"},
                params={
                    "chat_id": chat,
                    "text": f"{trades_rejected} trade(s) have been rejected!"
                }
            )


def quit_check():
    print("Exiting programme...")
    exit()


every(30).seconds.do(check_algo)
every(60).seconds.do(check_rejected)
every().day.at("15:30").do(quit_check)


while True:
    run_scheduler()
