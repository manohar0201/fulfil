from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from django.db import transaction

from .models import ImportJob, ImportJobStatus, Product

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = {"product_id", "name", "category"}
ROW_UPDATE_BATCH_SIZE = 500


class ImportErrorEntry(Dict[str, str]):
    """Typed alias for error log entries."""


def import_products_from_csv(csv_path: Path, job: ImportJob) -> Tuple[int, int, List[ImportErrorEntry]]:
    """
    Parse a CSV file and upsert products while tracking job progress.

    Returns:
        success_count, failure_count, error_entries
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    errors: List[ImportErrorEntry] = []
    success_count = 0
    failure_count = 0

    with csv_path.open(newline="", encoding="utf-8") as fh:
        total_rows = max(sum(1 for _ in fh) - 1, 0)  # subtract header
        fh.seek(0)
        reader = csv.DictReader(fh)

        if reader.fieldnames is None:
            raise ValueError("CSV file is missing a header row.")

        missing = EXPECTED_COLUMNS - set(field.lower() for field in reader.fieldnames)
        if missing:
            raise ValueError(f"CSV header missing required columns: {', '.join(sorted(missing))}")

        job.status = ImportJobStatus.PROCESSING
        job.total_rows = total_rows
        job.processed_rows = 0
        job.success_count = 0
        job.failure_count = 0
        job.error_log = []
        job.save(update_fields=["status", "total_rows", "processed_rows", "success_count", "failure_count", "error_log", "updated_at"])

        for index, raw_row in enumerate(reader, start=1):
            row = {k.lower(): (v or "").strip() for k, v in raw_row.items()}
            product_id = row.get("product_id", "")
            name = row.get("name", "")
            category = row.get("category", "")

            if not product_id or not product_id.isdigit() or len(product_id) != 5:
                failure_count += 1
                errors.append(
                    {
                        "row": index,
                        "product_id": product_id,
                        "error": "Invalid product_id (expected 5-digit number).",
                    }
                )
                continue

            if not name:
                failure_count += 1
                errors.append({"row": index, "product_id": product_id, "error": "Missing product name."})
                continue

            if not category:
                failure_count += 1
                errors.append({"row": index, "product_id": product_id, "error": "Missing category."})
                continue

            with transaction.atomic():
                product = Product.objects.filter(product_id__iexact=product_id).first()
                if product:
                    product.name = name
                    product.category = category
                    product.save(update_fields=["name", "category", "updated_at"])
                else:
                    Product.objects.create(
                        product_id=product_id,
                        name=name,
                        category=category,
                        is_active=True,
                    )

            success_count += 1

            if index % ROW_UPDATE_BATCH_SIZE == 0:
                job.processed_rows = index
                job.success_count = success_count
                job.failure_count = failure_count
                job.error_log = errors[-50:]  # keep recent errors for polling
                job.save(
                    update_fields=[
                        "processed_rows",
                        "success_count",
                        "failure_count",
                        "error_log",
                        "updated_at",
                    ]
                )

    return success_count, failure_count, errors

