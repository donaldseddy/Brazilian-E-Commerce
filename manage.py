#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Passez à True pour lancer l'ingestion avec `python manage.py` (sans sous-commande).
RUN_OLIST_INGESTION = True


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base_settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    if RUN_OLIST_INGESTION and len(sys.argv) == 1:
        sys.argv.append("load_olist_data")

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
