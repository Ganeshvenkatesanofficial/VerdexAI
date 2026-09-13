from django.db import models
from companies.models import Company


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('datasheet', 'Datasheet'),
        ('certificate', 'Certificate'),
        ('financial', 'Financial Statement'),
        ('other', 'Other'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES, default='other')
    file = models.FileField(upload_to='vault_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.company.name})"
