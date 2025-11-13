import uuid

from django.db import models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower


class Product(models.Model):
    """
    Represents a product that can be created through the UI or imported via CSV.
    """

    product_id = models.CharField(
        max_length=5,
        unique=False,
        help_text="5-character product identifier from the source system.",
    )
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(
                Lower("product_id"),
                name="unique_product_id_case_insensitive",
            ),
        ]
        indexes = [
            models.Index(Lower("product_id"), name="idx_product_product_id_ci"),
            models.Index(fields=["name"], name="idx_product_name"),
            models.Index(fields=["category"], name="idx_product_category"),
        ]
        ordering = ("product_id",)

    def __str__(self) -> str:
        return f"{self.product_id}: {self.name}"


class ImportJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class ImportJob(models.Model):
    """
    Tracks the lifecycle and progress of a CSV import run.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_filename = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=ImportJobStatus.choices, default=ImportJobStatus.PENDING
    )
    total_rows = models.PositiveIntegerField(default=0)
    processed_rows = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    error_log = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    @property
    def progress_percent(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round((self.processed_rows / self.total_rows) * 100, 2)

    def __str__(self) -> str:
        return f"ImportJob<{self.id}> [{self.status}]"


class Webhook(models.Model):
    """
    Stores webhook subscriptions for downstream integrations.
    """

    class EventType(models.TextChoices):
        PRODUCT_CREATED = "product.created", "Product Created"
        PRODUCT_UPDATED = "product.updated", "Product Updated"
        PRODUCT_DELETED = "product.deleted", "Product Deleted"
        IMPORT_COMPLETED = "import.completed", "Import Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    url = models.URLField()
    event_type = models.CharField(max_length=50, choices=EventType.choices)
    is_enabled = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    last_response_ms = models.PositiveIntegerField(null=True, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        unique_together = ("url", "event_type")

    def __str__(self) -> str:
        return f"{self.name} ({self.event_type})"
