from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from uuid import uuid4
from django.core import mail
from .serializers import VoterUploadSerializer
from .models import Poll, PollOption, Voter, Vote, CustomUser as User

# ===========================================================
# POLL AND VOTER TESTS
# ===========================================================
class PollTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create a poll creator
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

        # Controlled voter
        # self.voter = Voter.objects.create(
        #     poll=self.poll,
        #     email="voter@test.com"
        # )
        
        serializer = VoterUploadSerializer(
            data={"voters": [{"email": "voter@test.com"}]},
            context={"poll": self.poll}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        self.voter = Voter.objects.get(email="voter@test.com", poll=self.poll)

        self.vote_url = reverse("poll-vote", args=[self.poll.poll_id])
        self.voter_upload_url = reverse("voter-upload", args=[self.poll.poll_id])

    # -------------------------
    # Poll creation
    # -------------------------
    def test_poll_creation(self):
        self.assertEqual(self.poll.title, "Favorite Fruit?")
        self.assertEqual(self.poll.options.count(), 2)

    # -------------------------
    # Anonymous voting
    # -------------------------
    def test_vote_anonymous(self):
        anon_id = str(uuid4())
        data = {
            "poll_option": str(self.option1.option_id),
            "anon_id": anon_id
        }
        response = self.client.post(self.vote_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        vote = Vote.objects.first()
        self.assertEqual(vote.poll_option, self.option1)
        self.assertEqual(vote.anon_id, anon_id)

    def test_single_choice_anon_constraint(self):
        anon_id = str(uuid4())

        # First vote
        self.client.post(self.vote_url, {
            "poll_option": str(self.option1.option_id),
            "anon_id": anon_id
        }, format="json")

        # Second vote for different option
        response = self.client.post(self.vote_url, {
            "poll_option": str(self.option2.option_id),
            "anon_id": anon_id
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can only vote once", str(response.data.get("error")))

    # -------------------------
    # Controlled voter voting
    # -------------------------
    def test_controlled_voter_can_vote(self):
        data = {
            "poll_option": str(self.option1.option_id),
            "voter": str(self.voter.voter_id)
        }

        response = self.client.post(self.vote_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        vote = Vote.objects.get(voter=self.voter)
        self.assertEqual(vote.poll_option, self.option1)

        self.voter.refresh_from_db()
        self.assertTrue(self.voter.has_voted)

    def test_controlled_voter_cannot_vote_twice(self):
        # First vote
        self.client.post(self.vote_url, {
            "poll_option": str(self.option1.option_id),
            "voter": str(self.voter.voter_id)
        }, format="json")

        # Second vote attempt
        response = self.client.post(self.vote_url, {
            "poll_option": str(self.option2.option_id),
            "voter": str(self.voter.voter_id)
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_msg = response.data.get("error")
        if isinstance(error_msg, dict):
            error_msg = str(list(error_msg.values())[0])
        self.assertIn("You can only vote once", str(error_msg))

    # -------------------------
    # Poll results
    # -------------------------
    def test_results_endpoint(self):
        # Add some votes
        Vote.objects.create(poll_option=self.option1, anon_id=str(uuid4()))
        Vote.objects.create(poll_option=self.option1, anon_id=str(uuid4()))
        Vote.objects.create(poll_option=self.option2, voter=self.voter, anon_id=self.voter.anon_id)

        url = reverse("poll-results", args=[self.poll.poll_id])
        response = self.client.get(url)
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
        created = response.data["created"]
        self.assertTrue(created[0]["created"])
        self.assertTrue(created[1]["created"])

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
    
    # -----------------------------
    # Test Email Sending
    # -----------------------------
    def test_voter_upload_sends_email(self):
        payload = {
            "voters": [
                {"email": "newvoter@test.com"}
            ]
        }

        # Clear mail outbox before test
        mail.outbox = []

        response = self.client.post(self.voter_upload_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]

        # Basic checks
        self.assertEqual(email.to, ["newvoter@test.com"])
        self.assertIn(f"Voting Access for Poll: {self.poll.title}", email.subject)

        # Verify content
        response_data = response.data["created"][0]
        returned_anon_id = response_data["anon_id"]
        returned_temp_pwd = response_data["temp_password"]

        self.assertIn(returned_anon_id, email.body)
        self.assertIn(returned_temp_pwd, email.body)
    
    def test_multiple_voters_send_multiple_emails(self):
        mail.outbox = []

        payload = {
            "voters": [
                {"email": "a@test.com"},
                {"email": "b@test.com"},
                {"email": "c@test.com"},
            ]
        }

        response = self.client.post(self.voter_upload_url, payload, format="json")

        self.assertEqual(len(mail.outbox), 3)

