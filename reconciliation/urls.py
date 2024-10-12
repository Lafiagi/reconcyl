from django.urls import path
from reconciliation.views import FileUploadView, ReconciliationResultView

urlpatterns = [
    path("upload/", FileUploadView.as_view(), name="file-upload"),
    path(
        "results/<str:task_id>/",
        ReconciliationResultView.as_view(),
        name="reconciliation-result",
    ),
]
