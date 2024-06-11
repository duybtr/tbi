from .defaults import *

# Used in common_utils.py 
IS_DEV = True
DATABASES = {
    'default' : {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': '127.0.0.1',
            'PORT': '5432',
            'NAME': 'test_db',
            'USER': db_username,
            'PASSWORD': db_password,
    }
}
 