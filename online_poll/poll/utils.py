from django.core.mail import send_mail
from django.conf import settings
import hashlib
import random
import string
from uuid import uuid4

def send_voter_credentials_email(email, temp_password, login_token, poll):
    subject = f"Voting Access for Poll: {poll.title}"

    login_link = f"{settings.FRONTEND_URL}/vote?token={login_token}"

    message = (
        f"You have been invited to vote in '{poll.title}'.\n\n"
        f"Temporary Password: {temp_password}\n"
        f"Login Link: {login_link}\n\n"
        f"Use the link to access and cast your vote."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )

def generate_anon_id(email, poll_id):
    """Generate a consistent anon_id based on email and poll_id"""
    hash_input = f"{email}-{poll_id}-{uuid4()}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def generate_temp_password():
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(10))

