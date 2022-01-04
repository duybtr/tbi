# If running locally, be sure to authenticate first. 
# gcloud auth application-default login

from google.cloud import storage

GCS_ROOT_BUCKET = 'tran_ba_investment_group_llc'

def format_for_storage(filename):
    # maybe use regex here instead
    filename = filename.replace('+', 'and')
    filename = filename.replace('&', 'and')
    return filename.replace(' ', '_')

def create_or_retrieve(bucket):
    client = storage.Client()
    bucket = client.bucket(bucket)
    if not bucket.exists():
        bucket = client.create_bucket(bucket)
    return bucket

def store_files(files, blob_prefix):
    store_in_gcs(files, GCS_ROOT_BUCKET, blob_prefix)

def store_in_gcs(files, bucket, blob_prefix):
    client = storage.Client()
    bucket = create_or_retrieve(bucket)
    for file in files:
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
        
        #if blob.exists(client):
            #raise Exception('File already exists')
        blob.upload_from_file(file)

def list_blobs(folder_name):
    client = storage.Client()
    return client.list_blobs(GCS_ROOT_BUCKET, prefix=folder_name, delimiter='/')

def get_full_blob_url(blob):
    return display_full_path_to_gcs(blob.name)

def get_full_path_to_gcs(relative_path):
    return 'https://storage.cloud.google.com/{}/{}'.format(GCS_ROOT_BUCKET, relative_path)

def rename_blob(orig, dest):
    client = storage.Client()
    bucket = create_or_retrieve(GCS_ROOT_BUCKET)
    blob=bucket.blob(orig)
    bucket.rename_blob(blob, dest)

def delete_file(file, blob_prefix):
    client = storage.Client()
    bucket = create_or_retrieve(GCS_ROOT_BUCKET)
    generated_filename = format_for_storage(file.name)
    blob = bucket.blob('{}/{}'.format(blob_prefix, generated_filename))
    blob.delete()