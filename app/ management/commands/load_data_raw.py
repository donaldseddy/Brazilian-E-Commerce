import pandas as pd
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Charge les utilisateurs depuis un CSV dans PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default="data/users_1k.csv",
            help="Chemin du fichier CSV à importer"
        )

    def handle(self, *args, **options):
        csv_path = options["csv"]

        self.stdout.write(self.style.NOTICE(f" Lecture du fichier {csv_path}..."))
        df = pd.read_csv(csv_path)

        users_created = 0
        for _, row in df.iterrows():
            user, created = User.objects.get_or_create(
                email_address=row["email_address"],  # adapté au CSV
                defaults={
                    "full_name": row.get("full_name", ""),
                    "address": row.get("address", ""),
                    "country": row.get("country", "Unknown"),
                    "credit_card_number": row.get("credit_card_number", None),
                    "is_chargemap_pro_user": row.get("is_pro", False),
                    "invoices_count": row.get("invoices_count", 0),
                    "paid_invoices_count": row.get("paid_invoices_count", 0),
                    "current_debt_amount": row.get("debt_amount", 0.0),
                    "feedback_count": row.get("feedback_count", 0),
                    "payment_mean": row.get("payment_mean", None),
                    "payment_time_avg": row.get("payment_time_avg", 0.0),
                }
            )
            if created:
                users_created += 1

        self.stdout.write(self.style.SUCCESS(f"{users_created} utilisateurs importés dans PostgreSQL"))
