from django.db import models
from uuid import uuid4

class Poll(models.Model):
    SINGLE_CHOICE = 'single choice'
    MULTIPLE_CHOICE = 'multiple choice'
    POLL_TYPES = [
        (SINGLE_CHOICE, 'Single Choice'),
        (MULTIPLE_CHOICE, 'Multiple Choice'),
    ]

    poll_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    poll_type = models.CharField(max_length=20, choices=POLL_TYPES, default=SINGLE_CHOICE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class PollOption(models.Model):
    option_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    poll = models.ForeignKey(Poll, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"self.text ({self.poll.title})"

class Vote(models.Model):
    vote_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    poll_option = models.ForeignKey(PollOption, related_name='votes', on_delete=models.CASCADE)
    anon_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields = ['poll_option', 'anon_id'],
                name = 'unique_vote_per_user'
            )
        ]

    def __str__(self):
        return f"Vote for {self.poll_option.text} in {self.poll_option.poll.title}"
