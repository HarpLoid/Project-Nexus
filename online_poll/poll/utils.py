import hashlib
import random
import string
from uuid import uuid4
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import AccessToken

# Generate a random temporary password
def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

# Generate anon_id for a voter
def generate_anon_id(email, poll_id):
    hash_input = f"{email}-{poll_id}-{uuid4()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

# Create a JWT token for a voter
def create_voter_token(voter):
    token = AccessToken()
    token['voter_id'] = str(voter.voter_id)
    token['poll_id'] = str(voter.poll.poll_id)
    return str(token)

# Send voter credentials via SendGrid
def send_voter_credentials_email(email, temp_password, login_token, poll):
    login_link = f"{settings.FRONTEND_URL}/vote?token={login_token}"
    content = f"""
You have been invited to vote in '{poll.title}'.

Temporary Password: {temp_password}
Login Link: {login_link}

Use the link to access and cast your vote.
"""
    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=email,
        subject=f"Voting Access for Poll: {poll.title}",
        plain_text_content=content
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(message)
        print(f"Email successfully sent to {email}")
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")
        raise e