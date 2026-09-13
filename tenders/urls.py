from rest_framework.routers import DefaultRouter
from .views import TenderViewSet, VerdictViewSet

router = DefaultRouter()
router.register(r'tenders', TenderViewSet, basename='tender')
router.register(r'verdicts', VerdictViewSet, basename='verdict')

urlpatterns = router.urls
