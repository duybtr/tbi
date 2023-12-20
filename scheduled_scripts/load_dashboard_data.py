import psycopg2
import pandas as pd
import logging
import google.cloud.logging
import os
from utils import create_or_retrieve
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.cloud import secretmanager

def access_secret_version(secret_version_id):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Access the secret version.
    response = client.access_secret_version(name=secret_version_id)

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')


def load_data(request):
    env = os.environ.get('env')
    if env == 'PROD':
      db_host = "/cloudsql/tbi-finance:us-central1:tbi-postgres"
    else:
      db_host = "localhost"
    
    db_username = access_secret_version("projects/334572487877/secrets/db_username/versions/1")
    db_password = access_secret_version("projects/334572487877/secrets/db_password/versions/2")
    
    client = google.cloud.logging.Client()
    client.setup_logging()
    logging.info("Connecting to the database...")
    conn = psycopg2.connect(host=db_host, port = 5432, database="postgres", user=db_username, password=db_password)
    # Create a cursor object
    cur = conn.cursor()
    logging.info("Successfully connected to the database")
    logging.info("Retrieving property data...")
    df_properties = pd.read_sql_query("SELECT * FROM transactions_property", conn)
    df_properties = df_properties[['address','purchase_price','full_address']]
    logging.info("Successfully retrieved {} rows of property data".format(len(df_properties)))
    logging.info("Retrieving tax data...")
    df_tax = pd.read_sql_query("SELECT * FROM tbi_tax_report", conn)
    logging.info("Successfully retrieved {} rows of tax data".format(len(df_tax)))
    df_tax['record_date'] = df_tax['record_date'].astype(str)
    df_tax['date_filed'] = df_tax['date_filed'].map(lambda x: x.strftime('%Y-%m-%d'))

    daily_report = df_tax.groupby(['record_date','address','suite','accounting_classification'])['amount'].sum().reset_index()
    daily_report = daily_report.pivot(index = ['record_date','address', 'suite'], columns= "accounting_classification").fillna(0)
    daily_report.columns = daily_report.columns.droplevel(0)
    daily_report = daily_report.reset_index()
    daily_report['Expense'] = daily_report['Expense']*-1
    daily_report['Expense'] = daily_report['Expense'].round(2)
    daily_report['Revenue'] = daily_report['Revenue'].round(2)
    
    logging.info("Moving data in cloud storage....")
    bucket = create_or_retrieve("tran_ba_investment_group_llc")
    bucket.blob('temp/tax_report.csv').upload_from_string(df_tax.to_csv(index=False, sep='|'), 'text/csv')
    bucket.blob('temp/rental_properties.csv').upload_from_string(df_properties.to_csv(index=False, sep='|'), 'text/csv')
    bucket.blob('temp/daily_report.csv').upload_from_string(daily_report.to_csv(index=False, sep='|'), 'text/csv')
    logging.info("All data successfully moved to cloud storage")
    
    # Construct a BigQuery client object.
    logging.info("Connecting to BigQuery...")
    client = bigquery.Client()

    #dataset = bigquery.Dataset(dataset_id)
    dataset_id = "{}.tax_data".format(client.project)
    # Send the dataset to the API for creation, with an explicit timeout.
    # Raises google.api_core.exceptions.Conflict if the Dataset already
    # exists within the project.
    #dataset = client.create_dataset(dataset, timeout=30)  # Make an API request.
    try:
        logging.info("Retrieving dataset {}".format(dataset_id))
        client.get_dataset(dataset_id)
        logging.info("Dataset {} found.".format(dataset_id))
    except NotFound:
        logging.info("Dataset {} not found. Creating the dataset".format(dataset_id))
        client.create_dataset(dataset_id, timeout=30)

    # TODO(developer): Set table_id to the ID of the table to create.
    tax_table_id = "{}.tax_report".format(dataset_id)
    logging.info("Loading tax data into BigQuery table {}".format(tax_table_id))
    client.delete_table(tax_table_id, not_found_ok=True)  # Make an API request.
    tax_job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("record_date", "DATETIME"),
            bigquery.SchemaField("date_filed", "DATETIME"),
            bigquery.SchemaField("full_address", "STRING"),
            bigquery.SchemaField("address", "STRING"),
            bigquery.SchemaField("suite", "STRING"),
            bigquery.SchemaField("amount", "NUMERIC"),
            bigquery.SchemaField("note", "STRING"),
            bigquery.SchemaField("accounting_classification", "STRING"),
            bigquery.SchemaField("category", "STRING"),
        ],
        skip_leading_rows=1,
        # The source format defaults to CSV, so the line below is optional.
        source_format=bigquery.SourceFormat.CSV,
        field_delimiter='|',
        allow_jagged_rows = True,
        allow_quoted_newlines = True
    )
    tax_uri = "gs://tran_ba_investment_group_llc/temp/tax_report.csv"

    load_tax_job = client.load_table_from_uri(
        tax_uri, tax_table_id, job_config=tax_job_config
    )  # Make an API request.

    logging.info("Job completed {}".format(load_tax_job.result()))

    property_table_id = "{}.rental_property".format(dataset_id)
    logging.info("Loading rental data into BigQuery table {}".format(property_table_id))
    client.delete_table(property_table_id, not_found_ok=True)  # Make an API request.
    property_job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("address", "STRING"),
            bigquery.SchemaField("purchase_price", "NUMERIC"),
            bigquery.SchemaField("full_address", "STRING"),
        ],
        skip_leading_rows=1,
        # The source format defaults to CSV, so the line below is optional.
        source_format=bigquery.SourceFormat.CSV,
        field_delimiter='|',
        allow_jagged_rows = True,
        allow_quoted_newlines = True
    )
    property_uri = "gs://tran_ba_investment_group_llc/temp/rental_properties.csv"

    load_property_job = client.load_table_from_uri(
        property_uri, property_table_id, job_config=property_job_config
    )  # Make an API request.
    load_property_job.result()
    logging.info("Job completed {}".format(load_property_job.result()))

    daily_tax_table_id = "{}.daily_tax_table".format(dataset_id)
    logging.info("Loading rental data into BigQuery table {}".format(daily_tax_table_id))
    client.delete_table(daily_tax_table_id, not_found_ok=True)  # Make an API request.
    daily_tax_job_config = bigquery.LoadJobConfig(
        schema=[
            bigquery.SchemaField("record_date", "DATETIME"),
            bigquery.SchemaField("address", "STRING"),
            bigquery.SchemaField("suite", "STRING"),
            bigquery.SchemaField("expense", "NUMERIC"),
            bigquery.SchemaField("revenue", "NUMERIC")
        ],
        skip_leading_rows=1,
        # The source format defaults to CSV, so the line below is optional.
        source_format=bigquery.SourceFormat.CSV,
        field_delimiter='|',
        allow_jagged_rows = True,
        allow_quoted_newlines = True
    )
    daily_tax_uri = "gs://tran_ba_investment_group_llc/temp/daily_report.csv"

    load_daily_tax_job = client.load_table_from_uri(
        daily_tax_uri, daily_tax_table_id, job_config=daily_tax_job_config
    )  # Make an API request.
    load_daily_tax_job.result()
    logging.info("Job completed {}".format(load_daily_tax_job.result()))
    return "Success"