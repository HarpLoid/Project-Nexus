from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Poll, PollOption, Voter, Vote
from uuid import uuid4

class PollTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create a test poll
        self.poll = Poll.objects.create(
            title="Favorite Fruit?",
            description="Choose your favorite",
            poll_type=Poll.SINGLE_CHOICE,
            allow_anonymous=True
        )
        # Add options
        self.option1 = PollOption.objects.create(poll=self.poll, text="Apple")
        self.option2 = PollOption.objects.create(poll=self.poll, text="Banana")

    def test_poll_creation(self):
        """Test that the poll is created with correct fields"""
        self.assertEqual(self.poll.title, "Favorite Fruit?")
        self.assertEqual(self.poll.options.count(), 2)

    def test_add_voter(self):
        """Test adding a controlled voter"""
        url = reverse('poll-add-voters', args=[self.poll.poll_id])
        data = {"voters": [{"email": "voter1@test.com"}]}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.poll.voters.count(), 1)
        voter = self.poll.voters.first()
        self.assertIsNotNone(voter.temp_password)
        self.assertIsNotNone(voter.anon_id)

    def test_vote_anonymous(self):
        """Test casting an anonymous vote"""
        url = reverse('poll-vote', args=[self.poll.poll_id])
        anon_id = str(uuid4())
        data = {"poll_option": str(self.option1.option_id), "anon_id": anon_id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vote.objects.count(), 1)
        vote = Vote.objects.first()
        self.assertEqual(vote.anon_id, anon_id)
        self.assertEqual(vote.poll_option, self.option1)

    def test_vote_single_choice_constraint(self):
        """Test that a single-choice poll prevents multiple votes per anon_id"""
        url = reverse('poll-vote', args=[self.poll.poll_id])
        anon_id = str(uuid4())
        data = {"poll_option": str(self.option1.option_id), "anon_id": anon_id}
        self.client.post(url, data, format='json')
        # Try voting again for another option with same anon_id
        data2 = {"poll_option": str(self.option2.option_id), "anon_id": anon_id}
        response2 = self.client.post(url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You can only vote for one option", str(response2.data))

    def test_results_endpoint(self):
        """Test the results endpoint returns vote counts"""
        # Cast votes
        anon_id1 = str(uuid4())
        anon_id2 = str(uuid4())
        Vote.objects.create(poll_option=self.option1, anon_id=anon_id1)
        Vote.objects.create(poll_option=self.option1, anon_id=anon_id2)
        url = reverse('poll-results', args=[self.poll.poll_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that votes_count is correct
        self.assertEqual(response.data[0]['votes_count'], 2)
