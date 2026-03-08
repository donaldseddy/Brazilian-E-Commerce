from rest_framework import serializers
from .models import (
    User, Customer, Seller, Category, Product,
    Order, OrderItem, Payment, Review, Cart, CartItem, ProductImage
)


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    role      = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model  = User
        fields = ["email", "first_name", "last_name", "phone_number", "role",
                  "password", "password2"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("Mots de passe différents.")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")
        role     = validated_data.get("role", User.ROLE_CUSTOMER)

        user = User(username=validated_data["email"], **validated_data)
        user.set_password(password)
        user.save()

        if role == User.ROLE_CUSTOMER:
            Customer.objects.create(user=user)
        else:
            Seller.objects.create(user=user)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ["id", "email", "first_name", "last_name",
                  "phone_number", "city", "state", "address", "role"]


# ─────────────────────────────────────────────────────────────────────────────
# CATALOGUE
# ─────────────────────────────────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model  = Category
        fields = ["id", "product_category_name", "product_category_name_english",
                  "parent_category"]


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.product_category_name_english", read_only=True
    )
    seller_id = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "product_id","product_name", "category", "category_name",
            "product_name_length", "product_description", "product_photo",
            "product_weight_g", "product_length_cm", "product_height_cm",
            "product_width_cm", "seller_id", "created_at",
        ]
        read_only_fields = ["product_id", "created_at"]

    def get_seller_id(self, obj):
        # Retourne le seller_id si le produit est lié à des order_items
        item = obj.order_items.first()
        return str(item.seller.seller_id) if item else None


class ProductCreateSerializer(serializers.ModelSerializer):
    """Utilisé par le vendeur pour créer un produit."""
    class Meta:
        model  = Product
        fields = [
            "category", "product_description", "product_photo",
            "product_weight_g", "product_length_cm", "product_height_cm",
            "product_width_cm",
        ]

class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model  = ProductImage
        fields = ["image_id", "url", "is_primary", "alt_text", "order", "created_at"]

    def get_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


# Mettre à jour ProductSerializer pour inclure les images
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source="category.product_category_name_english", read_only=True
    )
    # Remplace l'ancien champ seller_id
    primary_image = serializers.SerializerMethodField()
    all_images    = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            "product_id","product_name", "category", "category_name",
            "product_weight_g", "product_length_cm",
            "product_height_cm", "product_width_cm",
            "product_photo", "primary_image", "all_images",
            "created_at",
        ]
        extra_kwargs = {
            "product_name": {"required": True, "allow_blank": False},
        }

    def get_primary_image(self, obj):
        request = self.context.get("request")
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if img and request:
            return request.build_absolute_uri(img.image.url)
        return None

    def get_all_images(self, obj):
        request = self.context.get("request")
        return [
            request.build_absolute_uri(i.image.url)
            for i in obj.images.all()
            if request
        ]


# ─────────────────────────────────────────────────────────────────────────────
# PANIER
# ─────────────────────────────────────────────────────────────────────────────

class CartItemSerializer(serializers.ModelSerializer):
    product_id   = serializers.UUIDField(source="product.product_id", read_only=True)
    category     = serializers.CharField(
        source="product.category.product_category_name_english", read_only=True
    )

    class Meta:
        model  = CartItem
        fields = ["cart_Item_id", "product_id", "category",
                  "quantity", "unit_price", "subtotal"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(source="cart_items", many=True, read_only=True)

    class Meta:
        model  = Cart
        fields = ["cart_id", "items", "cart_total_amount", "updated_at"]


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDES
# ─────────────────────────────────────────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.product_id", read_only=True)
    seller_id  = serializers.UUIDField(source="seller.seller_id",  read_only=True)

    class Meta:
        model  = OrderItem
        fields = ["order_item_id", "product_id", "seller_id",
                  "order_item_sequence_number",
                  "order_item_price", "order_item_freight_value",
                  "shipping_limit_date"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Payment
        fields = ["payment_id", "payment_type", "payment_sequential",
                  "payment_installments", "payment_value"]


class OrderSerializer(serializers.ModelSerializer):
    items    = OrderItemSerializer(source="order_items", many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    total    = serializers.SerializerMethodField()
    paid     = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = ["order_id", "order_status", "order_purchase_timestamp",
                  "order_approved_at", "order_delivered_customer_date",
                  "order_estimated_delivery_date",
                  "items", "payments", "total", "paid"]

    def get_total(self, obj):
        return float(sum(
            i.order_item_price + i.order_item_freight_value
            for i in obj.order_items.all()
        ))

    def get_paid(self, obj):
        return obj.payments.exists()


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────────────────────────

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Review
        fields = ["review_id", "order", "review_score",
                  "review_comment_title", "review_comment_message",
                  "review_creation_date"]
        read_only_fields = ["review_id", "review_creation_date"]
