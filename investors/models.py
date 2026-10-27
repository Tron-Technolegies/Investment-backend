from django.db import models
from accounts.models import CustomUser

class InvestorProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='investor_profile')

    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100,blank=True)
    country_of_residence = models.CharField(max_length=100,blank=True)
    place_of_birth = models.CharField(max_length=100,blank=True)
    mobile_number = models.CharField(max_length=20)
    marketing_consent = models.BooleanField(default=False)
    terms_accepted = models.BooleanField(default=False)

    referral_source = models.CharField(max_length=255, blank=True, null=True)

    organization = models.CharField(max_length=255,blank=True,null=True)
    investor_type = models.CharField( max_length=50,
        choices=[
            ("individual", "Individual"),
            ("angel_investor", "Angel Investor"),
            ("vc_fund", "VC Fund"),
            ("family_office", "Family Office"),
            ("hni", "HNI"),
        ],
        default="individual"
    )

    status = models.CharField(max_length=30,
        choices=[
            ("active", "Active"),
            ("approved", "Approved"),
            ("under_review", "Under Review"),
            ("inactive", "Inactive")
        ],
        default="active"
    )


    def __str__(self):
        return self.full_name
