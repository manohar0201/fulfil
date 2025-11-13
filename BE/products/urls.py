from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ImportJobViewSet, ProductUploadView, ProductViewSet, WebhookViewSet

router = DefaultRouter()
router.register(r"products", ProductViewSet, basename="product")
router.register(r"import-jobs", ImportJobViewSet, basename="import-job")
router.register(r"webhooks", WebhookViewSet, basename="webhook")

urlpatterns = router.urls + [
    path("uploads/csv/", ProductUploadView.as_view(), name="product-upload"),
]