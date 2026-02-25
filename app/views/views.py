import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404
from rest_framework.parsers  import MultiPartParser, FormParser



from ..models import (
    User, Customer, Seller, Category, Product,
    Order, OrderItem, Payment, Review, Cart, CartItem,ProductImage
)
from ..serializers import (
    RegisterSerializer, UserSerializer,
    CategorySerializer, ProductSerializer, ProductCreateSerializer,
    CartSerializer, CartItemSerializer,
    OrderSerializer, PaymentSerializer, ReviewSerializer,ProductImageSerializer,
)



# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access":  str(refresh.access_token),
        "role":    user.role,
        "email":   user.email,
        "first_name": user.first_name,
    }

def get_customer(user):
    try: return user.customer_profile
    except Exception: return None

def get_seller(user):
    try: return user.seller_profile
    except Exception: return None


# ─────────────────────────────────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(get_tokens(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email    = request.data.get("email")
        password = request.data.get("password")
        user     = authenticate(request, username=email, password=password)
        if not user:
            return Response({"error": "Identifiants invalides."},
                            status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        return Response(get_tokens(user))


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            RefreshToken(request.data["refresh"]).blacklist()
        except Exception:
            pass
        logout(request)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        s = UserSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


# ─────────────────────────────────────────────────────────────────────────────
# CATALOGUE — accessible à tous
# ─────────────────────────────────────────────────────────────────────────────

class CategoryListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Category.objects.filter(parent_category=None)
        return Response(CategorySerializer(qs, many=True).data)


class ProductListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Product.objects.select_related("category").all()

        # Filtres optionnels
        category_id = request.query_params.get("category")
        search      = request.query_params.get("search")

        if category_id:
            qs = qs.filter(category_id=category_id)
        if search:
            qs = qs.filter(
                category__product_category_name_english__icontains=search
            )

        return Response(ProductSerializer(qs[:50], many=True).data)


class ProductDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        try:
            p = Product.objects.select_related("category").get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=404)
        return Response(ProductSerializer(p).data)

class ProductImageUploadView(APIView):
    """
    POST /products/<product_id>/images/
    Upload une ou plusieurs images pour un produit.
    Réservé au vendeur propriétaire du produit.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser]

    def _is_owner(self, user, product):
        """Vérifie que le vendeur connecté est bien lié au produit."""
        try:
            seller = user.seller_profile
        except Exception:
            return False
        return OrderItem.objects.filter(
            product=product, seller=seller
        ).exists()

    def get(self, request, product_id):
        """Liste les images d'un produit — public."""
        product = get_object_or_404(Product, product_id=product_id)
        images  = product.images.all()
        return Response(ProductImageSerializer(images, many=True,
                        context={"request": request}).data)

    def post(self, request, product_id):
        """Upload une image."""
        product = get_object_or_404(Product, product_id=product_id)

        # Vérification ownership
        if not self._is_owner(request.user, product):
            return Response(
                {"error": "Vous n'êtes pas le vendeur de ce produit."},
                status=status.HTTP_403_FORBIDDEN
            )

        files      = request.FILES.getlist("images")
        is_primary = request.data.get("is_primary", "false").lower() == "true"
        alt_text   = request.data.get("alt_text", "")

        if not files:
            return Response({"error": "Aucun fichier reçu."}, status=400)

        created = []
        for i, file in enumerate(files):
            # Vérification type MIME
            if not file.content_type.startswith("image/"):
                return Response(
                    {"error": f"{file.name} n'est pas une image."},
                    status=400
                )
            # Vérification taille (5 MB max par image)
            if file.size > 5 * 1024 * 1024:
                return Response(
                    {"error": f"{file.name} dépasse 5 MB."},
                    status=400
                )

            img = ProductImage.objects.create(
                product    = product,
                image      = file,
                is_primary = is_primary and i == 0,  # seule la 1ère est principale
                alt_text   = alt_text,
                order      = product.images.count(),
            )
            created.append(img)

        return Response(
            ProductImageSerializer(created, many=True,
                                   context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )


class ProductImageDetailView(APIView):
    """
    PATCH /products/<product_id>/images/<image_id>/   → set as primary / update alt
    DELETE /products/<product_id>/images/<image_id>/  → supprimer
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, product_id, image_id):
        image = get_object_or_404(
            ProductImage, image_id=image_id, product__product_id=product_id
        )
        if "is_primary" in request.data:
            image.is_primary = request.data["is_primary"]
        if "alt_text" in request.data:
            image.alt_text = request.data["alt_text"]
        if "order" in request.data:
            image.order = request.data["order"]
        image.save()
        return Response(ProductImageSerializer(image,
                        context={"request": request}).data)

    def delete(self, request, product_id, image_id):
        image = get_object_or_404(
            ProductImage, image_id=image_id, product__product_id=product_id
        )
        image.delete()  # supprime aussi le fichier physique
        return Response(status=status.HTTP_204_NO_CONTENT)

# ─────────────────────────────────────────────────────────────────────────────
# VENDEUR — gestion produits
# ─────────────────────────────────────────────────────────────────────────────

class SellerProductView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Liste les produits du vendeur (via ses order_items)."""
        seller = get_seller(request.user)
        if not seller:
            return Response({"error": "Profil vendeur introuvable."}, status=403)
        product_ids = (
            OrderItem.objects
            .filter(seller=seller)
            .values_list("product_id", flat=True)
            .distinct()
        )
        qs = Product.objects.filter(product_id__in=product_ids)
        return Response(ProductSerializer(qs, many=True).data)

    def post(self, request):
        """Crée un nouveau produit."""
        seller = get_seller(request.user)
        if not seller:
            return Response({"error": "Profil vendeur introuvable."}, status=403)
        s = ProductCreateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        product = s.save()
        return Response(ProductSerializer(product).data, status=201)


# ─────────────────────────────────────────────────────────────────────────────
# PANIER
# ─────────────────────────────────────────────────────────────────────────────

class CartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _cart(self, user):
        customer = get_customer(user)
        if not customer:
            return None, Response({"error": "Profil customer requis."}, status=403)
        cart, _ = Cart.objects.get_or_create(
            customer=customer, defaults={"cart_total_amount": 0}
        )
        return cart, None

    def _recalc(self, cart):
        cart.cart_total_amount = sum(i.subtotal for i in cart.cart_items.all())
        cart.save()

    def get(self, request):
        cart, err = self._cart(request.user)
        if err: return err
        return Response(CartSerializer(cart).data)

    def post(self, request):
        """Ajouter / incrémenter un article."""
        cart, err = self._cart(request.user)
        if err: return err

        product_id = request.data.get("product_id")
        quantity   = int(request.data.get("quantity", 1))
        unit_price = float(request.data.get("unit_price", 0))

        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=404)

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={
                "quantity":   quantity,
                "unit_price": unit_price,
                "subtotal":   unit_price * quantity,
            },
        )
        if not created:
            item.quantity  += quantity
            item.subtotal   = item.unit_price * item.quantity
            item.save()

        self._recalc(cart)
        return Response(CartSerializer(cart).data, status=201)

    def delete(self, request):
        """Supprimer un article."""
        cart, err = self._cart(request.user)
        if err: return err

        cart_item_id = request.data.get("cart_item_id")
        try:
            CartItem.objects.get(cart_Item_id=cart_item_id, cart=cart).delete()
        except CartItem.DoesNotExist:
            return Response({"error": "Article introuvable."}, status=404)

        self._recalc(cart)
        return Response(CartSerializer(cart).data)


# ─────────────────────────────────────────────────────────────────────────────
# COMMANDES
# ─────────────────────────────────────────────────────────────────────────────

class OrderListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        customer = get_customer(request.user)
        if not customer:
            return Response({"error": "Profil customer requis."}, status=403)
        orders = (
            customer.orders
            .prefetch_related("order_items", "payments")
            .order_by("-order_purchase_timestamp")
        )
        return Response(OrderSerializer(orders, many=True).data)

    def post(self, request):
        """Convertit le panier en commande."""
        customer = get_customer(request.user)
        if not customer:
            return Response({"error": "Profil customer requis."}, status=403)

        try:
            cart = Cart.objects.prefetch_related("cart_items__product").get(
                customer=customer
            )
        except Cart.DoesNotExist:
            return Response({"error": "Panier vide."}, status=400)

        if not cart.cart_items.exists():
            return Response({"error": "Panier vide."}, status=400)

        # Créer la commande
        order = Order.objects.create(
            customer                  = customer,
            order_status              = "pending",
            order_purchase_timestamp  = timezone.now(),
            order_estimated_delivery_date = timezone.now() + timezone.timedelta(days=7),
        )

        # Créer les OrderItems
        for seq, item in enumerate(cart.cart_items.all(), start=1):
            # Pour la démo : prend le premier seller si disponible
            first_item = item.product.order_items.first()
            seller     = first_item.seller if first_item else None

            if seller:
                OrderItem.objects.create(
                    order                      = order,
                    product                    = item.product,
                    seller                     = seller,
                    order_item_sequence_number = seq,
                    order_item_price           = item.unit_price,
                    order_item_freight_value   = 0,
                )

        # Vider le panier
        cart.cart_items.all().delete()
        cart.cart_total_amount = 0
        cart.save()

        return Response(OrderSerializer(order).data, status=201)


class OrderDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        customer = get_customer(request.user)
        try:
            order = Order.objects.prefetch_related(
                "order_items", "payments"
            ).get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)
        return Response(OrderSerializer(order).data)


# ─────────────────────────────────────────────────────────────────────────────
# PAIEMENT STRIPE
# ─────────────────────────────────────────────────────────────────────────────

class CreatePaymentIntentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id  = request.data.get("order_id")
        p_type    = request.data.get("payment_type", "credit_card")
        installs  = int(request.data.get("installments", 1))

        customer = get_customer(request.user)
        try:
            order = Order.objects.get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        total_cent = int(
            sum(i.order_item_price + i.order_item_freight_value
                for i in order.order_items.all()) * 100
        )
        if total_cent <= 0:
            return Response({"error": "Montant invalide."}, status=400)

        intent = stripe.PaymentIntent.create(
            amount   = total_cent,
            currency = "brl",
            metadata = {
                "order_id":     str(order_id),
                "customer_id":  str(customer.customer_id),
                "payment_type": p_type,
                "installments": installs,
            },
        )
        return Response({
            "client_secret": intent.client_secret,
            "amount":        total_cent / 100,
        })


class ConfirmPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        intent_id = request.data.get("payment_intent_id")
        order_id  = request.data.get("order_id")

        customer = get_customer(request.user)
        try:
            order = Order.objects.get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

        if intent.status != "succeeded":
            return Response({"error": f"Statut : {intent.status}"}, status=400)

        payment = Payment.objects.create(
            order=order,
            payment_type=intent.metadata.get("payment_type", "credit_card"),
            payment_sequential=order.payments.count() + 1,
            payment_installments=int(intent.metadata.get("installments", 1)),
            payment_value=intent.amount / 100,
            payment_timestamp=timezone.now(),
        )
        order.order_status = "approved"
        order.save()

        return Response(PaymentSerializer(payment).data, status=201)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes     = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            event = stripe.Webhook.construct_event(
                request.body,
                request.META.get("HTTP_STRIPE_SIGNATURE", ""),
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except Exception:
            return HttpResponse(status=400)

        obj      = event["data"]["object"]
        order_id = obj.get("metadata", {}).get("order_id")

        if order_id:
            status_map = {
                "payment_intent.succeeded":       "approved",
                "payment_intent.payment_failed":  "failed",
                "charge.refunded":                "refunded",
            }
            new_status = status_map.get(event["type"])
            if new_status:
                Order.objects.filter(order_id=order_id).update(order_status=new_status)

        return HttpResponse(status=200)


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ─────────────────────────────────────────────────────────────────────────────

class ReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        customer = get_customer(request.user)
        order_id = request.data.get("order")
        try:
            order = Order.objects.get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        if not order.payments.exists():
            return Response({"error": "Commande non payée."}, status=400)

        data = {**request.data, "order": str(order.order_id)}
        s    = ReviewSerializer(data=data)
        s.is_valid(raise_exception=True)
        review = s.save(review_creation_date=timezone.now())
        return Response(ReviewSerializer(review).data, status=201)


