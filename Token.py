from models import Credentials
from upstox_client import LoginApi
from upstox_client.rest import ApiException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Constants
TRUE = 1
FALSE = 0

# Define the schema of the database
schema = declarative_base().metadata

# Establish connection with the database
engine = create_engine('sqlite:///database.db')

# Reflect the schema of the database in the engine
# schema.reflect(engine)

# Create a session
Session = sessionmaker(bind=engine)

# Create an instance of the session
session = Session()

# Create an instance of the LoginApi class
api_instance = LoginApi()

# FE6912: 251176 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=d6cb7427-c883-456f-9e2a-5f01f944fd78&redirect_uri=https://account.upstox.com/contact-info/
# 42AFJE: 240220 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=4386a770-aed7-4e7f-8cb2-663b778e4457&redirect_uri=https://account.upstox.com/contact-info/
# 6CAB9R: 006474 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=2988abaa-c17e-4428-a43f-0fc7f22205b0&redirect_uri=https://account.upstox.com/contact-info/
# 6GALGR: 653278 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=465ab58e-8e35-4b09-a289-e813d59d73f0&redirect_uri=https://account.upstox.com/contact-info/
# 2LCHHP: 653278 https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=8c9a6826-1b46-41a3-9492-7f3fe2d2ee71&redirect_uri=https://account.upstox.com/contact-info/

# Select all the active client
active_clients = session.query(Credentials).filter_by(is_active=TRUE)

# For each active client
for client in active_clients:
    # Select the credentials of that client
    client = session.query(Credentials).filter_by(client_id=client.client_id).first()
    
    try:
        # Authorize that client
        api_response = api_instance.token(
            api_version='2.0',
            code=input(f"Enter the code for {client.client_id}: "),
            client_id=client.api_key,
            client_secret=client.api_secret,
            redirect_uri='https://account.upstox.com/contact-info/',
            grant_type='authorization_code'
        )
        # Update the access token of that client
        client.access_token = api_response.access_token
        session.commit()
        print("Access Token Updated")
    except ApiException as e:
        print("Exception when calling LoginApi->token: %s\n" % e)

# Close the session
session.close()
