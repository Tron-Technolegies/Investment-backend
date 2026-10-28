from requests import Response
from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes,force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser,FinanceType
from investors.models import InvestorProfile
from businesses.models import BusinessProfile
from rest_framework_simplejwt.tokens import RefreshToken


class InvestorRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    organization = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True
    )
    investor_type = serializers.ChoiceField(
        choices=InvestorProfile._meta.get_field("investor_type").choices
    )
    email = serializers.EmailField()
    mobile_number = serializers.CharField(max_length=20)
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        if CustomUser.objects.filter(
            email__iexact=data["email"]
        ).exists():
            raise serializers.ValidationError({
                "email": "An account with this email already exists."
            })

        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        email = validated_data["email"]

        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            user_type="investor"
        )

        InvestorProfile.objects.create(
            user=user,
            full_name=validated_data["full_name"],
            organization=validated_data.get("organization", ""),
            investor_type=validated_data["investor_type"],
            mobile_number=validated_data["mobile_number"]
        )

        return user



class BusinessRegistrationSerializer(serializers.Serializer):
    business_trade_name = serializers.CharField(max_length=255)

    business_type = serializers.ChoiceField(
        choices=BusinessProfile.BUSINESS_TYPE_CHOICES
    )

    sector = serializers.ChoiceField(
        choices=BusinessProfile.SECTOR_CHOICES,
        required=False,
        allow_blank=True
    )

    cin_reg_no = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    city_hq = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )

    email = serializers.EmailField()

    mobile_number = serializers.CharField(max_length=20)

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        email = data["email"].strip().lower()

        if CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({
                "email": "An account with this email already exists."
            })

        if CustomUser.objects.filter(username__iexact=email).exists():
            raise serializers.ValidationError({
                "email": "This email is already used as a username."
            })

        data["email"] = email
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")

        email = validated_data.pop("email")

        user = CustomUser.objects.create_user(
            username=email,
            email=email,
            password=password,
            user_type="business"
        )

        BusinessProfile.objects.create(
            user=user,
            full_name="",
            business_trade_name=validated_data["business_trade_name"],
            business_type=validated_data["business_type"],
            sector=validated_data.get("sector") or None,
            cin_reg_no=validated_data.get("cin_reg_no") or None,
            city_hq=validated_data.get("city_hq") or None,
            mobile_number=validated_data["mobile_number"]
        )

        return user



class FinanceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinanceType
        fields = ['id', 'name']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True
    )
    user_type = serializers.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        required=True
    )

    def validate(self, data):
        email = data["email"]
        password = data["password"]
        user_type = data["user_type"]

        try:
            user = CustomUser.objects.get(email__iexact=email)
            print("LOGIN DATABASE:", user._state.db)
            print("LOGIN USER ID:", user.pk)
            print("LOGIN USER TYPE:", repr(user.user_type))
            print("LOGIN IS SUPERUSER:", user.is_superuser)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                "email": "Invalid email or password."
            })

        if not user.check_password(password):
            raise serializers.ValidationError({
                "email": "Invalid email or password."
            })
        

        print("LOGIN EMAIL:", repr(email))
        print("DATABASE USER TYPE:", repr(user.user_type))
        print("REQUEST USER TYPE:", repr(user_type))

        if user.user_type != user_type:
            raise serializers.ValidationError({
                "user_type": "This account does not belong to this user type."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "email": "This account is inactive."
            })

        if user.user_type == "investor":
            try:
                investor_profile = user.investor_profile
            except InvestorProfile.DoesNotExist:
                raise serializers.ValidationError({
                    "detail": "Investor profile not found."
                })

            if investor_profile.status == "inactive":
                raise serializers.ValidationError({
                    "detail": "Your investor account is inactive."
                })
        data["user"] = user

        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, data):
        email = data["email"]

        try:
            user = CustomUser.objects.get(email__iexact=email)
        except CustomUser.DoesNotExist:
            # Don't reveal whether the email exists
            return data

        if not user.is_active:
            return data

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_link = (
            f"http://localhost:3000/reset-password/{uid}/{token}/"
        )

        send_mail(
            subject="Password Reset Request",
            message=(
                "You requested a password reset.\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_link}\n\n"
                "If you did not request this, you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return data

    def create(self, validated_data):
        return validated_data



class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    password = serializers.CharField(
        write_only=True,
        required=True
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True
    )
    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })
        try:
            uid = force_bytes(urlsafe_base64_decode(data["uid"]))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            raise serializers.ValidationError({
                "uid": "Invalid password reset link."
            })

        if not default_token_generator.check_token(user, data["token"]):
            raise serializers.ValidationError({
                "token": "Invalid or expired password reset token."
            })

        data["user"] = user
        return data

    def create(self, validated_data):
        user = validated_data["user"]
        password = validated_data["password"]

        user.set_password(password)
        user.save(update_fields=["password"])

        return user

class SetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField(required=True)
    token = serializers.CharField(required=True)

    password = serializers.CharField(
        write_only=True,
        required=True
    )

    confirm_password = serializers.CharField(
        write_only=True,
        required=True
    )

    def validate(self, data):

        # Check whether passwords match
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        # Decode user ID and find the user
        try:
            uid = force_str(
                urlsafe_base64_decode(data["uid"])
            )

            user = CustomUser.objects.get(pk=uid)

        except (
            TypeError,
            ValueError,
            OverflowError,
            CustomUser.DoesNotExist
        ):
            raise serializers.ValidationError({
                "uid": "Invalid password setup link."
            })

        # Validate setup token
        if not default_token_generator.check_token(
            user,
            data["token"]
        ):
            raise serializers.ValidationError({
                "token": "Invalid or expired password setup link."
            })
        if user.has_usable_password():
            raise serializers.ValidationError({
            "token": "This password setup link has already been used."
        })

        data["user"] = user

        return data

    def create(self, validated_data):

        user = validated_data["user"]
        password = validated_data["password"]

        user.set_password(password)

        user.save(update_fields=["password"])

        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate(self, data):
        try:
            RefreshToken(data["refresh"])
        except Exception as e:
            print("REFRESH TOKEN ERROR:", type(e).__name__, str(e))
            raise serializers.ValidationError({
                "refresh": "Invalid refresh token."
            })

        return data

    def create(self, validated_data):
        try:
            token = RefreshToken(validated_data["refresh"])
            token.blacklist()
        except Exception as e:
            print("BLACKLIST ERROR:", type(e).__name__, str(e))
            raise serializers.ValidationError({
                "refresh": "Logout failed."
            })

        return validated_data