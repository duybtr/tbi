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
    if file.name.lower().endswith('pdf'):
        blob.content_type = 'application/pdf'
    elif file.name.lower().endswith('png'):
        blob.content_type = 'image/png'
    elif file.name.lower().endswith(('jpeg','jpg')):
        blob.content_type = 'image/jpeg'
    elif file.name.lower().endswith(('csv','dat')):
        blob.content_type = 'text/plain'
    blob.upload_from_file(file)
    
