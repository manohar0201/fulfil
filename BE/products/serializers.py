from rest_framework import serializers

from .models import ImportJob, Product, Webhook


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "product_id",
            "name",
            "category",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ImportJobSerializer(serializers.ModelSerializer):
    progress_percent = serializers.FloatField(read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "original_filename",
            "status",
            "total_rows",
            "processed_rows",
            "success_count",
            "failure_count",
            "error_log",
            "created_at",
            "updated_at",
            "progress_percent",
        ]
        read_only_fields = fields


class WebhookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Webhook
        fields = [
            "id",
            "name",
            "url",
            "event_type",
            "is_enabled",
            "last_triggered_at",
            "last_response_status",
            "last_response_ms",
            "headers",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "last_triggered_at",
            "last_response_status",
            "last_response_ms",
            "created_at",
            "updated_at",
        ]

