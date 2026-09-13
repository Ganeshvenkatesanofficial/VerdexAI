from rest_framework import viewsets, permissions
from .models import Tender, Verdict
from .serializers import TenderSerializer, TenderDetailSerializer, VerdictSerializer
from companies.models import Company


class TenderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tender.objects.all().order_by('-closing_date')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TenderDetailSerializer
        return TenderSerializer


class VerdictViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VerdictSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_user_company(self):
        try:
            return Company.objects.get(owner=self.request.user)
        except Company.DoesNotExist:
            if hasattr(self.request.user, 'userprofile'):
                return self.request.user.userprofile.company
            return None

    def get_queryset(self):
        company = self._get_user_company()
        if not company:
            return Verdict.objects.none()
        return Verdict.objects.filter(company=company).order_by('-computed_at')
