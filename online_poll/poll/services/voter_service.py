from django.contrib.auth.hashers import make_password
from poll.models import Voter
from poll.utils import generate_temp_password, generate_anon_id, send_voter_credentials_email

def create_voter_for_poll(poll, email, send_email=True):
    """
    Create or get a Voter for `poll` and `email`.
    Returns (voter, created, plain_temp_password_or_None)
    - If created True -> returns the plaintext temp password (so controller can email or include in response)
    - If already exists -> returns None for plain password
    """
    # generate temp password plaintext
    plain_pw = generate_temp_password()

    # generate anon_id
    anon = generate_anon_id(email, str(poll.poll_id))

    # hash before saving
    hashed_pw = make_password(plain_pw)

    voter, created = Voter.objects.get_or_create(
        poll=poll,
        email=email,
        defaults={
            "anon_id": anon,
            "temp_password": hashed_pw,  # store hashed
        }
    )

    if not created and (not voter.has_voted):
        voter.anon_id = anon
        voter.temp_password = hashed_pw
        voter.save(update_fields=["temp_password", "anon_id"])

    # send email if requested and newly created (we only email when created)
    if send_email and created:
        send_voter_credentials_email(
            email=email,
            temp_password=plain_pw,
            login_token=voter.anon_id,
            poll=poll
        )

    return voter, created, plain_pw
