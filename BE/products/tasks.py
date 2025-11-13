from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from celery import shared_task
from django.utils import timezone

from .models import ImportJob, ImportJobStatus, Webhook
from .services import import_products_from_csv

logger = logging.getLogger(__name__)


def _append_error(job: ImportJob, messages: Sequence[str]) -> None:
    log = list(job.error_log or [])
    log.extend({"error": msg} for msg in messages)
    job.error_log = log[-200:]


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_import_job(self, job_id: str, csv_path: str) -> None:
    """
    Celery task that processes a CSV import job.
    """
    try:
        job = ImportJob.objects.get(id=job_id)
    except ImportJob.DoesNotExist:
        logger.error("ImportJob %s not found.", job_id)
        return

    try:
        success_count, failure_count, errors = import_products_from_csv(Path(csv_path), job)
    except Exception as exc:
        logger.exception("Import job %s failed: %s", job.id, exc)
        job.status = ImportJobStatus.FAILED
        _append_error(job, [str(exc)])
        job.failure_count = job.failure_count + 1
        job.updated_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "failure_count",
                "error_log",
                "updated_at",
            ]
        )
        raise

    total_processed = success_count + failure_count
    job.total_rows = job.total_rows or total_processed
    job.processed_rows = total_processed
    job.success_count = success_count
    job.failure_count = failure_count
    job.error_log = errors[-200:]
    job.updated_at = timezone.now()
    if failure_count and success_count == 0:
        job.status = ImportJobStatus.FAILED
    else:
        job.status = ImportJobStatus.COMPLETED
    job.save(
        update_fields=[
            "status",
            "processed_rows",
            "success_count",
            "failure_count",
            "error_log",
            "updated_at",
        ]
    )

    # Placeholder for webhook triggering logic
    Webhook.objects.filter(is_enabled=True, event_type=Webhook.EventType.IMPORT_COMPLETED)
    logger.info("Import job %s completed. Success: %s, Failure: %s", job.id, success_count, failure_count)

