import logging

from celery.result import AsyncResult
from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from manage import serializers
from tasks import find_broken_references

logger = logging.getLogger('oclapi')

class ManageBrokenReferencesView(viewsets.ViewSet):

    serializer_class = serializers.ReferenceSerializer

    def initial(self, request, *args, **kwargs):
        self.permission_classes = (IsAdminUser, )
        super(ManageBrokenReferencesView, self).initial(request, *args, **kwargs)

    def list(self, request):
        task = AsyncResult(request.GET.get('task'))

        if (task.successful() or task.failed()):
            broken_references = task.get()
            serializer = serializers.ReferenceListSerializer(
                instance=broken_references)
            return Response(serializer.data)
        else:
            return Response({'task': task.id, 'state': task.state})

    def post(self, request):
        task = find_broken_references.delay()

        return Response({'task': task.id, 'state': task.state})

    def delete(self, request):
        task = AsyncResult(request.GET.get('task'))

        if (task.successful() or task.failed()):
            broken_references = task.get()

            broken_references.delete()

            serializer = serializers.ReferenceListSerializer(
                instance=broken_references)
            return Response(serializer.data)
        else:
            return Response({'state': task.state}, status=status.HTTP_204_NO_CONTENT)