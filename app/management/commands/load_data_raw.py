import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
import logging
from tqdm import tqdm

from app.models import Geolocation, Customer, Order, OrderItem, Product, Category,Seller,Payment,Review,CartItem,Cart
from faker import Faker

from utils import *
fake = Faker()

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Import raw CSV files into PostgreSQL (Django ORM)"

    def add_arguments(self, parser):
            parser.add_argument('--geolocations', type=str,
                                default=PATH_DATA + 'raw/geolocation.csv',
                                help='Path to geolocations CSV file',
                                required=False)

            parser.add_argument('--customers', type=str,
                                default=PATH_DATA +'raw/olist_customers_dataset_enriched.csv',
                                required=False,
                                help='Path to customers CSV file')

            parser.add_argument('--orders', type=str,
                                default=PATH_DATA +'raw/olist_orders_dataset.csv',
                                required=False,
                                help='Path to orders CSV file')

            parser.add_argument('--order_items', type=str,
                                default=PATH_DATA +'raw/olist_order_items_dataset.csv',
                                required=False,
                                help='Path to order items CSV file')

            parser.add_argument('--products', type=str,
                                default=PATH_DATA +'raw/olist_products_dataset.csv',
                                required=False,
                                help='Path to products CSV file')

            parser.add_argument('--category', type=str,
                                default=PATH_DATA +'raw/category_translations.csv',
                                required=False,
                                help='Path to category translation CSV file')

            parser.add_argument('--seller', type=str,
                                default=PATH_DATA +'raw/olist_sellers_dataset_enriched.csv',
                                required=False,
                                help='Path to sellers CSV file')

            parser.add_argument('--payment', type=str,
                                default='data/raw/olist_order_payments_dataset.csv',
                                required=False,
                                help='Path to payments CSV file')

            parser.add_argument('--review', type=str,
                                default=PATH_DATA +'raw/olist_order_reviews_dataset.csv',
                                required=False,
                                help='Path to reviews CSV file')

            """parser.add_argument('--cart_items', type=str,
                                default='data/raw/cart_items.csv',
                                help='Path to cart items CSV file')
            parser.add_argument('--cart', type=str,
                                default='data/raw/cart.csv',
                                help='Path to cart CSV file')"""


    @transaction.atomic
    def handle(self, *args, **options):
        logger.info("🚀 Starting Olist import...")
        try:
            self.stdout.write(self.style.WARNING("🚀 Starting Olist import..."))
            self.import_geolocations(options['geolocations'])
            self.import_categories(options['category'])
            self.import_products(options['products'])
            self.import_customers(options['customers'])
            self.import_sellers(options['seller'])
            self.import_orders(options['orders'])
            self.import_order_items(options['order_items'])
            self.import_payments(options['payment'])
            self.review_import(options['review'])

        except Exception as e:
            logger.error(f"❌ IMPORT FAILED: {e}")
            raise

        logger.info("🎉 Import completed successfully!")

    def import_geolocations(self, path):
            df = pd.read_csv(path)
            ligne_csv = df.shape[0]
            objs = []
            for row in tqdm(df.itertuples(), total=ligne_csv, desc="Importing Geolocations"):
                try:
                    objs.append(Geolocation(
                        geolocation_zip_code_prefix=row.geolocation_zip_code_prefix,
                        geolocation_lat=row.geolocation_lat,
                        geolocation_lng=row.geolocation_lng,
                        geolocation_city=row.geolocation_city,
                        geolocation_state=row.geolocation_state
                    ))
                except Exception as e:
                    logger.error(f"Error importing geolocation {row.geolocation_zip_code_prefix}: {e}")
                    continue

            Geolocation.objects.bulk_create(objs, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f"📍 Geolocations imported: {len(objs)}/{ligne_csv}"))


    def import_categories(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        objs = []
        for row in tqdm( df.itertuples(), total=ligne_csv, desc="Importing Categories"):
            try:
                objs.append(Category(
                    product_category_name=row.product_category_name,
                    product_category_name_english=row.product_category_name_english,
                ))
            except Exception as e:
                logger.error(f"Error importing category {row.product_category_name}: {e}")
                continue
        Category.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"📂 Categories imported: {len(objs)}/{ligne_csv}"))


    def import_products(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        categories = {c.product_category_name: c for c in Category.objects.all()}

        objs = []
        for row in tqdm( df.itertuples(), total=ligne_csv, desc="Importing Products"):
            try:
                category = categories.get(row.product_category_name)
                objs.append(Product(
                    product_id=row.product_id,
                    category=category,
                    product_name_length=row.product_name_lenght,
                    product_description=row.product_description_lenght,
                    product_photo=row.product_photos_qty,
                    product_weight_g=row.product_weight_g,
                    product_length_cm=row.product_length_cm,
                    product_height_cm=row.product_height_cm,
                    product_width_cm=row.product_width_cm,
                ))
            except Exception as e:
                logger.error(f"Error importing product {row.product_id}: {e}")
                continue
        Product.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"📦 Products imported: {len(objs)}/{ligne_csv}"))


    def import_customers(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        geos = {g.geolocation_zip_code_prefix: g for g in Geolocation.objects.all()}

        objs = []
        for row in tqdm( df.itertuples(), total=ligne_csv, desc="Importing Customers"):
            try:
                geo = geos.get(str(row.customer_zip_code_prefix).zfill(5))
                objs.append(Customer(
                    customer_id=row.customer_id,
                    customer_first_name=row.customer_first_name,
                    customer_last_name=row.customer_last_name,
                    customer_zip_code_prefix=geo,
                    customer_city=row.customer_city,
                    customer_state=row.customer_state,
                    customer_address=row.address,
                    customer_email=fake.email(),
                    customer_phone_number=fake.phone_number(),
                ))
            except Exception as e:
                logger.error(f"Error importing customer {row.customer_id}: {e}")
                continue
        Customer.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"👤 Customers imported: {len(objs)}/{ligne_csv}"))


    def import_sellers(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        geos = {g.geolocation_zip_code_prefix: g for g in Geolocation.objects.all()}

        objs = []
        for row in tqdm( df.itertuples(), total=ligne_csv, desc="Importing Sellers"):
            try:
                geo = geos.get(str(row.seller_zip_code_prefix).zfill(5))
                objs.append(Seller(
                    seller_id=row.seller_id,
                    seller_first_name=row.seller_first_name,
                    seller_zip_code_prefix=geo,
                    seller_last_name=row.seller_last_name,
                    seller_phone_number=fake.phone_number(),
                    seller_city=row.seller_city,
                    seller_email=fake.email(),
                    seller_state=row.seller_state,
                    seller_address=row.seller_address
                ))
            except Exception as e:
                logger.error(f"Error importing seller {row.seller_id}: {e}")
                continue
        Seller.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"🏪 Sellers imported: {len(objs)}/{ligne_csv}"))


    def import_orders(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        customers = {c.customer_id: c for c in Customer.objects.all()}

        objs = []
        for row in tqdm( df.itertuples(), total=ligne_csv, desc="Importing Orders"):
            try:
                customer = customers.get(row.customer_id)
                objs.append(Order(
                    order_id=row.order_id,
                    customer=customer,
                    order_status=row.order_status,
                    order_purchase_timestamp=row.order_purchase_timestamp,
                    order_approved_at=row.order_approved_at,
                    order_delivered_carrier_date=row.order_delivered_carrier_date,
                    order_delivered_customer_date=row.order_delivered_customer_date,
                    order_estimated_delivery_date=row.order_estimated_delivery_date,
                ))
            except Exception as e:
                logger.error(f"Error importing order {row.order_id}: {e}")
                continue

        Order.objects.bulk_create(objs, ignore_conflicts=True)
        logger.info(f"Orders imported: {len(objs)}/{ligne_csv}")




    def import_order_items(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        orders = {o.order_id: o for o in Order.objects.all()}
        products = {p.product_id: p for p in Product.objects.all()}
        sellers = {s.seller_id: s for s in Seller.objects.all()}

        objs = []
        for row in tqdm(df.itertuples(),total=ligne_csv,desc="Importing Order Items"):
            try:
                objs.append(OrderItem(
                    order=orders.get(row.order_id),
                    product=products.get(row.product_id),
                    seller=sellers.get(row.seller_id),
                    order_item_sequence_number=row.order_item_id,
                    order_item_price=row.price,
                    order_item_freight_value=row.freight_value,
                    shipping_limit_date=row.shipping_limit_date
                ))
            except Exception as e:
                logger.error(f"Error importing order item for order {row.order_id}: {e}")
                continue
        OrderItem.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"📦 Order Items imported: {len(objs)}/{ligne_csv}"))



    def import_payments(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        orders = {o.order_id: o for o in Order.objects.all()}

        objs = []
        for row in df.itertuples():
            try:
                objs.append(Payment(
                    order=orders.get(row.order_id),
                    payment_sequential=row.payment_sequential,
                    payment_type=row.payment_type,
                    payment_installments=row.payment_installments,
                    payment_value=row.payment_value,
                ))
            except Exception as e:
                logger.error(f"Error importing payment for order {row.order_id}: {e}")
                continue
        Payment.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f" 💳 Payments imported: {len(objs)}/{ligne_csv}"))


    def review_import(self, path):
        df = pd.read_csv(path)
        ligne_csv = df.shape[0]
        orders = {o.order_id: o for o in Order.objects.all()}
        objs =[]
        for row in df.itertuples():
            try:
                objs.append(Review(
                    order=orders.get(row.order_id),
                    review_id=row.review_id,
                    review_score=row.review_score,
                    review_comment_title=row.review_comment_title,
                    review_comment_message=row.review_comment_message,
                    review_creation_date=row.review_creation_date,
                    review_answer_timestamp=row.review_answer_timestamp
                ))
            except Exception as e:
                logger.error(f"Error importing review for order {row.order_id}: {e}")
                continue
        Review.objects.bulk_create(objs, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"⭐ Reviews imported: {len(objs)}/{ligne_csv}"))