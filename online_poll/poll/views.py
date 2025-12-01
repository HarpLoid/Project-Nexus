from uuid import uuid4
from django.db.models import Count
from django.shortcuts import get_object_or_404
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
from .utils import generate_anon_id

from .models import Poll, PollOption, Voter, AnonymousVoter
from .serializers import (
    PollSerializer, PollCreateSerializer, PollOptionSerializer,
    VoteSerializer, VoterUploadSerializer, RegisterSerializer,
    LoginSerializer
)
from .swagger import (
    register_swagger, login_swagger,
    poll_list_swagger, poll_retrieve_swagger, poll_create_swagger,
    poll_update_swagger, poll_delete_swagger,
    vote_swagger, results_swagger,
    voter_upload_swagger, voter_login_swagger, anonymous_vote
)



# -------------------------
# User registration (public)
# -------------------------
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    @register_swagger
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]
    
    @login_swagger
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


# -------------------------
# PollViewSet
# -------------------------
class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all().order_by('-created_at')
    lookup_field = 'poll_id'

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return PollCreateSerializer
        return PollSerializer

    def get_permissions(self):
        """
        Apply dynamic permissions.
        """
        # Public actions
        if self.action in ('vote', 'anonymous_vote', 'results', 'list', 'retrieve'):
            return [AllowAny()]

        # Protected actions
        return [IsAuthenticated()]

    # -----------------------------
    # CREATOR-ONLY QUERYSET CONTROL
    # -----------------------------
    def get_queryset(self):
        qs = Poll.objects.all().order_by('-created_at')

        if self.action == 'list':
            return qs.filter(is_active=True)

        if self.action == 'retrieve':
            return qs

        if self.action in ('update', 'partial_update', 'destroy'):
            return qs.filter(creator=self.request.user)

        return qs

    # --------------------------------
    # Assign creator on create
    # --------------------------------
    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    # ---------------- Swagger Wrappers ----------------
    @poll_list_swagger
    def list(self, *args, **kwargs):
        return super().list(*args, **kwargs)

    @poll_retrieve_swagger
    def retrieve(self, *args, **kwargs):
        return super().retrieve(*args, **kwargs)

    @poll_create_swagger
    def create(self, *args, **kwargs):
        return super().create(*args, **kwargs)

    @poll_update_swagger
    def update(self, *args, **kwargs):
        return super().update(*args, **kwargs)

    @poll_delete_swagger
    def destroy(self, *args, **kwargs):
        return super().destroy(*args, **kwargs)

    from rest_framework.permissions import IsAuthenticated

    @action(
        detail=False,
        methods=['get'],
        url_path='user_polls',
        permission_classes=[IsAuthenticated]
    )
    def user_polls(self, request):
        """
        Returns all polls created by the logged-in user.
        """
        user = request.user
        polls = Poll.objects.filter(creator=user).order_by('-created_at')

        serializer = PollSerializer(polls, many=True)
        return Response(serializer.data)


    # ========================================================
    #             Anonymous Token Endpoint
    # ========================================================
    @anonymous_vote
    @action(detail=True, methods=['post'], url_path='anonymous_vote', permission_classes=[AllowAny])
    def anonymous_vote(self, request, poll_id=None):
        poll = self.get_object()

        if not poll.allow_anonymous:
            return Response({'error': 'Anonymous voting not allowed'}, status=403)

        anon_id = uuid4().hex

        AnonymousVoter.objects.create(
            poll=poll,
            anon_id=anon_id
        )

        return Response({'anon_id': anon_id}, status=200)

    # ========================================================
    #	            Vote Action (Secure)
    # ========================================================
    @vote_swagger
    @action(detail=True, methods=['post'], url_path='vote', permission_classes=[AllowAny])
    def vote(self, request, poll_id=None):

        poll = self.get_object()
        option_id = request.data.get('poll_option')
        voter_token = request.data.get('voter_token')
        anon_id = request.data.get('anon_id')

        # ------ Validate option ------
        try:
            option = poll.options.get(option_id=option_id)
        except PollOption.DoesNotExist:
            return Response({'error': 'Invalid poll option'}, status=400)

        voter = None

        # ---------- Authenticated Voter ----------
        if voter_token:
            try:
                token = AccessToken(voter_token)
                voter_id = token.get('voter_id')
                voter = Voter.objects.filter(voter_id=voter_id, poll=poll).first()

                if not voter:
                    return Response({'error': 'Voter not registered for this poll'}, status=400)

                if voter.has_voted:
                    return Response({'error': 'You already voted'}, status=400)

            except Exception as e:
                return Response({'error': f'Invalid token: {e}'}, status=400)

        else:
            # -----------------------------------
            # Anonymous mode
            # -----------------------------------
            if not poll.allow_anonymous:
                return Response({'error': 'Anonymous voting not allowed'}, status=403)

            if not anon_id:
                return Response({'error': 'anon_id is required for anonymous voting'}, status=400)

            anon_obj = AnonymousVoter.objects.filter(
                poll=poll,
                anon_id=anon_id
            ).first()

            if not anon_obj:
                return Response({'error': 'Invalid anonymous token'}, status=400)

            if anon_obj.has_voted:
                return Response({'error': 'This anonymous ID has already voted'}, status=400)

            anon_obj.has_voted = True
            anon_obj.save()

        vote_payload = {'poll_option': option.option_id}

        if voter:
            vote_payload['voter'] = str(voter.voter_id)
        else:
            vote_payload['anon_id'] = anon_id

        serializer = VoteSerializer(data=vote_payload)
        serializer.is_valid(raise_exception=True)
        vote = serializer.save()

        if voter:
            voter.has_voted = True
            voter.save()

        return Response(VoteSerializer(vote).data, status=201)

    # -------------------- Results --------------------
    @results_swagger
    @action(detail=True, methods=['get'], url_path='results', permission_classes=[AllowAny])
    def results(self, request, poll_id=None):
        poll = self.get_object()
        options = poll.options.annotate(votes_count=Count('votes')).order_by('-votes_count')
        serializer = PollOptionSerializer(options, many=True)
        return Response(serializer.data)




# -------------------------
# Upload voters (creator only)
# -------------------------
class VoterUploadView(generics.CreateAPIView):
    serializer_class = VoterUploadSerializer
    permission_classes = [IsAuthenticated]

    @voter_upload_swagger
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
@voter_login_swagger
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
