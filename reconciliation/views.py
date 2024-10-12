import json

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework import parsers, renderers
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from celery.result import AsyncResult

from reconciliation.tasks import (
    process_reconciliation,
    generate_csv_report,
    generate_html_report,
)
from reconciliation.serializers import (
    FileUploadSerializer,
    ReconciliationResulSerializer,
)


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

        return Response(
            {
                "task_id": task.id,
                "message": "Use the task_id to check the status of the task",
            },
            status=status.HTTP_202_ACCEPTED,
        )


class ReconciliationResultView(APIView):
    
    def get(self, request, task_id, format=None):
        task_result = AsyncResult(task_id)

        # Check task status
        if task_result.state == "PENDING":
            return Response(
                {"status": "Processing..."}, status=status.HTTP_202_ACCEPTED
            )

        elif task_result.state == "SUCCESS":
            # Get the report data and requested format
            report_data = task_result.result
            report_format = request.query_params.get("format", "json")

            if report_format == "json":
                response = HttpResponse(
                    json.dumps(report_data, indent=4), content_type="application/json"
                )
                response["Content-Disposition"] = (
                    'attachment; filename="reconciliation_report.json"'
                )
            elif report_format == "csv":
                csv_report = generate_csv_report(report_data)
                response = HttpResponse(csv_report, content_type="text/csv")
                response["Content-Disposition"] = (
                    'attachment; filename="reconciliation_report.csv"'
                )
            elif report_format == "html":
                html_report = generate_html_report(report_data)
                response = HttpResponse(html_report, content_type="text/html")
                response["Content-Disposition"] = (
                    'attachment; filename="reconciliation_report.html"'
                )
            else:
                return Response(
                    {"error": "Invalid report format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return response

        else:
            return Response(
                {"status": "Failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
