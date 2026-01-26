import pandas as pd
from django.core.management.base import BaseCommand
from app.models import

class Command(BaseCommand):
   help = "Import raw CSV files into PostgreSQL (Django ORM)"

    def handle(self, *args, **options):
        base_dir = Path("data/data_clean")

