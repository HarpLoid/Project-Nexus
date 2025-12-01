from django.contrib.auth.hashers import make_password
from poll.models import Voter
from poll.utils import generate_temp_password, generate_anon_id, send_voter_credentials_email

def create_voter_for_poll(poll, email, send_email=True):
    """
    Create or get a Voter for `poll` and `email`.
    
    Returns:
        voter: Voter instance
        created: True if newly created, False if already existed
        plain_pw: The plain temporary password if created or regenerated
    """
    # Generate a new temporary password
    plain_pw = generate_temp_password()

    # Generate a new anon_id
    anon = generate_anon_id(email, str(poll.poll_id))

    # Hash the password before storing
    hashed_pw = make_password(plain_pw)

    # Try to get existing voter
    voter, created = Voter.objects.get_or_create(
        poll=poll,
        email=email,
        defaults={
            "anon_id": anon,
            "temp_password": hashed_pw,
        }
    )

    # If voter exists and has not voted, allow password regeneration
    if not created and not voter.has_voted:
        voter.temp_password = hashed_pw
        voter.anon_id = anon  # optionally regenerate anon_id for extra security
        voter.save(update_fields=["temp_password", "anon_id"])
        created = False  # still not "newly created", but password regenerated

    # Send credentials via email if requested
    if send_email:
        send_voter_credentials_email(
            email=email,
            temp_password=plain_pw,
            login_token=voter.anon_id,
            poll=poll
        )

    return voter, created, plain_pw
