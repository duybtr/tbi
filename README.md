# Tutorial
Follow this tutorial to deploy Django to Cloud Run: 
https://www.youtube.com/watch?v=DvwhgXpLE-I

# Setup Guide
## Step 1: Clone the project
git clone https://github.com/duybtr/tbi.git

## Step 2. Create a virtual environment and activate it
Navigate to the folder we just clone and enter the following commands:

virtualenv env

env\Scripts\activate

## Step 3: Install the necessary requirements
pip install -r requirements.txt

## Step 4: Generate django secret key
python generate_secret_key.py

## Step 5: Download sqlproxy
