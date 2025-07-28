# models.py - FIXED VERSION
from django.db import models
from django.contrib.auth.models import User
import uuid

class MpesaTransaction(models.Model):
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),  # Added
        ('TIMEOUT', 'Timeout'),      # Added
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    account_reference = models.CharField(max_length=100)
    transaction_desc = models.CharField(max_length=200)
    
    # M-Pesa specific fields
    merchant_request_id = models.CharField(max_length=100, blank=True, null=True)
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    result_code = models.CharField(max_length=10, blank=True, null=True)
    result_desc = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.mpesa_receipt_number or 'N/A'} - {self.phone_number} - {self.amount}"

class MpesaCallback(models.Model):
    """Store raw callback data from M-Pesa"""
    transaction = models.ForeignKey(MpesaTransaction, on_delete=models.CASCADE, related_name='callbacks')
    merchant_request_id = models.CharField(max_length=100)
    checkout_request_id = models.CharField(max_length=100)
    result_code = models.CharField(max_length=10)
    result_desc = models.TextField()
    callback_data = models.JSONField()  # Store the full callback JSON
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['checkout_request_id']),
            models.Index(fields=['result_code']),
        ]
    
    def __str__(self):
        return f"Callback for {self.transaction.id} - Code: {self.result_code}"