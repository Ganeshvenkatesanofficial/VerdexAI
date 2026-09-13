from rest_framework import serializers
from .models import Tender, Verdict

class TenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = ['id', 'source_portal', 'source_tender_id', 'title', 'category',
                  'closing_date', 'published_date', 'status', 'ingested_at']
        # raw_listing_text and evidence_file excluded from list view for now — keep it lean

class TenderDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tender
        fields = '__all__'  # full detail view includes raw_listing_text, evidence_file

class VerdictSerializer(serializers.ModelSerializer):
    tender_title = serializers.CharField(source='tender.title', read_only=True)

    class Meta:
        model = Verdict
        fields = ['id', 'tender', 'tender_title', 'result', 'proof_lines', 'computed_at']
