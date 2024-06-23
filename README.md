# Tutorial
Follow this tutorial to deploy Django to Cloud Run: 
https://www.youtube.com/watch?v=DvwhgXpLE-I

# Setup Guide
## Step 1: Clone the project
git clone https://github.com/duybtr/tbi.git

## Step 2: Install Python dependencies
cd tbi\
pipenv shell\
pipenv install

## Step 3: Install Google Cloud CLI
https://cloud.google.com/sdk/docs/install

## Step 4: Login to your Google account
gcloud init

## Step 5: Select your Google account. For the project, choose "tbi-finance"

## Step 6: Start Cloud SQL Proxy on a new terminal. See the tutorial at the top. For example:
C:\Dev\cloud_sql_proxy.exe -instances=tbi-finance:us-central1:tbi-postgres=tcp:5432

## Step 7: Start the server
python manage.py runserver --settings=transactions.settings.dev

