from rest_framework import serializers
from .models import Poll, PollOption, Vote

class PollOptionSerializer(serializers.ModelSerializer):
    votes_count = serializers.IntegerField(source='votes.count', read_only=True)

    class Meta:
        model = PollOption
        fields = ['option_id', 'text', 'created_at', 'votes_count']

class PollSerializer(serializers.ModelSerializer):
    options = PollOptionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Poll
        fields = ['poll_id', 'title', 'description', 'created_at',
                  'updated_at', 'expires_at', 'is_active', 'options']

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
        
        if Vote.objects.filter(poll_option=poll_option, anon_id=anon_id).exists():
            raise serializers.ValidationError("This user has already voted for this option.")
        
        if poll.poll_type == Poll.SINGLE_CHOICE:
            voted_options = Vote.objects.filter(poll_option__poll=poll, anon_id=anon_id)
            if voted_options.exists():
                raise serializers.ValidationError("You can only vote for one option in this poll.")
        
        return data
