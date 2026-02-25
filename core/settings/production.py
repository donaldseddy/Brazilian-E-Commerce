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

AWS_ACCESS_KEY_ID       = config("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY   = config("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME      = config("AWS_S3_REGION_NAME", default="us-east-1")
AWS_S3_CUSTOM_DOMAIN    = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
AWS_DEFAULT_ACL         = "public-read"

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {"location": "media"},
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"

SESSION_COOKIE_SECURE = True
