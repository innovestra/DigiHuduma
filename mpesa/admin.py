# admin.py
from django.contrib import admin
from .models import MpesaTransaction, MpesaCallback

@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'phone_number', 
        'amount', 'status', 'mpesa_receipt_number', 'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['phone_number', 'mpesa_receipt_number', 'account_reference']
    readonly_fields = [
        'id', 'merchant_request_id', 'checkout_request_id', 
        'mpesa_receipt_number', 'transaction_date', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'phone_number', 'amount')
        }),
        ('Transaction Details', {
            'fields': ('account_reference', 'transaction_desc', 'status')
        }),
        ('M-Pesa Details', {
            'fields': (
                'merchant_request_id', 'checkout_request_id', 
                'mpesa_receipt_number', 'transaction_date'
            )
        }),
        ('Result Information', {
            'fields': ('result_code', 'result_desc')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of successful transactions
        if obj and obj.status == 'SUCCESS':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(MpesaCallback)
class MpesaCallbackAdmin(admin.ModelAdmin):
    list_display = [
        'transaction', 'merchant_request_id', 'checkout_request_id', 
        'result_code', 'created_at'
    ]
    list_filter = ['result_code', 'created_at']
    search_fields = ['merchant_request_id', 'checkout_request_id']
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        # Callbacks are created automatically
        return False
    
    def has_change_permission(self, request, obj=None):
        # Callbacks shouldn't be modified
        return False
