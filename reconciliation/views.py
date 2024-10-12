from rest_framework import status
from rest_framework.response import Response
from rest_framework import parsers, renderers
from rest_framework.generics import GenericAPIView

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
        source_file = request.FILES.get("source")
        target_file = request.FILES.get("target")

        if not source_file or not target_file:
            return Response(
                {"error": "Both source and target files are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Pass the files to a background task for reconciliation processing
        task = process_reconciliation.delay(
            source_file.read().decode(), target_file.read().decode()
        )

        return Response({"task_id": task.id}, status=status.HTTP_202_ACCEPTED)
