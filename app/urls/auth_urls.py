from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from app.views.views import (
    CustomerRegisterView,
    SellerRegisterView,
    LoginView,
    LogoutView,
    MeView,
)

urlpatterns = [
    # ── Inscription ───────────────────────────────────────────────
    path("register/customer/", CustomerRegisterView.as_view()),
    path("register/seller/",   SellerRegisterView.as_view()),

    # ── Login / Logout ────────────────────────────────────────────
    path("login/",   LoginView.as_view()),
    path("logout/",  LogoutView.as_view()),

    # ── JWT refresh ───────────────────────────────────────────────
    path("token/refresh/", TokenRefreshView.as_view()),

    # ── OAuth2 (allauth) ──────────────────────────────────────────
    path("social/", include("allauth.urls")),

    # ── Profil courant ────────────────────────────────────────────
    path("me/", MeView.as_view()),
]
