from django.db import models
from companies.models import Company


class Tender(models.Model):
    SOURCE_CHOICES = [
        ('cppp', 'CPPP'),
        ('gem', 'GeM'),
    ]

    STATUS_CHOICES = [
        ('new', 'New'),
        ('processed', 'Processed'),
        ('verdict_ready', 'Verdict Ready'),
    ]

    source_portal = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    source_tender_id = models.CharField(max_length=255)  # portal's own ID, for dedup
    title = models.CharField(max_length=500)
    category = models.CharField(max_length=255, blank=True)
    closing_date = models.DateTimeField()
    published_date = models.DateTimeField(null=True, blank=True)
    raw_listing_text = models.TextField()  # verbatim text, needed for citation gate later
    evidence_file = models.FileField(upload_to='tender_evidence/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    ingested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('source_portal', 'source_tender_id')  # prevents duplicate ingestion

    def __str__(self):
        return f"{self.title} ({self.source_portal})"


class Verdict(models.Model):
    VERDICT_CHOICES = [
        ('go', 'GO'),
        ('no_go', 'NO-GO'),
        ('fixable', 'FIXABLE'),
    ]

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='verdicts')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='verdicts')
    result = models.CharField(max_length=20, choices=VERDICT_CHOICES)
    proof_lines = models.JSONField(default=list)  # list of {clause, page, matched_document, citation}
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tender', 'company')

    def __str__(self):
        return f"{self.tender.title} -> {self.company.name}: {self.result}"
