from django.contrib import admin

from .models import ImportJob, Product, Webhook


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "name", "category", "is_active", "updated_at")
    search_fields = ("product_id", "name", "category")
    list_filter = ("is_active", "category")
    ordering = ("product_id",)


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_filename",
        "status",
        "processed_rows",
        "success_count",
        "failure_count",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("original_filename", "id")
    readonly_fields = ("created_at", "updated_at", "error_log")


@admin.register(Webhook)
class WebhookAdmin(admin.ModelAdmin):
    list_display = ("name", "event_type", "url", "is_enabled", "updated_at")
    list_filter = ("event_type", "is_enabled")
    search_fields = ("name", "url")
