from django.contrib import admin

from .models import (
    CustomUser,
    FinanceType
)
from investors.models import InvestorProfile
from businesses.models import BusinessProfile

admin.site.register(CustomUser)
admin.site.register(InvestorProfile)
admin.site.register(BusinessProfile)
admin.site.register(FinanceType)