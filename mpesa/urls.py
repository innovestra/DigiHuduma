from django.urls import path
from . import views

app_name = 'mpesa'

urlpatterns = [
    # Payment form
    path('payment/', views.MpesaPaymentView.as_view(), name='payment_form'),
    
    # STK Push endpoint - FIXED: Match the frontend URL
    path('stk-push/', views.stk_push_view, name='stk_push'),
    
    # Callback endpoint
    path('callback/', views.mpesa_callback, name='callback'),
    
    # Transaction status - FIXED: Match the frontend URL pattern  
    path('transaction/<uuid:transaction_id>/status/', views.transaction_status, name='transaction_status'),
    
    # Transaction history
    path('transactions/', views.transaction_history, name='transaction_history'),
    
    # Query status endpoint
    path('query/<str:checkout_request_id>/', views.mpesa_query_status, name='query_status'),
]