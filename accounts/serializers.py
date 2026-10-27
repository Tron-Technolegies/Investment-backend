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
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    confirm_email = serializers.EmailField(required=True)

    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    full_name = serializers.CharField(max_length=255, required=True)
    date_of_birth = serializers.DateField(required=True)

    nationality = serializers.CharField(max_length=100, required=True)
    country_of_residence = serializers.CharField(max_length=100, required=True)
    place_of_birth = serializers.CharField(max_length=100, required=True)

    mobile_number = serializers.CharField(max_length=20, required=True)

    marketing_consent = serializers.BooleanField(required=True)
    terms_accepted = serializers.BooleanField(required=True)

    referral_source = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, data):
        if data['email'].lower() != data['confirm_email'].lower():
            raise serializers.ValidationError({
                "confirm_email" : "Email address do not match"
            })

        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password" : "Password do not match"
            })

        if not data["terms_accepted"]:
            raise serializers.ValidationError({
                "terms_accepted" : "You must accept the Terms & Privacy Policy."
            })

        if CustomUser.objects.filter(
            email__iexact=data['email']
        ).exists():
            raise serializers.ValidationError({
                "email" : "A account with this email already exists."
            })

        if CustomUser.objects.filter(
            username__iexact=data['username']
        ).exists():
            raise serializers.ValidationError({
                "username" : "A account with this username already exists."
            })

        return data

    def create(self, validated_data):
        validated_data.pop ("confirm_email")
        validated_data.pop ("confirm_password")

        password = validated_data.pop("password")

        full_name = validated_data.pop("full_name")
        date_of_birth = validated_data.pop("date_of_birth")
        nationality = validated_data.pop("nationality")
        country_of_residence = validated_data.pop("country_of_residence")
        place_of_birth = validated_data.pop("place_of_birth")
        mobile_number = validated_data.pop("mobile_number")
        marketing_consent = validated_data.pop("marketing_consent")
        terms_accepted = validated_data.pop("terms_accepted")
        referral_source = validated_data.pop("referral_source", "")

        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=password,
            user_type="investor"
        )

        InvestorProfile.objects.create(

            user=user,
            full_name=full_name,
            date_of_birth=date_of_birth,
            nationality=nationality,
            country_of_residence=country_of_residence,
            place_of_birth=place_of_birth,
            mobile_number=mobile_number,
            marketing_consent=marketing_consent,
            terms_accepted=terms_accepted,
            referral_source=referral_source,
        )

        return user

class BusinessRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    confirm_email = serializers.EmailField(required=True)

    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    business_trade_name = serializers.CharField(
        max_length=255,
        required=True
    )

    business_incorporation_date = serializers.DateField(
        required=True
    )

    finance_type = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )

    finance_amount = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=True
    )

    customers = serializers.CharField(required=True)

    funding_purpose = serializers.CharField(
        max_length=255,
        required=True
    )

    preferred_funding_term = serializers.CharField(
        max_length=100,
        required=True
    )


    def validate(self, data):
        if data["email"].lower() != data["confirm_email"].lower():
            raise serializers.ValidationError({
                "confirm_email": "Email addresses do not match."
            })

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

        if CustomUser.objects.filter(
            username__iexact=data["username"]
        ).exists():
            raise serializers.ValidationError({
                "username": "An account with this username already exists."
            })

        if not data["finance_type"]:
            raise serializers.ValidationError({
                "finance_type": "Select at least one finance type."
            })

        return data



    def create(self, validated_data):
        validated_data.pop("confirm_email")
        validated_data.pop("confirm_password")

        password = validated_data.pop("password")
        finance_type_ids = validated_data.pop("finance_type")

        user = CustomUser.objects.create_user(
            username=validated_data.pop("username"),
            email=validated_data.pop("email"),
            password=password,
            user_type="business",
        )

        business_profile = BusinessProfile.objects.create(
            user=user,
            **validated_data
        )

        business_profile.finance_type.set(finance_type_ids)


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