from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import Poll, PollOption, Vote
from .serializers import PollSerializer, PollOptionSerializer, VoteSerializer

class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all().order_by('-created_at')
    serializer_class = PollSerializer
    lookup_field = 'poll_id'

class PollOptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PollOptionSerializer
    lookup_field = 'option_id'
    
    def get_queryset(self):
        poll_id = self.kwargs.get('poll_id')
        return PollOption.objects.filter(poll_id=poll_id)

class VoteViewSet(viewsets.ModelViewSet):
    serializer_class = VoteSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = VoteSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)