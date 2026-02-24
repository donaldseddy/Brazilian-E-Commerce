from django.urls import path
from ..views.stripe_views import (
    CreatePaymentIntentView,
    ConfirmPaymentView,
    StripeWebhookView,
    OrderPaymentsView,
    RefundPaymentView,
    CustomerOrdersView,
    CartView,
)

urlpatterns = [
    # ── Stripe ────────────────────────────────────────────────────
    path("payments/create-intent/",          CreatePaymentIntentView.as_view()),
    path("payments/confirm/",                ConfirmPaymentView.as_view()),
    path("payments/webhook/",                StripeWebhookView.as_view()),
    path("payments/<uuid:payment_id>/refund/", RefundPaymentView.as_view()),
    path("payments/order/<uuid:order_id>/",  OrderPaymentsView.as_view()),

    # ── Commandes ─────────────────────────────────────────────────
    path("orders/",                          CustomerOrdersView.as_view()),

    # ── Panier ────────────────────────────────────────────────────
    path("cart/",                            CartView.as_view()),
]
