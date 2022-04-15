from django.core.management.utils import get_random_secret_key
env_file = open('config/.env', 'w')
env_file.write('SECRET_KEY={}'.format(get_random_secret_key()))
env_file.close()