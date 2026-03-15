"""
management/commands/load_olist_data.py

Stratégie catégories (ruptures fixes) :
  1. Catégorie vide (610 produits) → catégorie fallback "Uncategorized"
  2. Catégorie présente dans products mais absente de translation
     (pc_gamer, portateis_cozinha…) → créée à la volée avec le nom PT seulement
  3. Toutes les autres → lookup normal
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker
from tqdm import tqdm
from utils import normalize_uuid, read_csv, to_int, to_str, parse_dt
from app.models import (
    Category, Customer, Geolocation, Order, OrderItem,
    Payment, Product, Review, Seller, User,
)
from django.db.models import Avg

logger = logging.getLogger(__name__)
fake   = Faker("pt_BR") # donnees fictives propres au bresil (ex: noms, villes, etc.) portugaises

try:
    from utils import PATH_DATA
except ImportError:
    PATH_DATA = "data/"

# Slug de la catégorie fallback — ne jamais changer après la 1ère migration
UNCATEGORIZED_SLUG = "__uncategorized__"
price_map = {}



# ─── Stats ───────────────────────────────────────────────────────────────────
@dataclass
class ImportStats:
    entity:   str
    total:    int = 0
    imported: int = 0
    skipped:  int = 0
    failed:   int = 0
    errors:   list[str] = field(default_factory=list)

    def record_error(self, msg: str) -> None:
        self.failed += 1
        self.errors.append(msg)
        logger.warning(msg)

    def summary(self) -> str:
        return (
            f"[{self.entity}] total={self.total} "
            f"imported={self.imported} "
            f"skipped={self.skipped} "
            f"failed={self.failed}"
        )


#─── Command ─────────────────────────────────────────────────────────────────
class Command(BaseCommand):
    help = "Import les CSV Olist dans PostgreSQL via le nouveau modèle Django."

    def add_arguments(self, parser) -> None:
        raw = PATH_DATA + "raw/"
        parser.add_argument("--geolocations", default=raw + "olist_geolocation_dataset.csv")
        parser.add_argument("--categories",   default=raw + "product_category_name_translation.csv")
        parser.add_argument("--products",     default=raw + "olist_products_dataset.csv")
        parser.add_argument("--customers",    default=raw + "olist_customers_dataset_enriched.csv")
        parser.add_argument("--sellers",      default=raw + "olist_sellers_dataset_enriched.csv")
        parser.add_argument("--orders",       default=raw + "olist_orders_dataset.csv")
        parser.add_argument("--order_items",  default=raw + "olist_order_items_dataset.csv")
        parser.add_argument("--payments",     default=raw + "olist_order_payments_dataset.csv")
        parser.add_argument("--reviews",      default=raw + "olist_order_reviews_dataset.csv")
        parser.add_argument("--batch-size",   type=int, default=500)
        parser.add_argument("--dry-run",      action="store_true")

    def handle(self, *args, **options) -> None:
        self.batch = options["batch_size"]
        self.dry   = options["dry_run"]

        if self.dry:
            self.stdout.write(self.style.WARNING("⚠  DRY-RUN — aucune écriture en base"))

        steps = [
            ("Géolocalisations", self.import_geolocations, options["geolocations"]),
            ("Catégories",       self.import_categories,   options["categories"]),
            ("Produits",         self.import_products,     options["products"]),
            ("Customers",        self.import_customers,    options["customers"]),
            ("Sellers",          self.import_sellers,      options["sellers"]),
            ("Commandes",        self.import_orders,       options["orders"]),
            ("Lignes commande",  self.import_order_items,  options["order_items"]),
            ("Paiements",        self.import_payments,     options["payments"]),
            ("Avis",             self.import_reviews,      options["reviews"]),
        ]

        for label, fn, path in steps:
            self.stdout.write(f"\n→ {label}  ({path})")
            stats = fn(path)
            style = self.style.SUCCESS if stats.failed == 0 else self.style.WARNING
            self.stdout.write(style(f"  {stats.summary()}"))
            for e in stats.errors[:5]:
                self.stdout.write(self.style.ERROR(f"    • {e}"))
            if len(stats.errors) > 5:
                self.stdout.write(f"    … et {len(stats.errors) - 5} autres")

        self.stdout.write(self.style.SUCCESS("\n✓ Import terminé."))

    # ─────────────────────────────────────────────────────────────────────────
    # CATÉGORIES
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_categories(self, path: str) -> ImportStats:
        df    = read_csv(path)
        stats = ImportStats(entity="Category", total=len(df))
        objs  = []

        for row in tqdm(df.itertuples(), total=stats.total, desc="Categories"):
            obj = self._build_category(row, stats)
            if obj:
                objs.append(obj)

        if not self.dry:
            self._bulk_import(Category, objs, self.batch)

            # ── Catégorie fallback (idempotent) ──────────────────────────────
            fallback, created = Category.objects.get_or_create(
                product_category_name = UNCATEGORIZED_SLUG,
                defaults = {"product_category_name_english": "Uncategorized"},
            )
            if created:
                self.stdout.write("  + Catégorie fallback créée")

            stats.imported = Category.objects.count()
        return stats

    @staticmethod
    def _build_category(row: Any, stats: ImportStats) -> Category | None:
        name = to_str(row.product_category_name)
        if not name:
            stats.record_error("Category: product_category_name vide")
            return None
        try:
            return Category(
                product_category_name         = name,
                product_category_name_english = to_str(row.product_category_name_english),
            )
        except Exception as e:
            stats.record_error(f"Category {name}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # PRODUITS
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_products(self, path: str) -> ImportStats:
        df    = read_csv(path)
        stats = ImportStats(entity="Product", total=len(df))

        # Map complet PT → objet Category
        cats = {c.product_category_name: c for c in Category.objects.all()}

        objs = []
        for row in tqdm(df.itertuples(), total=stats.total, desc="Products"):
            obj = self._build_product(row, cats, stats)
            if obj:
                objs.append(obj)

        if not self.dry:
            created        = self._bulk_import(Product, objs, self.batch)
            stats.imported = created
            stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_product(row: Any, cats: dict, stats: ImportStats) -> Product | None:
        uid = normalize_uuid(row.product_id)
        if not uid:
            stats.record_error(f"Product UUID invalide: {row.product_id}")
            return None
        product_name = to_str(row.product_name)
        weight = to_int(row.product_weight_g)
        height = to_int(row.product_height_cm)
        if weight is None or height is None:
            stats.record_error(f"Product {uid}: poids ou hauteur manquant")
            return None

        cat_name = to_str(row.product_category_name)

        # Niveau 1 — lookup exact dans la translation
        category = cats.get(cat_name)

        # Niveau 2 — catégorie PT absente de la translation → créer à la volée
        if category is None and cat_name:
            category, created = Category.objects.get_or_create(
                product_category_name = cat_name,
                defaults = {"product_category_name_english": cat_name.replace("_", " ").title()},
            )
            if created:
                cats[cat_name] = category
                logger.info(f"Catégorie créée à la volée: {cat_name!r}")

        # Niveau 3 — catégorie vide → fallback Uncategorized
        if category is None:
            category = cats.get(UNCATEGORIZED_SLUG)
            # Si même la fallback est absente (ex: dry-run), on laisse None — sera ignoré
            if category is None:
                stats.record_error(f"Product {uid}: catégorie vide et fallback introuvable")
                return None

        try:
            return Product(
                product_id          = uid,
                category            = category,
                product_name        = product_name,
                product_name_length = to_int(getattr(row, "product_name_lenght",
                                               getattr(row, "product_name_length", None))),
                product_description = to_int(getattr(row, "product_description_lenght",
                                               getattr(row, "product_description_length", None))) or 0,
                product_photo       = to_int(getattr(row, "product_photos_qty",
                                               getattr(row, "product_photo", None))) or 0,
                product_weight_g    = weight,
                product_length_cm   = to_int(row.product_length_cm),
                product_height_cm   = height,
                product_width_cm    = to_int(row.product_width_cm) or 0,
                product_price       =price_map.get(uid)
            )
        except Exception as e:
            stats.record_error(f"Product {uid}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # GEOLOCALISATIONS
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_geolocations(self, path: str) -> ImportStats:
        df    = read_csv(path)
        stats = ImportStats(entity="Geolocation", total=len(df))
        objs  = []
        for row in tqdm(df.itertuples(), total=stats.total, desc="Geolocations"):
            obj = self._build_geolocation(row, stats)
            if obj:
                objs.append(obj)
        if not self.dry:
            created        = self._bulk_import(Geolocation, objs, self.batch)
            stats.imported = created
            stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_geolocation(row: Any, stats: ImportStats) -> Geolocation | None:
        try:
            return Geolocation(
                geolocation_zip_code_prefix = str(row.geolocation_zip_code_prefix).zfill(5),
                geolocation_lat             = float(row.geolocation_lat),
                geolocation_lng             = float(row.geolocation_lng),
                geolocation_city            = to_str(row.geolocation_city),
                geolocation_state           = to_str(row.geolocation_state),
            )
        except Exception as e:
            stats.record_error(f"Geolocation {row.geolocation_zip_code_prefix}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # CUSTOMERS
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_customers(self, path: str) -> ImportStats:
        df    = read_csv(path)
        stats = ImportStats(entity="Customer", total=len(df))
        geos  = {g.geolocation_zip_code_prefix: g
                 for g in Geolocation.objects.only("geolocation_zip_code_prefix")}
        user_objs, pairs = [], []

        for row in tqdm(df.itertuples(), total=stats.total, desc="Customers"):
            result = self._build_customer_pair(row, geos, stats)
            if result:
                user_objs.append(result[0])
                pairs.append(result)

        if self.dry:
            return stats

        User.objects.bulk_create(user_objs, batch_size=self.batch, ignore_conflicts=True)
        emails        = [u.email for u in user_objs]
        user_by_email = {u.email: u for u in User.objects.filter(email__in=emails)}

        customer_objs = []
        for u_tpl, cid in pairs:
            user = user_by_email.get(u_tpl.email)
            if user:
                customer_objs.append(Customer(customer_id=cid, user=user))

        created        = self._bulk_import(Customer, customer_objs, self.batch)
        stats.imported = created
        stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_customer_pair(row: Any, geos: dict, stats: ImportStats):
        cid = normalize_uuid(row.customer_id)
        if not cid:
            stats.record_error(f"Customer UUID invalide: {row.customer_id}")
            return None
        zip_str = str(row.customer_zip_code_prefix).zfill(5)
        email   = fake.unique.email()
        try:
            user = User(
                username        = email,
                email           = email,
                first_name      = to_str(row.customer_first_name),
                last_name       = to_str(row.customer_last_name),
                city            = to_str(row.customer_city).title(),
                state           = to_str(row.customer_state).upper(),
                address         = to_str(row.customer_address),
                zip_code_prefix = geos.get(zip_str),
                role            = User.ROLE_CUSTOMER,
                password        = make_password(None),
                is_active       = False,
            )
            return user, cid
        except Exception as e:
            stats.record_error(f"Customer {cid}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # SELLERS
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_sellers(self, path: str) -> ImportStats:
        df    = read_csv(path)
        stats = ImportStats(entity="Seller", total=len(df))
        geos  = {g.geolocation_zip_code_prefix: g
                 for g in Geolocation.objects.only("geolocation_zip_code_prefix")}
        user_objs, pairs = [], []

        for row in tqdm(df.itertuples(), total=stats.total, desc="Sellers"):
            result = self._build_seller_pair(row, geos, stats)
            if result:
                user_objs.append(result[0])
                pairs.append(result)

        if self.dry:
            return stats

        User.objects.bulk_create(user_objs, batch_size=self.batch, ignore_conflicts=True)
        emails        = [u.email for u in user_objs]
        user_by_email = {u.email: u for u in User.objects.filter(email__in=emails)}

        seller_objs = []
        for u_tpl, sid in pairs:
            user = user_by_email.get(u_tpl.email)
            if user:
                seller_objs.append(Seller(seller_id=sid, user=user))

        created        = self._bulk_import(Seller, seller_objs, self.batch)
        stats.imported = created
        stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_seller_pair(row: Any, geos: dict, stats: ImportStats):
        sid = normalize_uuid(row.seller_id)
        if not sid:
            stats.record_error(f"Seller UUID invalide: {row.seller_id}")
            return None
        zip_str = str(row.seller_zip_code_prefix).zfill(5)
        email   = fake.unique.email()
        try:
            user = User(
                username        = email,
                email           = email,
                first_name      = to_str(row.seller_first_name),
                last_name       = to_str(row.seller_last_name),
                city            = to_str(row.seller_city).title(),
                state           = to_str(row.seller_state).upper(),
                address         = to_str(row.seller_full_address),
                zip_code_prefix = geos.get(zip_str),
                role            = User.ROLE_SELLER,
                password        = make_password(None),
                is_active       = False,
            )
            return user, sid
        except Exception as e:
            stats.record_error(f"Seller {sid}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # COMMANDES
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_orders(self, path: str) -> ImportStats:
        df       = read_csv(path)
        stats    = ImportStats(entity="Order", total=len(df))
        customers = {str(c.customer_id): c for c in Customer.objects.only("customer_id")}
        objs     = []
        for row in tqdm(df.itertuples(), total=stats.total, desc="Orders"):
            obj = self._build_order(row, customers, stats)
            if obj:
                objs.append(obj)
        if not self.dry:
            created        = self._bulk_import(Order, objs, self.batch)
            stats.imported = created
            stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_order(row: Any, customers: dict, stats: ImportStats) -> Order | None:
        oid = normalize_uuid(row.order_id)
        if not oid:
            stats.record_error(f"Order UUID invalide: {row.order_id}")
            return None
        cid      = normalize_uuid(row.customer_id)
        customer = customers.get(str(cid)) if cid else None
        if not customer:
            stats.record_error(f"Order {oid}: customer {row.customer_id} introuvable")
            return None
        try:
            return Order(
                order_id                      = oid,
                customer                      = customer,
                order_status                  = to_str(row.order_status),
                order_purchase_timestamp      = parse_dt(row.order_purchase_timestamp) or timezone.now(),
                order_approved_at             = parse_dt(row.order_approved_at),
                order_delivered_carrier_date  = parse_dt(row.order_delivered_carrier_date),
                order_delivered_customer_date = parse_dt(row.order_delivered_customer_date),
                order_estimated_delivery_date = parse_dt(row.order_estimated_delivery_date),
            )
        except Exception as e:
            stats.record_error(f"Order {oid}: {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # LIGNES DE COMMANDE
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_order_items(self, path: str) -> ImportStats:
        df       = read_csv(path)
        stats    = ImportStats(entity="OrderItem", total=len(df))
        orders   = {str(o.order_id):   o for o in Order.objects.only("order_id")}
        products = {str(p.product_id): p for p in Product.objects.only("product_id")}
        sellers  = {str(s.seller_id):  s for s in Seller.objects.only("seller_id")}
        objs     = []
        for row in tqdm(df.itertuples(), total=stats.total, desc="Order Items"):
            obj = self._build_order_item(row, orders, products, sellers, stats)
            if obj:
                objs.append(obj)
        if not self.dry:
            created        = self._bulk_import(OrderItem, objs, self.batch)
            stats.imported = created
            stats.skipped  = stats.total - stats.failed - created

            # Calcule la moyenne des order_item_price par produit et l'écrit dans Product.price — appelé après import_order_items.
            price_map = {
                row["product_id"]: row["avg"]
                for row in OrderItem.objects
                .values("product_id")
                .annotate(avg=Avg("order_item_price"))
            }
            to_update = []
            for product in Product.objects.filter(product_id__in=price_map):
                product.price = price_map[product.product_id]
                to_update.append(product)
            Product.objects.bulk_update(to_update, ["product_price"], batch_size=self.batch)
            self.stdout.write(f"  Prix mis à jour : {len(to_update)} produits")

        return stats


    @staticmethod
    def _build_order_item(row, orders, products, sellers, stats) -> OrderItem | None:
        oid     = normalize_uuid(row.order_id)
        pid     = normalize_uuid(row.product_id)
        sid     = normalize_uuid(row.seller_id)
        order   = orders.get(str(oid))   if oid else None
        product = products.get(str(pid)) if pid else None
        seller  = sellers.get(str(sid))  if sid else None
        if not order:
            stats.record_error(f"OrderItem: order {row.order_id} introuvable"); return None
        if not product:
            stats.record_error(f"OrderItem order {oid}: product {row.product_id} introuvable"); return None
        if not seller:
            stats.record_error(f"OrderItem order {oid}: seller {row.seller_id} introuvable"); return None
        seq = to_int(row.order_item_id)
        if seq is None:
            stats.record_error(f"OrderItem order {oid}: order_item_id non parseable"); return None
        try:
            return OrderItem(
                order                      = order,
                product                    = product,
                seller                     = seller,
                order_item_sequence_number = seq,
                order_item_price           = float(row.price),
                order_item_freight_value   = float(row.freight_value),
                shipping_limit_date        = parse_dt(row.shipping_limit_date),
            )
        except Exception as e:
            stats.record_error(f"OrderItem order {oid} seq {seq}: {e}"); return None

    # ─────────────────────────────────────────────────────────────────────────
    # PAIEMENTS
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_payments(self, path: str) -> ImportStats:
        df     = read_csv(path)
        stats  = ImportStats(entity="Payment", total=len(df))
        orders = {str(o.order_id): o for o in Order.objects.only("order_id")}
        objs   = []
        for row in tqdm(df.itertuples(), total=stats.total, desc="Payments"):
            obj = self._build_payment(row, orders, stats)
            if obj:
                objs.append(obj)
        if not self.dry:
            created        = self._bulk_import(Payment, objs, self.batch)
            stats.imported = created
            stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_payment(row: Any, orders: dict, stats: ImportStats) -> Payment | None:
        oid   = normalize_uuid(row.order_id)
        order = orders.get(str(oid)) if oid else None
        if not order:
            stats.record_error(f"Payment: order {row.order_id} introuvable"); return None
        seq = to_int(row.payment_sequential)
        if seq is None:
            stats.record_error(f"Payment order {oid}: payment_sequential invalide"); return None
        try:
            return Payment(
                order                = order,
                payment_type         = to_str(row.payment_type),
                payment_sequential   = seq,
                payment_installments = to_int(row.payment_installments),
                payment_value        = float(row.payment_value),
                payment_timestamp    = timezone.now(),
            )
        except Exception as e:
            stats.record_error(f"Payment order {oid}: {e}"); return None

    # ─────────────────────────────────────────────────────────────────────────
    # AVIS
    # ─────────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def import_reviews(self, path: str) -> ImportStats:
        df     = read_csv(path)
        stats  = ImportStats(entity="Review", total=len(df))
        orders = {str(o.order_id): o for o in Order.objects.only("order_id")}
        objs   = []
        for row in tqdm(df.itertuples(), total=stats.total, desc="Reviews"):
            obj = self._build_review(row, orders, stats)
            if obj:
                objs.append(obj)
        if not self.dry:
            created        = self._bulk_import(Review, objs, self.batch)
            stats.imported = created
            stats.skipped  = stats.total - stats.failed - created
        return stats

    @staticmethod
    def _build_review(row: Any, orders: dict, stats: ImportStats) -> Review | None:
        rid = normalize_uuid(row.review_id)
        if not rid:
            stats.record_error(f"Review UUID invalide: {row.review_id}"); return None
        oid   = normalize_uuid(row.order_id)
        order = orders.get(str(oid)) if oid else None
        if not order:
            stats.record_error(f"Review {rid}: order {row.order_id} introuvable"); return None
        score    = to_int(row.review_score)
        creation = parse_dt(row.review_creation_date)
        if score is None:
            stats.record_error(f"Review {rid}: review_score invalide"); return None
        if not creation:
            stats.record_error(f"Review {rid}: review_creation_date invalide"); return None
        try:
            return Review(
                review_id               = rid,
                order                   = order,
                review_score            = score,
                review_comment_title    = to_str(row.review_comment_title),
                review_comment_message  = to_str(row.review_comment_message),
                review_creation_date    = creation,
                review_answer_timestamp = parse_dt(row.review_answer_timestamp),
            )
        except Exception as e:
            stats.record_error(f"Review {rid}: {e}"); return None

    # ─────────────────────────────────────────────────────────────────────────
    # HELPER
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _bulk_import(model, objs: list, batch_size: int) -> int:
        if not objs:
            return 0
        model.objects.bulk_create(objs, batch_size=batch_size, ignore_conflicts=True)
        return len(objs)
