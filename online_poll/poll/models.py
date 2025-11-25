import string
import random
from uuid import uuid4
from django.db import models
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin
)

# -------------------------
# Custom User Manager
# -------------------------
class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Users must have an email")

        email = self.normalize_email(email)
        user = self.model(email=email)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user


# -------------------------
# Custom User
# -------------------------
class CustomUser(AbstractBaseUser, PermissionsMixin):
    user_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"

    objects = CustomUserManager()

    def __str__(self):
        return self.email


# -------------------------
# Poll
# -------------------------
class Poll(models.Model):
    SINGLE_CHOICE = 'single'
    MULTIPLE_CHOICE = 'multiple'

    POLL_TYPES = [
        (SINGLE_CHOICE, 'Single Choice'),
        (MULTIPLE_CHOICE, 'Multiple Choice'),
    ]

    poll_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='polls',
        null=True,
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    poll_type = models.CharField(max_length=20, choices=POLL_TYPES, default=SINGLE_CHOICE)
    allow_anonymous = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


# -------------------------
# Poll Options
# -------------------------
class PollOption(models.Model):
    option_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    poll = models.ForeignKey(Poll, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


# -------------------------
# Controlled Voters
# -------------------------
class Voter(models.Model):
    voter_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    poll = models.ForeignKey(Poll, related_name='voters', on_delete=models.CASCADE)
    email = models.EmailField()
    temp_password = models.CharField(max_length=128)
    anon_id = models.CharField(max_length=255)
    has_voted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['poll', 'email'], name='unique_voter_per_poll'),
            models.UniqueConstraint(fields=['poll', 'anon_id'], name='unique_anonid_per_poll')
        ]


# -------------------------
# Votes
# -------------------------
class Vote(models.Model):
    vote_id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    poll_option = models.ForeignKey(PollOption, related_name='votes', on_delete=models.CASCADE)
    anon_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['poll_option', 'anon_id'],
                name='unique_vote_per_option_per_anon'
            )
        ]
