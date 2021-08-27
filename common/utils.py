# If running locally, be sure to authenticate first. 
# gcloud auth application-default login

from google.cloud import storage

def format_for_storage(filename):
    return filename.replace(' ', '_')

def create_or_retrieve(bucket):
    client = storage.Client()
    bucket = client.bucket(bucket)
    if not bucket.exists():
        bucket = client.create_bucket(bucket)
    return bucket

def store_in_gcs(file, bucket, blob_prefix):
    client = storage.Client()
    bucket = create_or_retrieve(bucket)
    generated_filename = format_for_storage(file.name)
    blob = bucket.blob('{}/{}'.format(blob_prefix, generated_filename))
    blob.upload_from_file(file)
    
