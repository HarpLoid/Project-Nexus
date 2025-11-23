from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PollViewSet, VoterUploadView, voter_login, RegisterView, LoginView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = DefaultRouter()
router.register(r'polls', PollViewSet, basename='poll')

urlpatterns = [
    path('', include(router.urls)),
    path('voters/upload/<uuid:poll_id>/', VoterUploadView.as_view(), name='voter-upload'),
    path('voters/login/', voter_login, name='voter-login'),
    # Auth endpoints for creators
    path('auth/register/', RegisterView.as_view(), name='register'),
    path("auth/login/", LoginView.as_view(), name="login"),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
