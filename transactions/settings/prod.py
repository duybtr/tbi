from .defaults import *

if os.environ.get('K_REVISION', None):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '/cloudsql/tbi-finance:us-central1:tbi-postgres',
            'USER': db_username,
            'PASSWORD': db_password,
            'NAME': 'postgres',
        }
    }
else:
    # Running locally so connect to either a local MySQL instance or connect 
    # to Cloud SQL via the proxy.  To start the proxy via command line: 
    #    $ cloud_sql_proxy -instances=[INSTANCE_CONNECTION_NAME]=tcp:3306 
    # See https://cloud.google.com/sql/docs/mysql-connect-proxy
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '127.0.0.1',
            'PORT': '5432',
            'NAME': 'postgres',
            'USER': db_username,
            'PASSWORD': db_password,
        }
    }