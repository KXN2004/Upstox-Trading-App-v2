from models import Credentials, Active
from upstox_client import LoginApi
from upstox_client.rest import ApiException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Define the schema of the database
schema = declarative_base().metadata

# Establish connection with the database
engine = create_engine('sqlite:///database.db')

# Reflect the schema of the database in the engine
schema.reflect(engine)

# Create a session
Session = sessionmaker(bind=engine)

# Create an instance of the session
session = Session()

# Create an instance of the LoginApi class
api_instance = LoginApi()

# login_url = https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=d6cb7427-c883-456f-9e2a-5f01f944fd78&redirect_uri=https://account.upstox.com/contact-info/

# Select all the active client
active_clients = session.query(Active)

# For each active client
for client in active_clients:
    # Select the credentials of that client
    client = session.query(Credentials).filter_by(client_id=client.client_id).first()

    try:
        # Authorize that client
        api_response = api_instance.token(
            api_version='2.0',
            code=input(f"Enter the code for {client.client_id}: "),  # Temp: bZu7TU
            client_id=client.api_key,
            client_secret=client.api_secret,
            redirect_uri='https://account.upstox.com/contact-info/',
            grant_type='authorization_code'
        )
        # Update the access token of that client
        client.access_token = api_response.access_token
        session.commit()
        print(f"Access token of {client.client_id} is {client.access_token}")
    except ApiException as e:
        print("Exception when calling LoginApi->token: %s\n" % e)

# Close the session
session.close()
