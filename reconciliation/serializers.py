from rest_framework import serializers


class FileUploadSerializer(serializers.Serializer):
    source = serializers.FileField()
    target = serializers.FileField()
    email = serializers.CharField(required=False)
    report_format = serializers.CharField(required=False)


class ReconciliationResulSerializer(serializers.Serializer):
    report_format = serializers.CharField(required=False)
