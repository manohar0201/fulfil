import uuid
from pathlib import Path

from django.conf import settings
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ImportJob, Product, Webhook
from .serializers import ImportJobSerializer, ProductSerializer, WebhookSerializer
from .tasks import process_import_job


class ProductPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    pagination_class = ProductPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active", "category"]

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search")
        sku = self.request.query_params.get("sku")
        if sku:
            queryset = queryset.filter(product_id__iexact=sku)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(category__icontains=search)
                | Q(product_id__icontains=search)
            )
        return queryset

    @action(detail=False, methods=["delete"])
    def delete_all(self, request):
        count, _ = Product.objects.all().delete()
        return Response({"deleted": count}, status=status.HTTP_200_OK)


class ImportJobViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = ImportJob.objects.all()
    serializer_class = ImportJobSerializer
    pagination_class = PageNumberPagination


class WebhookViewSet(viewsets.ModelViewSet):
    queryset = Webhook.objects.all()
    serializer_class = WebhookSerializer
    pagination_class = PageNumberPagination

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        # Placeholder response; will enqueue actual webhook test later
        webhook = self.get_object()
        return Response(
            {
                "message": "Test trigger queued.",
                "webhook_id": str(webhook.id),
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ProductUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response({"detail": "CSV file is required under 'file' field."}, status=status.HTTP_400_BAD_REQUEST)

        upload_dir = Path(settings.MEDIA_ROOT) / "imports"
        upload_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid.uuid4()}_{csv_file.name}"
        stored_path = upload_dir / filename

        with stored_path.open("wb+") as destination:
            for chunk in csv_file.chunks():
                destination.write(chunk)

        job = ImportJob.objects.create(original_filename=csv_file.name)

        process_import_job.delay(str(job.id), str(stored_path))

        serializer = ImportJobSerializer(job)
        return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
