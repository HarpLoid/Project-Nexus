from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PollViewSet, PollOptionViewSet, VoteViewSet

router = DefaultRouter()
router.register(r'polls', PollViewSet, basename='polls')
router.register('vote', VoteViewSet, basename='vote')

urlpatterns = [
    path('', include(router.urls)),
    path('polls/<uuid:poll_id>/options/',
         PollOptionViewSet.as_view({'get': 'list'}),
         name='poll-options'),
]

