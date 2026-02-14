from django.db import models
from django.conf import settings
import uuid
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point
from django.contrib.postgres.search import SearchVectorField


# Create your models here.

class Geolocation(models.Model):
    geolocation_zip_code_prefix = models.CharField(
        max_length=5,
        primary_key=True,
       db_comment="First 5 digits of zip code"
    )

    geolocation_lat = models.FloatField(
        db_comment="Latitude"
    )

    geolocation_lng = models.FloatField(
        db_comment="Longitude"
    )

    geolocation_city = models.CharField(
        max_length=100,
        default="",
        db_comment="City name"
    )

    geolocation_state = models.CharField(
        max_length=2,
        default="",
        db_comment="State abbreviation"
    )

    vector = SearchVectorField(verbose_name='geolocation_city', null=True)
    geolocalization = PointField(srid=4326, geography=True,null=True)



    def save(self, *args, **kwargs):
        self.geolocalization = Point(self.geolocation_lng, self.geolocation_lat, srid=4326)
        super().save(*args, **kwargs)



    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "geolocation"
        ordering = ["geolocation_zip_code_prefix"]



class Customer(models.Model):

    customer_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the customer"
    )

    customer_last_name = models.CharField(max_length=50, db_comment="customer last name.",default="")
    customer_first_name= models.CharField(max_length=50, db_comment="customer first name.",default="")
    customer_zip_code_prefix = models.ForeignKey(Geolocation,on_delete=models.CASCADE, related_name="customers")
    customer_city = models.CharField(max_length=100, default="",db_comment="customer city name.")
    customer_state = models.CharField(max_length=2, default="",db_comment="customer state abbreviation.")
    customer_phone_number= models.CharField(max_length=20,default="", db_comment="customer phone number digits only.")
    customer_address = models.CharField(max_length=150,default="", db_comment="customer address.")
    customer_email = models.EmailField(max_length=50,default="", db_comment="customer email address.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    vector = SearchVectorField(verbose_name=['customer_first_name','customer_last_name'], null=True)


    class Meta:
        db_table = "customer"
        verbose_name_plural = "Customers"


class Seller(models.Model):
    seller_id =  models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the seller"
    )

    seller_first_name= models.CharField(max_length=100, default="",db_comment="seller first name.")
    seller_last_name= models.CharField(max_length=100,default="", db_comment="seller last name.")
    seller_zip_code_prefix = models.ForeignKey(Geolocation,on_delete=models.CASCADE, related_name="Sellers")
    seller_city = models.CharField(max_length=100,default="", db_comment="seller city name.")
    seller_state = models.CharField(max_length=2,default="", db_comment="seller state abbreviation.")
    seller_phone_number= models.CharField(max_length=20,default="", db_comment="seller phone number digits only.")
    seller_address = models.CharField(max_length=150,default="", db_comment="seller address.")
    seller_email = models.EmailField(max_length=50,default="", db_comment="seller email address.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "seller"
        verbose_name_plural = "Sellers"




class Category(models.Model):
    product_category_name = models.CharField(
        max_length=150,default="", db_comment="category name in Portuguese"
    )
    product_category_name_english = models.CharField(
        max_length=150,default="", db_comment="category name in English"
    )
    parent_category = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subcategories'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        verbose_name_plural = "Categories"
        db_table = "category"
        ordering = ['product_category_name']




class Product(models.Model):
    product_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the product"
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )

    product_name_length = models.PositiveIntegerField(null=True,
        blank=True)
    product_description = models.IntegerField(db_comment="number of characters extracted from the product description.")
    product_photo = models.IntegerField(db_comment="number of product published photos")
    product_weight_g = models.IntegerField(db_comment="product weight in grams")
    product_length_cm = models.IntegerField(db_comment="product length in centimeters")
    product_height_cm = models.IntegerField(db_comment="product height in centimeters")
    product_width_cm = models.IntegerField(db_comment="product width in centimeters")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product"
        verbose_name_plural = "Products"




class Order(models.Model):
    order_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the order"
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    order_status = models.CharField(max_length=100,default="", db_comment="Reference to the order status (delivered, shipped, etc)")
    order_purchase_timestamp = models.DateTimeField(db_comment="Timestamp when the order was purchased")
    order_approved_at = models.DateTimeField(null=True, blank=True, db_comment="Timestamp when the order was approved")
    order_delivered_carrier_date = models.DateTimeField(null=True, blank=True, db_comment="Shows the order posting timestamp. When it was handled to the logistic partner.")
    order_delivered_customer_date = models.DateTimeField(null=True, blank=True, db_comment="Shows the order delivery timestamp. When it was delivered to the customer.")
    order_estimated_delivery_date = models.DateTimeField(null=True, blank=True, db_comment="Shows the estimated delivery date that was informed to customer at the purchase moment.")

    class Meta:
        db_table = "order"
        ordering = ['order_purchase_timestamp']
        verbose_name_plural = "Orders"


class OrderItem(models.Model):
    order_item_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the order item"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="order_items")
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name="order_items")
    order_item_sequence_number = models.IntegerField(db_comment="Sequence number of the item in the order")
    order_item_price = models.DecimalField(max_digits=10, decimal_places=2, db_comment="Price of the item ordered")
    order_item_freight_value = models.DecimalField(max_digits=10, decimal_places=2, db_comment="item freight value item( if an order has more than one item the freight value is splitted between items)")
    shipping_limit_date= models.DateTimeField(null=True, blank=True, db_comment="Shows the seller shipping limit date for handling the order over to the logistic partner.")



    class Meta:
        db_table = "order_item"
        verbose_name_plural = "Order Items"



class Payment(models.Model):
    payment_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the payment"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    payment_type = models.CharField(max_length=100, db_comment="Reference to the payment method (credit card, boleto, etc)")
    payment_sequential= models.IntegerField(db_comment="a customer may pay an order with more than one payment method. If he does so, a sequence will be created to")
    payment_timestamp = models.DateTimeField(db_comment="Timestamp when the payment was made")
    payment_installments= models.IntegerField(null=True, blank=True, db_comment="Number of installments chosen by the customer")
    payment_value= models.DecimalField(max_digits=10, decimal_places=2, db_comment="transaction value")

    class Meta:
        db_table = "payment"
        verbose_name_plural = "Payments"




class Review(models.Model):
    review_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the review"
    )
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    review_score = models.IntegerField(db_comment="Score given by the customer in the review (1 to 5)")
    review_comment_title = models.CharField(max_length=255, db_comment="Title of the review comment")
    review_comment_message = models.TextField(db_comment="Message of the review comment")
    review_creation_date = models.DateTimeField(db_comment="Timestamp when the review was created")
    review_answer_timestamp = models.DateTimeField(null=True, blank=True, db_comment="Timestamp when the review was answered by the seller")
    class Meta:
        db_table = "review"
        verbose_name_plural = "Reviews"



class Cart(models.Model):
    cart_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        db_comment="Unique identifier for the cart"
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="carts")
    created_at = models.DateTimeField(db_comment="Timestamp when the cart was created")
    updated_at = models.DateTimeField(null=True, blank=True, db_comment="Timestamp when the cart was updated")
    cart_total_amount = models.DecimalField(max_digits=10, decimal_places=2, db_comment="Total amount of the cart")

    class Meta:
        db_table = "cart"
        ordering = ['created_at']
        verbose_name_plural = "Carts"



class CartItem(models.Model):
    cart_Item_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
    )
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.IntegerField(db_comment="Quantity of the item in the cart")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_comment="Price of the item in the cart")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, db_comment="Subtotal of the item in the cart")
    added_at = models.DateTimeField(null=True,blank=True,db_comment="Timestamp when the item was added to the cart")


    class Meta:
        db_table = "cart_item"
        ordering = ['added_at']
        verbose_name_plural = "Cart Items"


