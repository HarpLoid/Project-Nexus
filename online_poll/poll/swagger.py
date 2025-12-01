from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from .serializers import (
    PollSerializer, PollCreateSerializer, PollOptionSerializer,
    VoteSerializer, VoterUploadSerializer, RegisterSerializer,
    LoginSerializer, AnonymousVoteSerializer
)

# ================================================================
#  USER AUTH SWAGGER
# ================================================================

register_swagger = swagger_auto_schema(
    operation_summary="Register a new user",
    request_body=RegisterSerializer,
    responses={201: "User created successfully"}
)

login_swagger = swagger_auto_schema(
    operation_summary="Login to obtain JWT token pair",
    request_body=LoginSerializer,
    responses={200: "Access + Refresh tokens returned"}
)


# ================================================================
#  POLL CRUD SWAGGER
# ================================================================

poll_list_swagger = swagger_auto_schema(
    operation_summary="List active polls",
    responses={200: PollSerializer(many=True)}
)

poll_retrieve_swagger = swagger_auto_schema(
    operation_summary="Retrieve a specific poll",
    responses={200: PollSerializer}
)

poll_create_swagger = swagger_auto_schema(
    operation_summary="Create a new poll",
    request_body=PollCreateSerializer,
    responses={201: PollSerializer}
)

poll_update_swagger = swagger_auto_schema(
    operation_summary="Update a poll",
    request_body=PollCreateSerializer,
    responses={200: PollSerializer}
)

poll_delete_swagger = swagger_auto_schema(
    operation_summary="Delete a poll",
    responses={204: "Deleted successfully"}
)


# ================================================================
#  VOTE ACTION SWAGGER
# ================================================================

vote_request_body = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    required=["poll_option"],
    properties={
        "poll_option": openapi.Schema(type=openapi.TYPE_STRING),
        "voter_token": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
        "anon_id": openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
    },
)

vote_swagger = swagger_auto_schema(
    method="post",
    operation_summary="Cast a vote",
    request_body=vote_request_body,
    responses={
        201: openapi.Response("Vote created", VoteSerializer),
        400: "Invalid vote"
    }
)


# ================================================================
#  POLL RESULTS SWAGGER
# ================================================================

results_swagger = swagger_auto_schema(
    method="get",
    operation_summary="Get poll results",
    responses={200: PollOptionSerializer(many=True)}
)


# ================================================================
#  VOTER UPLOAD SWAGGER
# ================================================================

voter_upload_swagger = swagger_auto_schema(
    operation_summary="Upload voters for a poll",
    request_body=VoterUploadSerializer,
    responses={
        201: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "created": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "email": openapi.Schema(type=openapi.TYPE_STRING),
                            "created": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        },
                    ),
                )
            },
        )
    }
)


# ================================================================
#  VOTER LOGIN SWAGGER
# ================================================================

voter_login_swagger = swagger_auto_schema(
    method="post",
    operation_summary="Login voter using email + temp password",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["email", "temp_password", "poll_id"],
        properties={
            "email": openapi.Schema(type=openapi.TYPE_STRING),
            "temp_password": openapi.Schema(type=openapi.TYPE_STRING),
            "poll_id": openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={
        200: "voter_token + anon_id returned",
        400: "Invalid credentials",
        404: "Voter not found"
    }
)

anonymous_vote = swagger_auto_schema(
    method='post',
    request_body=AnonymousVoteSerializer,
    responses={
        200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "anon_id": openapi.Schema(type=openapi.TYPE_STRING, description="Anonymous voting token")
            }
        ),
        403: "Anonymous voting not allowed"
    }
)
