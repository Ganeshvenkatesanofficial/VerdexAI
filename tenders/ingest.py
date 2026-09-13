from celery import shared_task
from .models import Tender
from .adapters.cppp_adapter import CPPPAdapter


@shared_task
def run_daily_sweep():
    adapters = [CPPPAdapter(max_pages=3)]
    total_new = 0
    total_skipped = 0

    for adapter in adapters:
        normalized_tenders = adapter.fetch_and_normalize()

        for tender_data in normalized_tenders:
            if tender_data["closing_date"] is None:
                continue  # skip malformed rows rather than crash the whole sweep

            obj, created = Tender.objects.get_or_create(
                source_portal=tender_data["source_portal"],
                source_tender_id=tender_data["source_tender_id"],
                defaults=tender_data,
            )
            if created:
                total_new += 1
            else:
                total_skipped += 1

    print(f"Sweep complete: {total_new} new, {total_skipped} already existed")
    return total_new, total_skipped
