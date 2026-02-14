from django.test import TestCase


import os
import tempfile
import pandas as pd
from django.test import TestCase
from django.core.management import call_command
from app.models import Geolocation, Customer, Order, OrderItem, Product, Category, Seller, Payment, Review


class TestLoadDataRaw(TestCase):
    def setUp(self):
        self.geo_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        geo_df = pd.DataFrame({
            'geolocation_zip_code_prefix': [12345],
            'geolocation_lat': [12.34],
            'geolocation_lng': [56.78],
            'geolocation_city': ['Test City'],
            'geolocation_state': ['TS']
        })
        geo_df.to_csv(self.geo_file.name, index=False)

        self.categ_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")

        categ_df = pd.DataFrame({
            'product_category_name': ['Test Category name portuguese'],
            'product_category_name_english': ['Test Category name english']
        })
        categ_df.to_csv(self.categ_file.name, index=False)

        self.products_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        products_df = pd.DataFrame({
            'product_id': [1],
            'product_category_name': ['Test Category name portuguese'],
            'product_name_lenght': [10],
            'product_description_lenght': [20],
            'product_photos_qty': [5],
            'product_weight_g': [500],
            'product_length_cm': [30],
            'product_height_cm': [20],
            'product_width_cm': [15]
        })
        products_df.to_csv(self.products_file.name, index=False)

        self.customers_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        customers_df = pd.DataFrame({
            'customer_id': [1],
            'customer_first_name': ['John'],
            'customer_last_name': ['Doe'],
            'customer_city': ['Test City'],
            'customer_state': ['TS'],
            'customer_address': ['Test Address'],
            'customer_zip_code_prefix': [12345]
        })
        customers_df.to_csv(self.customers_file.name, index=False)

        self.sellers_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        sellers_df = pd.DataFrame({
            'seller_id': [1],
            'seller_first_name': ['Jane'],
            'seller_zip_code_prefix': [12345],
            'seller_last_name': ['Smith'],
            'seller_phone_number': ['123-456-7890'],
            'seller_city': ['Test City'],
            'seller_state': ['TS'],
            'seller_address': ['Test Address']
            })
        sellers_df.to_csv(self.sellers_file.name, index=False)

        self.orders_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        orders_df = pd.DataFrame({
            'order_id': ['1'],
            'customer': ['12'],
            'order_status': ['delivered'],
            'order_purchase_timestamp': ['2024-01-01 10:00:00'],
            'order_approved_at' : ['2024-01-01 11:00:00'],
            'order_delivered_carrier_date' : ['2024-01-02 10:00:00'],
            'order_delivered_customer_date' : ['2024-01-03 10:00:00'],
            'order_estimated_delivery_date' : ['2024-01-04 10:00:00']
        })
        orders_df.to_csv(self.orders_file.name, index=False)

        self.order_items_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        order_items_df = pd.DataFrame({
            'order': ['1'],
            'product': ['1'],
            'seller': ['1'],
            'order_item_sequence_number': [1],
            'order_item_price': [100.0],
            'order_item_freight_value': [10.0],
            'shipping_limit_date': ['2024-01-05 10:00:00']
        })
        order_items_df.to_csv(self.order_items_file.name, index=False)

        self.payments_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        payments_df = pd.DataFrame({
            'order': ['1'],
            'payment_sequential': [1],
            'payment_type': ['credit_card'],
            'payment_installments': [1],
            'payment_value': [100.0]
        })
        payments_df.to_csv(self.payments_file.name, index=False)

        self.reviews_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        reviews_df = pd.DataFrame({
            'order': ['1'],
            'review_id': ['1'],
            'review_score': [5],
            'review_comment_title': ['Great product!'],
            'review_comment_message': ['I loved this product, it exceeded my expectations.'],
            'review_creation_date': ['2024-01-10 10:00:00'],
            'review_answer_timestamp': ['2024-01-11 10:00:00']
        })
        reviews_df.to_csv(self.reviews_file.name, index=False)

    def test_load_data_raw(self):
        call_command("load_data_raw",
                     geolocations=self.geo_file.name,
                     category=self.categ_file.name,
                     products=self.products_file.name,
                     customers=self.customers_file.name,
                     seller=self.sellers_file.name,
                     orders=self.orders_file.name,
                     order_items=self.order_items_file.name,
                     payment=self.payments_file.name,
                     review=self.reviews_file.name
                     )
        self.assertEqual(Geolocation.objects.count(), 1)
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Seller.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Review.objects.count(), 1)

    def test_no_duplicate_import(self):
        call_command("load_data_raw",
                     geolocations=self.geo_file.name,
                     category=self.categ_file.name,
                     products=self.products_file.name,
                     customers=self.customers_file.name,
                     seller=self.sellers_file.name,
                     orders=self.orders_file.name,
                     order_items=self.order_items_file.name,
                     payment=self.payments_file.name,
                     review=self.reviews_file.name
                     )

        call_command("load_data_raw",
                     geolocations=self.geo_file.name,
                     category=self.categ_file.name,
                     products=self.products_file.name,
                     customers=self.customers_file.name,
                     seller=self.sellers_file.name,
                     orders=self.orders_file.name,
                     order_items=self.order_items_file.name,
                     payment=self.payments_file.name,
                     review=self.reviews_file.name
                     )

        self.assertEqual(Geolocation.objects.count(), 1)

