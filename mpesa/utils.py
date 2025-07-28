import base64
import requests
from django.conf import settings
import os
from dotenv import load_dotenv

load_dotenv()

CONSUMER_KEY = os.getenv('CONSUMER_KEY')
CONSUMER_SECRET = os.getenv('CONSUMER_SECRET')
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY')
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE')  # FIXED: Was using CONSUMER_KEY
CALLBACK_URL = os.getenv('CALLBACK_URL')
MPESA_BASE_URL = os.getenv('MPESA_BASE_URL')

def generate_access_token():
    """Generate M-Pesa access token"""
    try:
        # Create basic auth string
        auth_string = f"{CONSUMER_KEY}:{CONSUMER_SECRET}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        
        # Set headers
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json'
        }
        
        url = 'https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
        
        # Make request
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json().get('access_token')
        else:
            print(f"Failed to get access token: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error generating access token: {e}")
        return None

def format_phone_number(phone_number):
    """Format phone number to M-Pesa required format (254XXXXXXXXX)"""
    # Remove any spaces, hyphens, or other characters
    phone = ''.join(filter(str.isdigit, phone_number))
    
    # Handle different formats
    if phone.startswith('0'):
        # Convert 0XXXXXXXXX to 254XXXXXXXXX
        phone = '254' + phone[1:]
    elif phone.startswith('254'):
        # Already in correct format
        pass
    elif phone.startswith('+254'):
        # Remove the + sign
        phone = phone[1:]
    elif len(phone) == 9:
        # Add country code
        phone = '254' + phone
    
    return phone

def validate_phone_number(phone_number):
    """Validate Kenyan phone number"""
    formatted = format_phone_number(phone_number)
    
    # Check if it's a valid Kenyan number
    if len(formatted) != 12 or not formatted.startswith('254'):
        return False
    
    # Check if it's a valid mobile number (starts with 254 + 7)
    if not formatted.startswith('2547'):
        return False
    
    return True