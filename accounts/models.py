from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ("investor", "Investor"),
        ("business", "Business"),
        ("consulting_partner", "Consulting Partner"),
        ("internal", "Internal"),
    ]

    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=30, choices=USER_TYPE_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class FinanceType(models.Model):
    name = models.CharField(max_length=100,unique=True)

    def __str__(self):
        return self.name



