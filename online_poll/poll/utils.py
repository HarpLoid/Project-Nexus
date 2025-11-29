from django.conf import settings
import hashlib
import random
import string
from uuid import uuid4
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def send_voter_credentials_email(email, temp_password, login_token, poll):
    """
    Sends voter credentials using SendGrid Web API.
    """
    login_link = f"{settings.FRONTEND_URL}/vote?token={login_token}"

    content = f"""
You have been invited to vote in '{poll.title}'.

Voter Email: {email}
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

def generate_anon_id(email, poll_id):
    """Generate a consistent anon_id based on email and poll_id"""
    hash_input = f"{email}-{poll_id}-{uuid4()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def generate_temp_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

