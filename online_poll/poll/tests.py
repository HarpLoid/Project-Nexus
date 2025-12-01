from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from uuid import uuid4
from poll.models import Poll, PollOption, Voter, Vote, CustomUser as User
from unittest.mock import patch

class PollAndVoterTests(TestCase):

    def setUp(self):
        self.client = APIClient()

        # Patch send_voter_credentials_email globally for tests
        patcher = patch("poll.utils.send_voter_credentials_email")
        self.mock_send_email = patcher.start()
        self.addCleanup(patcher.stop)

        # Create poll creator
        self.user = User.objects.create_user(email="creator@test.com", password="password123")
        self.client.force_authenticate(user=self.user)

        # Create poll
        self.poll = Poll.objects.create(
            creator=self.user,
            title="Favorite Fruit?",
            description="Choose your favorite",
            poll_type=Poll.SINGLE_CHOICE,
            allow_anonymous=True
        )

        # Options
        self.option1 = PollOption.objects.create(poll=self.poll, text="Apple")
        self.option2 = PollOption.objects.create(poll=self.poll, text="Banana")

        # URLs
        self.vote_url = reverse("poll-vote", args=[self.poll.poll_id])
        self.results_url = reverse("poll-results", args=[self.poll.poll_id])
        self.voter_upload_url = reverse("voter-upload", args=[self.poll.poll_id])
        self.voter_login_url = reverse("voter-login")

        # Upload a controlled voter
        payload = {"voters": [{"email": "voter@test.com"}]}
        response = self.client.post(self.voter_upload_url, payload, format="json")
        voter_info = response.data["created"][0]

        # Login voter
        voter_login_response = self.client.post(self.voter_login_url, {
            "email": voter_info["email"],
            "temp_password": voter_info["temp_password"],
            "poll_id": str(self.poll.poll_id)
        }, format="json")
        self.voter_data = voter_login_response.data
        token = AccessToken(self.voter_data.get("voter_token"))
        voter_id = token.get('voter_id')
        self.voter = Voter.objects.filter(voter_id=voter_id, poll=self.poll).first()

    # -------------------------
    # Poll creation
    # -------------------------
    def test_poll_creation(self):
        self.assertEqual(self.poll.title, "Favorite Fruit?")
        self.assertEqual(self.poll.options.count(), 2)

    # -------------------------
    # Controlled voter voting
    # -------------------------
    def test_controlled_voter_can_vote(self):
        data = {
            "poll_option": str(self.option1.option_id),
            "voter_token": str(self.voter_data.get("voter_token"))
        }
        response = self.client.post(self.vote_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        vote = Vote.objects.get(anon_id=self.voter_data.get('anon_id'))
        self.assertEqual(vote.poll_option, self.option1)

        self.voter.refresh_from_db()
        self.assertTrue(self.voter.has_voted)

    def test_controlled_voter_cannot_vote_twice(self):
        # First vote
        self.client.post(self.vote_url, {
            "poll_option": str(self.option1.option_id),
            "voter_token": str(self.voter_data.get("voter_token"))
        }, format="json")

        # Second vote attempt
        response = self.client.post(self.vote_url, {
            "poll_option": str(self.option2.option_id),
            "voter_token": str(self.voter_data.get("voter_token"))
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already voted", str(response.data))

    # -------------------------
    # Poll results
    # -------------------------
    def test_results_endpoint(self):
        # Add some votes
        Vote.objects.create(poll_option=self.option1, anon_id=str(uuid4()))
        Vote.objects.create(poll_option=self.option1, anon_id=str(uuid4()))
        Vote.objects.create(poll_option=self.option2, anon_id=self.voter.anon_id)

        response = self.client.get(self.results_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = {item["text"]: item["votes_count"] for item in response.data}
        self.assertEqual(results["Apple"], 2)
        self.assertEqual(results["Banana"], 1)

    # -------------------------
    # Voter upload
    # -------------------------
    def test_upload_multiple_voters(self):
        payload = {
            "voters": [
                {"email": "test1@example.com"},
                {"email": "test2@example.com"}
            ]
        }
        response = self.client.post(self.voter_upload_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Voter.objects.filter(poll=self.poll).count(), 3)  # existing + 2 new

    def test_upload_rejects_missing_email(self):
        payload = {
            "voters": [
                {"email": "valid@example.com"},
                {"name": "No email"}
            ]
        }
        response = self.client.post(self.voter_upload_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", str(response.data).lower())

    def test_upload_multiple_voters_sends_emails(self):
        payload = {
            "voters": [
                {"email": "a@test.com"},
                {"email": "b@test.com"},
                {"email": "c@test.com"},
            ]
        }
        response = self.client.post(self.voter_upload_url, payload, format="json")

        # Ensure the mock email was called 3 times
        self.assertEqual(self.mock_send_email.call_count, 3)
        called_emails = [call.kwargs["email"] for call in self.mock_send_email.call_args_list]
        self.assertIn("a@test.com", called_emails)
        self.assertIn("b@test.com", called_emails)
        self.assertIn("c@test.com", called_emails)

    # -------------------------
    # Anonymous voting tests
    # -------------------------
    def test_anonymous_vote(self):
        anon_id = str(uuid4())
        data = {
            "poll_option": str(self.option1.option_id),
            "anon_id": anon_id
        }
        response = self.client.post(self.vote_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        vote = Vote.objects.get(anon_id=anon_id)
        self.assertEqual(vote.poll_option, self.option1)

    def test_anonymous_vote_single_choice_constraint(self):
        anon_id = str(uuid4())
        # First vote
        self.client.post(self.vote_url, {
            "poll_option": str(self.option1.option_id),
            "anon_id": anon_id
        }, format="json")
        # Second vote attempt
        response = self.client.post(self.vote_url, {
            "poll_option": str(self.option2.option_id),
            "anon_id": anon_id
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can only vote once", str(response.data))
    
    def test_multiple_anonymous_votes(self):
        anon_ids = [str(uuid4()) for _ in range(3)]
        for anon_id in anon_ids:
            response = self.client.post(self.vote_url, {
                "poll_option": str(self.option1.option_id),
                "anon_id": anon_id
            }, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Vote.objects.filter(poll_option=self.option1).count(), 3)

    def test_anonymous_single_choice_enforced(self):
        anon_id = str(uuid4())
        # First vote
        self.client.post(self.vote_url, {
            "poll_option": str(self.option1.option_id),
            "anon_id": anon_id
        }, format="json")
        # Attempt to vote again for different option
        response = self.client.post(self.vote_url, {
            "poll_option": str(self.option2.option_id),
            "anon_id": anon_id
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can only vote once", str(response.data))

    def test_mix_anonymous_and_controlled_votes(self):
        # Anonymous voter
        anon_id = str(uuid4())
        anon_response = self.client.post(self.vote_url, {
            "poll_option": str(self.option1.option_id),
            "anon_id": anon_id
        }, format="json")
        self.assertEqual(anon_response.status_code, status.HTTP_201_CREATED)

        # Controlled voter
        controlled_response = self.client.post(self.vote_url, {
            "poll_option": str(self.option2.option_id),
            "voter_token": str(self.voter_data.get("voter_token"))
        }, format="json")
        self.assertEqual(controlled_response.status_code, status.HTTP_201_CREATED)

        # Verify votes
        self.assertEqual(Vote.objects.filter(poll_option=self.option1).count(), 1)
        self.assertEqual(Vote.objects.filter(poll_option=self.option2).count(), 1)
