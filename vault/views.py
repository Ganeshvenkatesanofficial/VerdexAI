from rest_framework import viewsets, permissions
from rest_framework.exceptions import ValidationError
from .models import Document
from .serializers import DocumentSerializer
from companies.models import Company

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
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
            return Document.objects.none()
        return Document.objects.filter(company=company)

    def perform_create(self, serializer):
        company = self._get_user_company()
        if not company:
            raise ValidationError("No company associated with this user.")
        serializer.save(company=company)
