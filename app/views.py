from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, login, logout

from .serializers import CustomerRegisterSerializer, SellerRegisterSerializer
from .models import User


def get_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access":  str(refresh.access_token),
        "role":    user.role,
        "email":   user.email,
    }


class CustomerRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = CustomerRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(get_tokens(user), status=status.HTTP_201_CREATED)


class SellerRegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = SellerRegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        return Response(get_tokens(user), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Login unifié Customer + Seller → JWT + Session."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email    = request.data.get("email")
        password = request.data.get("password")

        # authenticate utilise USERNAME_FIELD=email défini dans User
        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {"error": "Identifiants invalides."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        login(request, user)   # session Django
        return Response(get_tokens(user), status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
        except Exception:
            pass
        logout(request)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    """Retourne le profil de l'utilisateur connecté."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        data = {
            "email":        user.email,
            "role":         user.role,
            "first_name":   user.first_name,
            "last_name":    user.last_name,
            "phone_number": user.phone_number,
            "city":         user.city,
            "state":        user.state,
            "address":      user.address,
        }

        # Ajout l'id spécifique au rôle
        if user.is_customer:
            try:
                data["customer_id"] = str(user.customer_profile.customer_id)
            except user.__class__.customer_profile.RelatedObjectDoesNotExist:
                data["customer_id"] = None

        elif user.is_seller:
            try:
                data["seller_id"] = str(user.seller_profile.seller_id)
            except user.__class__.seller_profile.RelatedObjectDoesNotExist:
                data["seller_id"] = None

        return Response(data)
