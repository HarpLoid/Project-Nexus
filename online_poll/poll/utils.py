from django.core.mail import send_mail
from django.conf import settings

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
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
    )

