import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

from ..models import Order, Payment, Cart, CartItem, OrderItem, Customer,Product

stripe.api_key = settings.STRIPE_SECRET_KEY


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_customer(user):
    """Retourne le Customer lié à l'User ou None."""
    try:
        return user.customer_profile
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# VUE 1 — Créer un PaymentIntent Stripe
# POST /payments/create-intent/
# Body : { order_id, payment_type, installments }
# ─────────────────────────────────────────────────────────────────────────────

class CreatePaymentIntentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [permissions.IsAuthenticated]

    def post(self, request):
        order_id      = request.data.get("order_id")
        payment_type  = request.data.get("payment_type", "credit_card")
        installments  = int(request.data.get("installments", 1))

        # Récupérer la commande et vérifier l'appartenance
        try:
            customer = _get_customer(request.user)
            order    = Order.objects.get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        # Calculer le montant total depuis les OrderItems
        items      = order.order_items.all()
        total_cent = int(
            sum(i.order_item_price + i.order_item_freight_value for i in items) * 100
        )

        if total_cent <= 0:
            return Response({"error": "Montant invalide."}, status=400)

        # Stripe : PaymentIntent
        intent = stripe.PaymentIntent.create(
            amount      = total_cent,
            currency    = "brl",
            metadata    = {
                "order_id":     str(order_id),
                "customer_id":  str(customer.customer_id),
                "payment_type": payment_type,
                "installments": installments,
            },
            description = f"Commande #{str(order_id)[:8]}",
        )

        return Response({
            "client_secret":  intent.client_secret,
            "payment_intent": intent.id,
            "amount":         total_cent / 100,
            "currency":       "brl",
        })


# ─────────────────────────────────────────────────────────────────────────────
# VUE 2 — Confirmer le paiement (après succès Stripe côté client)
# POST /payments/confirm/
# Body : { payment_intent_id, order_id }
# ─────────────────────────────────────────────────────────────────────────────

class ConfirmPaymentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [permissions.IsAuthenticated]

    def post(self, request):
        intent_id = request.data.get("payment_intent_id")
        order_id  = request.data.get("order_id")

        try:
            customer = _get_customer(request.user)
            order    = Order.objects.get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        # Vérifier le statut chez Stripe
        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

        if intent.status != "succeeded":
            return Response(
                {"error": f"Paiement non confirmé. Statut : {intent.status}"},
                status=400,
            )

        # Numéro de séquence du paiement
        seq = order.payments.count() + 1

        # Créer le Payment en base
        payment = Payment.objects.create(
            order                = order,
            payment_type         = intent.metadata.get("payment_type", "credit_card"),
            payment_sequential   = seq,
            payment_installments = int(intent.metadata.get("installments", 1)),
            payment_value        = intent.amount / 100,
        )

        # Mettre à jour le statut de la commande
        order.order_status = "approved"
        order.save()

        return Response({
            "payment_id":  str(payment.payment_id),
            "order_id":    str(order.order_id),
            "status":      "approved",
            "amount":      float(payment.payment_value),
        }, status=201)


# ─────────────────────────────────────────────────────────────────────────────
# VUE 3 — Webhook Stripe (événements asynchrones)
# POST /payments/webhook/
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        payload    = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            return HttpResponse(status=400)

        # ── Paiement réussi ──────────────────────────────────────
        if event["type"] == "payment_intent.succeeded":
            intent   = event["data"]["object"]
            order_id = intent["metadata"].get("order_id")
            if order_id:
                Order.objects.filter(order_id=order_id).update(order_status="approved")

        # ── Paiement échoué ──────────────────────────────────────
        elif event["type"] == "payment_intent.payment_failed":
            intent   = event["data"]["object"]
            order_id = intent["metadata"].get("order_id")
            if order_id:
                Order.objects.filter(order_id=order_id).update(order_status="failed")

        # ── Remboursement ────────────────────────────────────────
        elif event["type"] == "charge.refunded":
            charge   = event["data"]["object"]
            order_id = charge.get("metadata", {}).get("order_id")
            if order_id:
                Order.objects.filter(order_id=order_id).update(order_status="refunded")

        return HttpResponse(status=200)


# ─────────────────────────────────────────────────────────────────────────────
# VUE 4 — Historique des paiements d'une commande
# GET /payments/order/<order_id>/
# ─────────────────────────────────────────────────────────────────────────────

class OrderPaymentsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        try:
            customer = _get_customer(request.user)
            order    = Order.objects.get(order_id=order_id, customer=customer)
        except Order.DoesNotExist:
            return Response({"error": "Commande introuvable."}, status=404)

        payments = order.payments.all().order_by("payment_sequential")
        data = [
            {
                "payment_id":          str(p.payment_id),
                "payment_type":        p.payment_type,
                "payment_sequential":  p.payment_sequential,
                "payment_installments": p.payment_installments,
                "payment_value":       float(p.payment_value),
            }
            for p in payments
        ]
        return Response({
            "order_id":     str(order.order_id),
            "order_status": order.order_status,
            "payments":     data,
            "total":        sum(p["payment_value"] for p in data),
        })


# ─────────────────────────────────────────────────────────────────────────────
# VUE 5 — Remboursement
# POST /payments/<payment_id>/refund/
# ─────────────────────────────────────────────────────────────────────────────

class RefundPaymentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [permissions.IsAuthenticated]

    def post(self, request, payment_id):
        try:
            customer = _get_customer(request.user)
            payment  = Payment.objects.get(
                payment_id=payment_id,
                order__customer=customer,
            )
        except Payment.DoesNotExist:
            return Response({"error": "Paiement introuvable."}, status=404)

        # Retrouver le PaymentIntent via Stripe
        try:
            intents = stripe.PaymentIntent.list(limit=10)
            target  = next(
                (i for i in intents.data
                 if i.metadata.get("order_id") == str(payment.order.order_id)),
                None,
            )
            if not target:
                return Response({"error": "PaymentIntent Stripe introuvable."}, status=404)

            refund = stripe.Refund.create(
                payment_intent = target.id,
                amount         = int(payment.payment_value * 100),
            )
        except stripe.error.StripeError as e:
            return Response({"error": str(e)}, status=400)

        payment.order.order_status = "refunded"
        payment.order.save()

        return Response({
            "refund_id": refund.id,
            "status":    refund.status,
            "amount":    refund.amount / 100,
        })


# ─────────────────────────────────────────────────────────────────────────────
# VUE 6 — Commandes du customer connecté
# GET /orders/
# ─────────────────────────────────────────────────────────────────────────────

class CustomerOrdersView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [permissions.IsAuthenticated]

    def get(self, request):
        customer = _get_customer(request.user)
        if not customer:
            return Response({"error": "Profil customer introuvable."}, status=404)

        orders = customer.orders.prefetch_related("order_items", "payments").order_by(
            "-order_purchase_timestamp"
        )
        data = []
        for o in orders:
            items = [
                {
                    "product_id": str(i.product_id),
                    "price":      float(i.order_item_price),
                    "freight":    float(i.order_item_freight_value),
                    "seq":        i.order_item_sequence_number,
                }
                for i in o.order_items.all()
            ]
            data.append({
                "order_id":       str(o.order_id),
                "order_status":   o.order_status,
                "purchase_date":  o.order_purchase_timestamp.isoformat() if o.order_purchase_timestamp else None,
                "items":          items,
                "items_count":    len(items),
                "total":          sum(i["price"] + i["freight"] for i in items),
                "paid":           o.payments.count() > 0,
            })
        return Response(data)


# ─────────────────────────────────────────────────────────────────────────────
# VUE 7 — Panier : voir / ajouter / supprimer
# GET|POST|DELETE /cart/
# ─────────────────────────────────────────────────────────────────────────────

class CartView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes     = [permissions.IsAuthenticated]

    def _get_or_create_cart(self, customer):
        cart, _ = Cart.objects.get_or_create(
            customer=customer,
            defaults={"cart_total_amount": 0},
        )
        return cart

    def get(self, request):
        customer = _get_customer(request.user)
        if not customer:
            return Response({"error": "Profil customer introuvable."}, status=404)

        cart  = self._get_or_create_cart(customer)
        items = cart.cart_items.select_related("product").all()
        data  = [
            {
                "cart_item_id": str(i.cart_Item_id),
                "product_id":   str(i.product.product_id),
                "quantity":     i.quantity,
                "unit_price":   float(i.unit_price),
                "subtotal":     float(i.subtotal),
            }
            for i in items
        ]
        return Response({
            "cart_id": str(cart.cart_id),
            "items":   data,
            "total":   float(cart.cart_total_amount),
        })

    def post(self, request):
        """Ajouter un article."""
        customer   = _get_customer(request.user)
        product_id = request.data.get("product_id")
        quantity   = int(request.data.get("quantity", 1))

        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Produit introuvable."}, status=404)

        cart       = self._get_or_create_cart(customer)
        unit_price = 0   # à remplacer par ton champ prix quand disponible
        subtotal   = unit_price * quantity

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={"quantity": quantity, "unit_price": unit_price, "subtotal": subtotal},
        )
        if not created:
            item.quantity  += quantity
            item.subtotal   = item.unit_price * item.quantity
            item.save()

        cart.cart_total_amount = sum(
            i.subtotal for i in cart.cart_items.all()
        )
        cart.save()

        return Response({"message": "Article ajouté.", "cart_id": str(cart.cart_id)}, status=201)

    def delete(self, request):
        """Supprimer un article du panier."""
        customer     = _get_customer(request.user)
        cart_item_id = request.data.get("cart_item_id")
        try:
            cart = Cart.objects.get(customer=customer)
            item = CartItem.objects.get(cart_Item_id=cart_item_id, cart=cart)
            item.delete()
            cart.cart_total_amount = sum(i.subtotal for i in cart.cart_items.all())
            cart.save()
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response({"error": "Article introuvable."}, status=404)

        return Response({"message": "Article supprimé."})
