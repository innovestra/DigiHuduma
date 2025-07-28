import json
import base64
from datetime import datetime
from django.shortcuts import render, get_object_or_404,redirect
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
import requests
from django.contrib import messages
from .models import MpesaTransaction, MpesaCallback
from .utils import generate_access_token, format_phone_number
import os
from dotenv import load_dotenv

load_dotenv()

CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')
CALLBACK_URL = os.getenv('CALLBACK_URL')
MPESA_BASE_URL = os.getenv('MPESA_BASE_URL')


def initiate_stk_push(phone_number, amount):
    """Utility function to initiate STK push"""
    try:
        url = 'https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
        token = generate_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode('utf-8')

        request_body = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerBuyGoodsOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": 9445283,
            "PhoneNumber": phone_number,
            "CallBackURL": "https://ff18444b4591.ngrok-free.app/callback/",
            "AccountReference": "INNOVESTRA TECH ENTERPRISES",
            "TransactionDesc": "Payment purchase of bingwa products",
        }

        response = requests.post(
            url,
            json=request_body,
            headers=headers,
        ).json()

        return response

    except Exception as e:
        print(f"Failed to initiate STK Push: {str(e)}")
        return e

def query_stk(checkout_request_id):
    """Utility function to query STK status"""
    try:
        print(f"DEBUG: Querying STK status for: {checkout_request_id}")
        
        access_token = generate_access_token()
        if not access_token:
            return {'success': False, 'error': 'Failed to authenticate with M-Pesa'}
        
        if not all([MPESA_SHORTCODE, MPESA_PASSKEY]):
            return {'success': False, 'error': 'Missing M-Pesa configuration'}
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode('utf-8')
        
        query_data = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = 'https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query'
        print(f"DEBUG: Querying: {url}")
        
        response = requests.post(url, json=query_data, headers=headers, timeout=30)
        response_data = response.json()
        
        print(f"DEBUG: Query response: {response_data}")
        
        return {
            'success': True,
            'response_data': response_data,
            'status_code': response.status_code
        }
        
    except requests.exceptions.RequestException as e:
        print(f"DEBUG: Query request exception: {str(e)}")
        return {'success': False, 'error': f'Network error: {str(e)}'}
    except Exception as e:
        print(f"DEBUG: Query exception: {str(e)}")
        return {'success': False, 'error': str(e)}

def process_stk_push(phone_number, amount, user=None):
    """Process STK push and create transaction record"""
    try:
        # Create transaction record
        transaction = MpesaTransaction.objects.create(
            user=user if user and user.is_authenticated else None,
            phone_number=phone_number,
            amount=amount,
            status='INITIATED'
        )
        
        url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        token = generate_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode('utf-8')

        request_body = {
            "BusinessShortCode": MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerBuyGoodsOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": 9445283,
            "PhoneNumber": phone_number,
            "CallBackURL": CALLBACK_URL,
            "AccountReference": "INNOVESTRA TECH ENTERPRISES",
            "TransactionDesc": "Payment purchase of bingwa products",
        }

        response = requests.post(url, json=request_body, headers=headers)
        response_data = response.json()
        # Update transaction with response
        transaction.result_code = response_data.get('ResponseCode', response_data.get('errorCode', 'Unknown'))
        transaction.result_desc = response_data.get('ResponseDescription', response_data.get('errorMessage', 'No description'))
        
        if response.status_code == 200 and response_data.get('ResponseCode') == '0':
            transaction.merchant_request_id = response_data.get('MerchantRequestID')
            transaction.checkout_request_id = response_data.get('CheckoutRequestID')
            transaction.status = 'PENDING'
            transaction.save()
            
            return {
                'success': True,
                'message': 'STK Push sent successfully',
                'transaction_id': str(transaction.id),
                'checkout_request_id': response_data.get('CheckoutRequestID'),
                'merchant_request_id': response_data.get('MerchantRequestID'),
                'response_data': response_data
            }
        else:
            # Handle failure - FIXED: Better error code extraction
            error_code = response_data.get('errorCode', response_data.get('ResponseCode', 'Unknown'))
            error_message = response_data.get('errorMessage', response_data.get('ResponseDescription', 'STK Push failed'))
            transaction.status = 'FAILED'
            transaction.result_code = str(error_code)
            transaction.result_desc = error_message
            transaction.save()
            
            return {
                'success': False,
                'error': error_message,
                'error_code': str(error_code),  # Ensure it's a string
                'transaction_id': str(transaction.id),
                'response_data': response_data
            }
            
    except requests.exceptions.RequestException as e:
        print(f"Network error in STK Push: {str(e)}")
        return {'success': False, 'error': f'Network error: {str(e)}'}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

@csrf_exempt
@require_http_methods(["POST"])
def stk_push_view(request):
    """Django view to handle STK push requests"""
    try:
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        amount = data.get('amount')

        if not phone_number or not amount:
            return JsonResponse({'success': False, 'error': 'Phone number and amount are required'}, status=400)
        
        # Format phone number if needed
        phone_number = format_phone_number(phone_number)
        
        # Process the STK push
        result = process_stk_push(
            phone_number=phone_number,
            amount=amount,
            user=request.user
        )
        
        # Always return result with proper structure
        return JsonResponse(result)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# Keep the old function name for backward compatibility
@csrf_exempt
@require_http_methods(["POST"])
def payment_processing(request):
    """Alias for stk_push_view for backward compatibility"""
    return stk_push_view(request)

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """Handle M-Pesa callback notifications"""
    try:
        callback_data = json.loads(request.body)
        # Extract callback information
        stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
        mpesa_receipt_number = stk_callback.get('MpesaReceiptNumber')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')
        
        print(f"DEBUG: Callback details - ResultCode: {result_code}, ResultDesc: {result_desc}")
        
        # Find the transaction
        try:
            transaction = MpesaTransaction.objects.get(
                checkout_request_id=checkout_request_id
            )
        except MpesaTransaction.DoesNotExist:
            return HttpResponse('Transaction not found', status=404)
        
        # Create callback record
        MpesaCallback.objects.create(
            transaction=transaction,
            mpesa_receipt_number=mpesa_receipt_number,
            checkout_request_id=checkout_request_id,
            result_code=str(result_code),
            result_desc=result_desc,
            callback_data=callback_data
        )
        
        # Update transaction status based on result code
        if result_code == 0:  # Success
            transaction.status = 'SUCCESS'
            transaction.result_code = str(result_code)
            transaction.result_desc = result_desc
            
            # Extract callback metadata
            callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')
                
                if name == 'MpesaReceiptNumber':
                    transaction.mpesa_receipt_number = value
                elif name == 'TransactionDate':
                    try:
                        # Convert M-Pesa date format to datetime
                        transaction.transaction_date = datetime.strptime(str(value), '%Y%m%d%H%M%S')
                    except ValueError:
                        print(f"DEBUG: Could not parse transaction date: {value}")
                    
        else:  # Failed - FIXED: Handle specific failure codes
            transaction.status = 'FAILED'
            transaction.result_code = str(result_code)
            transaction.result_desc = result_desc
        
        transaction.save()
        
        return HttpResponse('OK')
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

def transaction_status(request, transaction_id):
    """Check transaction status"""
    try:
        # Handle both authenticated and anonymous users
        if request.user.is_authenticated:
            transaction = get_object_or_404(MpesaTransaction, id=transaction_id, user=request.user)
        else:
            transaction = get_object_or_404(MpesaTransaction, id=transaction_id)
        
        # FIXED: Include result_code in response for better error handling
        return JsonResponse({
            'transaction_id': str(transaction.id),
            'status': transaction.status,
            'amount': str(transaction.amount),
            'phone_number': transaction.phone_number,
            'mpesa_receipt_number': transaction.mpesa_receipt_number,
            'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            'result_desc': transaction.result_desc,
            'result_code': transaction.result_code  # Include this for frontend error handling
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def transaction_history(request):
    """Get user's transaction history"""
    if request.user.is_authenticated:
        transactions = MpesaTransaction.objects.filter(user=request.user).order_by('-created_at')
    else:
        # For anonymous users, return empty list
        transactions = MpesaTransaction.objects.none()
    
    transactions_data = []
    for transaction in transactions:
        transactions_data.append({
            'id': str(transaction.id),
            'amount': str(transaction.amount),
            'phone_number': transaction.phone_number,
            'status': transaction.status,
            'mpesa_receipt_number': transaction.mpesa_receipt_number,
            'created_at': transaction.created_at.isoformat(),
            'transaction_date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            'result_code': transaction.result_code,
            'result_desc': transaction.result_desc
        })
    
    return JsonResponse({'transactions': transactions_data})

class MpesaPaymentView(View):
    """Render payment form"""
    
    def get(self, request):
        return render(request, 'mpesa/payment_form.html')

def mpesa_query_status(request, checkout_request_id):
    """Query STK Push status from M-Pesa API"""
    try:
        result = query_stk(checkout_request_id)
        
        if result['success']:
            return JsonResponse(result['response_data'])
        else:
            return JsonResponse({'error': result['error']}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)