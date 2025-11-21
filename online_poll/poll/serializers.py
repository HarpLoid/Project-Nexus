from rest_framework import serializers
from .models import Poll, PollOption, Vote
from django.utils import timezone

class PollOptionSerializer(serializers.ModelSerializer):
    votes_count = serializers.IntegerField(source='votes.count', read_only=True)

    class Meta:
        model = PollOption
        fields = ['option_id', 'text', 'created_at', 'votes_count']

class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Poll
        fields = ['poll_id', 'title', 'description', 'created_at', 'poll_type',
                  'updated_at', 'expires_at', 'is_active', 'options']

class PollOptionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollOption
        fields = ['text']

class PollCreateSerializer(serializers.ModelSerializer):
    options = PollOptionCreateSerializer(many=True)
    
    class Meta:
        model = Poll
        fields = ['title', 'description', 'poll_type',
                  'expires_at', 'is_active', 'options']

    def create(self, validated_data):
        options_data = validated_data.pop('options')
        poll = Poll.objects.create(**validated_data)
        
        for option_data in options_data:
            PollOption.objects.create(poll=poll, **option_data)
        
        return poll

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['vote_id', 'poll_option', 'anon_id', 'created_at']
        read_only_fields = ['vote_id', 'created_at']
    
    def validate(self, data):
        """
        Ensure that the anon_id has not already voted for the given poll_option.
        """
        poll_option = data.get('poll_option')
        anon_id = data.get('anon_id')
        poll = poll_option.poll
        
        if not poll.is_active:
            raise serializers.ValidationError("This poll is not active.")
        
        if poll.expires_at and poll.expires_at < timezone.now():
            raise serializers.ValidationError("This poll has expired.")
        
        if Vote.objects.filter(poll_option=poll_option, anon_id=anon_id).exists():
            raise serializers.ValidationError("This user has already voted for this option.")
        
        if poll.poll_type == Poll.SINGLE_CHOICE:
            voted_before = Vote.objects.filter(
                poll_option__poll=poll,
                anon_id=anon_id
                ).exists()
            
            if voted_before:
                raise serializers.ValidationError(
                    "You can only vote for one option in this poll."
                    )
        
        return data
