from django.contrib import admin
from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'policy', 'submitted_by', 'claim_amount', 'status', 'fraud_flag', 'date_filed')
    list_filter = ('status', 'fraud_flag')
    search_fields = ('policy__policy_number', 'submitted_by__username')
    readonly_fields = ('date_filed', 'fraud_flag', 'fraud_reason', 'reviewed_by', 'reviewed_at')
