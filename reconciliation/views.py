from rest_framework import status
from rest_framework.response import Response
from rest_framework import parsers, renderers
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from celery.result import AsyncResult

from reconciliation.tasks import process_reconciliation
from reconciliation.serializers import FileUploadSerializer


class FileUploadView(GenericAPIView):
    serializer_class = FileUploadSerializer
    parser_classes = (
        parsers.FormParser,
        parsers.MultiPartParser,
        parsers.FileUploadParser,
    )
    renderer_classes = (renderers.JSONRenderer,)

    def post(self, request, *args, **kwargs):
        # Get files from the request
        source_file = request.FILES.get("source")
        target_file = request.FILES.get("target")

        # Get optional email and report format from the request
        email = request.data.get("email", None)  # Optional email field
        report_format = request.data.get("report_format", "json").lower()

        if not source_file or not target_file:
            return Response(
                {"error": "Both source and target files are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the report format
        if report_format not in ["html", "json", "csv"]:
            return Response(
                {"error": "Invalid report format. Choose 'html', 'json', or 'csv'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Process the reconciliation in the background using Celery
        task = process_reconciliation.delay(
            source_file.read().decode(),
            target_file.read().decode(),
            email=email,
            report_format=report_format,
        )

        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)


class ReconciliationResultView(APIView):

    def get(self, request, task_id, format=None):
        task_result = AsyncResult(task_id)

        if task_result.state == "PENDING":
            return Response({"status": "Processing..."})
        elif task_result.state == "SUCCESS":
            return Response(task_result.result)
        else:
            return Response(
                {"status": "Failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
