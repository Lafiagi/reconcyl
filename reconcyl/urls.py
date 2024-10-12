from django.urls import include, path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from reconciliation.urls import urlpatterns


schema_view = get_schema_view(
    openapi.Info(
        title="Reconcyl API",
        default_version="v1",
        description="API documentation for the Reconcyl project",
    ),
    public=False,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path("api/v1/reconcile/", include(urlpatterns)),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
