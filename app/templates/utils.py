import os
import resend
import secrets

resend.api_key = os.environ.get("RESEND_API_KEY")

def send_verification_email(user_email, user_name):
    token = secrets.token_urlsafe(32)
    # ... (the rest of your function code here) ...
    return token # Return the token so you can save it to your DB