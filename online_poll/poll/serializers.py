from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import authenticate
from poll.services.voter_service import create_voter_for_poll
from .models import CustomUser, Poll, PollOption, Voter, Vote
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# -----------------------
# User registration
# -----------------------
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['user_id', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        user = CustomUser.objects.create_user(email=email, password=password)
        return user


class LoginSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        user = authenticate(email=email, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        
        if not user.is_active:
            raise serializers.ValidationError("Your account is disabled.")
        
        data = super().validate(attrs)
        
        data['user'] = {
            'user_id': user.user_id,
            'email': user.email
        }

        return data


# -----------------------
# Poll option read
# -----------------------
class PollOptionSerializer(serializers.ModelSerializer):
    votes_count = serializers.IntegerField(source='votes.count', read_only=True)

    class Meta:
        model = PollOption
        fields = ['option_id', 'text', 'created_at', 'votes_count']


# -----------------------
# Poll read serializer
# -----------------------
class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)

    class Meta:
        model = Poll
        fields = [
            'poll_id', 'title', 'description', 'created_at', 'poll_type',
            'allow_anonymous', 'updated_at', 'expires_at', 'is_active', 'options'
        ]


# -----------------------
# Poll create (nested)
# -----------------------
class PollOptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ['text']


class PollCreateSerializer(serializers.ModelSerializer):
    options = PollOptionCreateSerializer(many=True)

    class Meta:
        model = Poll
        fields = ['title', 'description', 'poll_type', 'allow_anonymous', 'expires_at', 'options']

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        # creator must be provided by view (serializer.save(creator=request.user))
        creator = self.context.get('creator')
        poll = Poll.objects.create(creator=creator, **validated_data)
        for option_data in options_data:
            PollOption.objects.create(poll=poll, **option_data)
        return poll


# -----------------------
# Voter
# -----------------------
class VoterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voter
        fields = ['voter_id', 'email', 'temp_password', 'anon_id', 'has_voted', 'created_at']
        read_only_fields = ['voter_id', 'temp_password', 'anon_id', 'has_voted', 'created_at']


# -----------------------
# Voter upload serializer
# -----------------------
class VoterUploadSerializer(serializers.Serializer):
    voters = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )
    
    def validate(self, data):
        for obj in data["voters"]:
            if "email" not in obj:
                raise serializers.ValidationError("Each voter must have an email field.")
        return data

    def create(self, validated_data):
        poll = self.context["poll"]
        created_list = []

        for obj in validated_data["voters"]:
            email = obj["email"]
            voter, was_created, plain_pw = create_voter_for_poll(
                poll=poll,
                email=email,
                send_email=True
            )

            created_list.append({
                "email": voter.email,
                "temp_password": plain_pw,   # only for newly created
                "anon_id": voter.anon_id,
                "created": was_created
            })

        return {"created": created_list}


# -----------------------
# Vote serializer
# -----------------------
class VoteSerializer(serializers.ModelSerializer):
    poll_option = serializers.PrimaryKeyRelatedField(
        queryset=PollOption.objects.all()
    )
    voter = serializers.PrimaryKeyRelatedField(
        queryset=Voter.objects.all(), 
        required=False, allow_null=True)

    class Meta:
        model = Vote
        fields = ['vote_id', 'poll_option', 'anon_id', 'voter', 'created_at']
        read_only_fields = ['vote_id', 'created_at']

    def validate(self, data):
        poll_option = data.get('poll_option')
        if poll_option is None:
            raise serializers.ValidationError("poll_option is required.")

        poll = poll_option.poll
        anon_id = data.get('anon_id')
        voter = data.get('voter')  # may be None

        # poll active & not expired
        if not poll.is_active:
            raise serializers.ValidationError("This poll is not active.")
        if poll.expires_at and poll.expires_at < timezone.now():
            raise serializers.ValidationError("This poll has expired.")

        # require anon_id (for anonymity and uniqueness)
        if not anon_id:
            raise serializers.ValidationError("anon_id is required (server can generate one).")

        # duplicate vote for the same option
        if Vote.objects.filter(poll_option=poll_option, anon_id=anon_id).exists():
            raise serializers.ValidationError("You have already voted for this option.")

        # single-choice: check anon_id or voter hasn't voted in this poll already
        if poll.poll_type == Poll.SINGLE_CHOICE:
            # anon_id double voting
            if Vote.objects.filter(poll_option__poll=poll, anon_id=anon_id).exists():
                raise serializers.ValidationError("You can only vote once in this poll.")

            # controlled voter double voting
            if voter and voter.has_voted:
                raise serializers.ValidationError("You can only vote once in this poll.")
        
        # controlled voter cannot have already voted
        if voter and voter.has_voted:
            raise serializers.ValidationError("This voter has already cast their vote.")

        return data

    def create(self, validated_data):
        voter = validated_data.get('voter')
        vote = super().create(validated_data)

        # mark voter as having voted (controlled path)
        if voter:
            voter.has_voted = True
            voter.save()

        return vote
