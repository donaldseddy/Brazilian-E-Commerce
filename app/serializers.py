from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Customer, Seller


class CustomerRegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ["email", "first_name", "last_name", "phone_number",
                  "password", "password2"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("Mots de passe différents.")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")

        user = User(
            username=validated_data["email"],
            role=User.ROLE_CUSTOMER,
            **validated_data,
        )
        user.is_staff = False
        user.set_password(password)
        user.save()

        Customer.objects.create(user=user)
        return user


class SellerRegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ["email", "first_name", "last_name", "phone_number",
                  "password", "password2"]

    def validate(self, data):
        if data["password"] != data["password2"]:
            raise serializers.ValidationError("Mots de passe différents.")
        return data

    def create(self, validated_data):
        validated_data.pop("password2")
        password = validated_data.pop("password")

        user = User(
            username=validated_data["email"],
            role=User.ROLE_SELLER,
            **validated_data,
        )
        user.is_staff = True
        user.set_password(password)
        user.save()

        Seller.objects.create(user=user)
        return user


class TokenResponseSerializer(serializers.Serializer):
    """Retourné après login/register : access + refresh + profil."""
    access  = serializers.CharField()
    refresh = serializers.CharField()
    role    = serializers.CharField()
    email   = serializers.EmailField()
