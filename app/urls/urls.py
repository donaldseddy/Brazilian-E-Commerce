from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from ..views.views import (
    CartView,
    CategoryListView,
    CreateCheckoutSessionView,
    LoginView,
    LogoutView,
    MeView,
    OrderDetailView,
    OrderListView,
    ProductDetailView,
    ProductImageDetailView,
    ProductImageUploadView,
    ProductListView,
    RegisterView,
    ReviewView,
    SellerProductView,
    StripeWebhookView,
)

urlpatterns = [
    # ── Auth ─────────────────────────────────────────────────────
    path("auth/register/",          RegisterView.as_view()),
    path("auth/login/",             LoginView.as_view()),
    path("auth/logout/",            LogoutView.as_view()),
    path("auth/token/refresh/",     TokenRefreshView.as_view()),
    path("auth/me/",                MeView.as_view()),

    # ── Catalogue ─────────────────────────────────────────────────
    path("categories/",             CategoryListView.as_view()),
    path("products/",               ProductListView.as_view()),
    path("products/<uuid:product_id>/", ProductDetailView.as_view()),
    path("products/<uuid:product_id>/images/", ProductImageUploadView.as_view()),
    path("products/<uuid:product_id>/images/<uuid:image_id>/",ProductImageDetailView.as_view()),

    # ── Vendeur ──────────────────────────────────────────────────
    path("seller/products/",        SellerProductView.as_view()),

    # ── Panier ───────────────────────────────────────────────────
    path("cart/",                   CartView.as_view()),

    # ── Commandes ─────────────────────────────────────────────────
    path("orders/",                 OrderListView.as_view()),
    path("orders/<uuid:order_id>/", OrderDetailView.as_view()),

    # ── Paiement ──────────────────────────────────────────────────

    path("payments/webhook/",       StripeWebhookView.as_view()),
    path("payments/create-checkout-session/", CreateCheckoutSessionView.as_view(),),


    # ── Reviews ───────────────────────────────────────────────────
    path("reviews/",                ReviewView.as_view()),
]
