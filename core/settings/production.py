from .base_settings import *
import dj_database_url
from .base_settings import config

DEBUG = False
ALLOWED_HOSTS = []

DATABASES = {

    'default': dj_database_url.parse(
        
        config("DATABASE_URL"),
        conn_max_age=600,
        engine='django.contrib.gis.db.backends.postgis'
    
    )
}