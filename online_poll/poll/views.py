from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import AccessToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.hashers import check_password

from .models import Poll, PollOption, Voter, Vote
from .serializers import (
    PollSerializer, PollCreateSerializer, PollOptionSerializer,
    VoteSerializer, VoterUploadSerializer, RegisterSerializer,
    LoginSerializer
)


# -------------------------
# User registration (public)
# -------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


# -------------------------
# PollViewSet
# -------------------------
class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all().order_by('-created_at')
    lookup_field = 'poll_id'
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return PollCreateSerializer
        return PollSerializer

    def perform_create(self, serializer):
        # ensure creator is request.user
        serializer.context['creator'] = self.request.user
        serializer.save()

    # -------------------- vote action --------------------
    @swagger_auto_schema(
        method='post',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['poll_option'],
            properties={
                'poll_option': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the poll option to vote for'),
                'anon_id': openapi.Schema(type=openapi.TYPE_STRING, description='Anonymous voter id (optional)'),
                'voter_token': openapi.Schema(type=openapi.TYPE_STRING, description='Voter JWT (optional)')
            }
        ),
        responses={201: VoteSerializer, 400: 'Validation errors'},
    )
    @action(detail=True, methods=['post'], url_path='vote', permission_classes=[AllowAny])
    def vote(self, request, poll_id=None):
        poll = self.get_object()
        option_id = request.data.get('poll_option')
        anon_id = request.data.get('anon_id')
        voter_token = request.data.get('voter_token')
        voter_id = request.data.get('voter')

        # resolve option
        try:
            option = poll.options.get(option_id=option_id)
        except PollOption.DoesNotExist:
            return Response({'error': 'Option does not exist for this poll.'}, status=status.HTTP_400_BAD_REQUEST)

        voter = None
        # if voter_token supplied: decode and load voter
        if voter_token:
            try:
                token = AccessToken(voter_token)
                voter = Voter.objects.get(voter_id=token['voter_id'], poll=poll)
                anon_id = voter.anon_id
            except Exception:
                return Response({'error': 'Invalid voter token.'}, status=status.HTTP_400_BAD_REQUEST)
        elif voter_id:
            try:
                voter = Voter.objects.get(voter_id=voter_id, poll=poll)
                anon_id = voter.anon_id
            except Voter.DoesNotExist:
                return Response({'error': 'Voter not found.'}, status=status.HTTP_400_BAD_REQUEST)

        if voter and voter.has_voted:
            return Response({'error': 'You can only vote once in this poll.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            if Vote.objects.filter(poll_option__poll=poll, anon_id=anon_id).exists():
                return Response({'error': 'You can only vote once in this poll.'}, status=status.HTTP_400_BAD_REQUEST)

        # build serializer input: pass model instance for poll_option
        vote_payload = {'poll_option': str(option.option_id),
                        'anon_id': anon_id,
                        'voter': str(voter.voter_id) if voter else None}

        serializer = VoteSerializer(data=vote_payload)
        try:
            serializer.is_valid(raise_exception=True)
            vote = serializer.save()
            
            if voter:
                voter.has_voted = True
                voter.save()
        
            return Response(VoteSerializer(vote).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({'error': e.detail}, status=status.HTTP_400_BAD_REQUEST)

    # -------------------- results action --------------------
    @swagger_auto_schema(
        method='get',
        responses={200: PollOptionSerializer(many=True)},
    )
    @action(detail=True, methods=['get'], url_path='results', permission_classes=[AllowAny])
    def results(self, request, poll_id=None):
        poll = self.get_object()
        options = poll.options.annotate(votes_count=Count('votes')).order_by('-votes_count')
        serializer = PollOptionSerializer(options, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# -------------------------
# Upload voters (creator only)
# -------------------------
class VoterUploadView(generics.CreateAPIView):
    serializer_class = VoterUploadSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=VoterUploadSerializer,
        responses={201: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "created": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "email": openapi.Schema(type=openapi.TYPE_STRING),
                            "temp_password": openapi.Schema(type=openapi.TYPE_STRING),
                            "anon_id": openapi.Schema(type=openapi.TYPE_STRING),
                            "created": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        }
                    )
                )
            }
        )}
    )
    def post(self, request, poll_id):
        poll = get_object_or_404(Poll, poll_id=poll_id)

        serializer = self.get_serializer(
            data=request.data,
            context={"poll": poll}
        )
        serializer.is_valid(raise_exception=True)

        result = serializer.save()  # calls create()

        return Response(result, status=status.HTTP_201_CREATED)


# -------------------------
# Voter login (temp credentials -> voter token)
# -------------------------
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['email', 'temp_password', 'poll_id'],
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING, description="Voter's email"),
            'temp_password': openapi.Schema(type=openapi.TYPE_STRING, description="Temporary password sent to voter"),
            'poll_id': openapi.Schema(type=openapi.TYPE_STRING, description="Poll ID")
        }
    ),
    responses={200: 'JWT token returned', 400: 'Invalid credentials'}
)

@api_view(['POST'])
@permission_classes([AllowAny])
def voter_login(request):
    email = request.data.get('email')
    temp_password = request.data.get('temp_password')
    poll_id = request.data.get('poll_id')

    try:
        voter = Voter.objects.get(email=email, poll_id=poll_id)
    except Voter.DoesNotExist:
        return Response({'error': 'Voter not found'}, status=status.HTTP_404_NOT_FOUND)

    if not check_password(temp_password, voter.temp_password):
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)

    # create a short-lived voter token (AccessToken) with voter_id and poll_id
    token = AccessToken()
    token['voter_id'] = str(voter.voter_id)
    token['poll_id'] = str(poll_id)
    # optionally set expiry: token.set_exp(from_now=...), but default expiry applies
    return Response({'voter_token': str(token), 'anon_id': voter.anon_id})
