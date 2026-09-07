from django.contrib import admin
from .models import Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'user', 'policy_type', 'coverage_amount', 'status', 'created_at')
    list_filter = ('policy_type', 'status')
    search_fields = ('policy_number', 'user__username')
    readonly_fields = ('policy_number', 'created_at')
