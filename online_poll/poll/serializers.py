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
        fields = ['poll_id','title', 'description', 'poll_type', 'allow_anonymous', 'expires_at', 'options']
        read_only_fields = ['poll_id','created_at', 'updated_at', 'is_active']

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
                "temp_password": plain_pw,
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
        write_only=True,
        required=False
    )

    class Meta:
        model = Vote
        fields = ['vote_id', 'poll_option', 'created_at', 'voter']
        read_only_fields = ['vote_id', 'created_at']

    def validate(self, data):
        print("Validating vote data:", data)
        request = self.context.get('request')

        if not request:
            raise serializers.ValidationError("Invalid request context.")

        voter = data.get('voter')
        print("Validating vote for voter:", voter)
        poll_option = data.get('poll_option')
        poll = poll_option.poll

        if not voter:
            raise serializers.ValidationError("Voter could not be resolved.")

        # poll active & not expired
        if not poll.is_active:
            raise serializers.ValidationError("This poll is not active.")
        if poll.expires_at and poll.expires_at < timezone.now():
            raise serializers.ValidationError("This poll has expired.")

        # Check uniqueness
        if voter.has_voted:
            raise serializers.ValidationError("You have already voted.")

        if poll.poll_type == Poll.SINGLE_CHOICE:
            if Vote.objects.filter(
                poll_option__poll=poll,
                anon_id=voter.anon_id
            ).exists():
                raise serializers.ValidationError("You can only vote once in this poll.")

        # Keep voter so create() can use it
        data['voter'] = voter
        return data

    def create(self, validated_data):
        voter = validated_data.pop('voter')

        validated_data['anon_id'] = voter.anon_id
        vote = super().create(validated_data)

        voter.has_voted = True
        voter.save()

        return vote
