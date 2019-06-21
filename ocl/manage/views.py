import logging
import uuid

from celery.result import AsyncResult
from django.http import HttpResponse
from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from manage import serializers
from tasks import find_broken_references, bulk_import

logger = logging.getLogger('oclapi')

class ManageBrokenReferencesView(viewsets.ViewSet):

    serializer_class = serializers.ReferenceSerializer

    def initial(self, request, *args, **kwargs):
        self.permission_classes = (IsAdminUser, )
        super(ManageBrokenReferencesView, self).initial(request, *args, **kwargs)

    def list(self, request):
        task = AsyncResult(request.GET.get('task'))

        if task.successful():
            broken_references = task.get()
            serializer = serializers.ReferenceListSerializer(
                instance=broken_references)
            return Response(serializer.data)
        elif task.failed():
            return Response({'exception': str(task.result)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'task': task.id, 'state': task.state})

    def post(self, request):
        task = find_broken_references.delay()

        return Response({'task': task.id, 'state': task.state})

    def delete(self, request):
        force = request.GET.get('force')
        if not force:
            force = False
        task = AsyncResult(request.GET.get('task'))

        if task.successful():
            broken_references = task.get()

            broken_references.delete(force)

            serializer = serializers.ReferenceListSerializer(
                instance=broken_references)
            return Response(serializer.data)
        elif task.failed():
            return Response({'exception': str(task.result)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'state': task.state}, status=status.HTTP_204_NO_CONTENT)


class BulkImportView(viewsets.ViewSet):

    def initial(self, request, *args, **kwargs):
        self.permission_classes = (IsAuthenticated, )
        super(BulkImportView, self).initial(request, *args, **kwargs)

    def list(self, request):
        task_id = request.GET.get('task')
        username = task_id[37:]
        user = self.request.user

        if not user.is_staff and user.username != username:
            return Response(status=status.HTTP_403_FORBIDDEN)

        task = AsyncResult(task_id)
        result_format = request.GET.get('result')

        if task.successful():
            result = task.get()
            if result_format == 'json':
                return HttpResponse(result.to_json(), content_type="application/json")
            elif result_format == 'report':
                return HttpResponse(result.display_report())
            else:
                return HttpResponse(result.get_detailed_summary())

        elif task.failed():
            return Response({'exception': str(task.result)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'task': task.id, 'state': task.state})


    def post(self, request):
        username = self.request.user.username
        update_if_exists = request.GET.get('update_if_exists', 'true')
        if update_if_exists == 'true':
            update_if_exists = True
        elif update_if_exists == 'false':
            update_if_exists = False
        else:
            return Response({'exception': 'update_if_exists must be either \'true\' or \'false\''}, status=status.HTTP_400_BAD_REQUEST)

        task = bulk_import.apply_async((request.body, username, update_if_exists), task_id=str(uuid.uuid4()) + '-' + username)

        return Response({'task': task.id, 'state': task.state})