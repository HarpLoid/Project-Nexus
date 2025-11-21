from uuid import uuid4
from drf_yasg import openapi
from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError
from .models import Poll, PollOption
from .serializers import PollSerializer, PollCreateSerializer, PollOptionSerializer, VoteSerializer

class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all().order_by('-created_at')
    lookup_field = 'poll_id'
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PollCreateSerializer
        return PollSerializer
    
    @swagger_auto_schema(
        request_body=PollCreateSerializer,
        responses={
            201: PollSerializer,
            400: 'Validation errors'
        },
        operation_description="Create a new poll with nested poll options."
    )
    def create(self, request, *args, **kwargs):
        """
        Use PollCreateSerializer to validate input,
        then return full PollSerializer for response.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = serializer.save()

        read_serializer = PollSerializer(poll, context={'request': request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
    
    @swagger_auto_schema(
        method='post',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['poll_option'],
            properties={
                'poll_option': openapi.Schema(
                    type=openapi.TYPE_STRING, description='UUID of the poll option to vote for'
                ),
                'anon_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Anonymous voter ID (optional, will auto-generate if not provided)'
                )
            }
        ),
        responses={
            201: VoteSerializer,
            400: 'Validation errors (e.g., already voted, poll expired)'
        },
        operation_description="Cast a vote on a poll. Single-choice polls enforce one vote per user."
    )
    @action(detail=True, methods=['post'], url_path='vote')
    def vote(self, request, poll_id=None):
        """
        Cast a vote on a poll.
        - `poll_option`: UUID of the poll option to vote for
        - `anon_id` (optional): Anonymous voter ID
        """
    
        poll = self.get_object()
        option_id = request.data.get('poll_option')
        anon_id = request.data.get('anon_id') or str(uuid4())
        
        try:
            option = poll.options.get(option_id=option_id)
        except PollOption.DoesNotExist:
            return Response(
                {'error': 'Option does not exist for this poll.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vote_data = {
            'poll_option': option.option_id,
            'anon_id': anon_id
        }
        
        serializer = VoteSerializer(data=vote_data)
        
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response(
                {'error': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @swagger_auto_schema(
        method='get',
        responses={
            200: PollOptionSerializer(many=True),
        },
        operation_description="Get poll results with vote counts per option."
    )
    @action(detail=True, methods=['get'], url_path='results')
    def results(self, request, poll_id=None):
        
        poll = self.get_object()
        options = poll.options.annotate(votes_count=Count('votes')).order_by('-votes_count')
        serializer = PollOptionSerializer(options, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
