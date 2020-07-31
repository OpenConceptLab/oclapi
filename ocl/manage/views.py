import logging
import json
import requests
from requests.auth import HTTPBasicAuth

from celery.result import AsyncResult
from django.http import HttpResponse
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from manage import serializers
from tasks import find_broken_references, queue_bulk_import, parse_bulk_import_task_id, task_exists, flower_get

logger = logging.getLogger('oclapi')


class ManageBrokenReferencesView(APIView):

    serializer_class = serializers.ReferenceSerializer

    def initial(self, request, *args, **kwargs):
        self.permission_classes = (IsAdminUser, )
        super(ManageBrokenReferencesView, self).initial(request, *args, **kwargs)

    def get(self, request):
        task = AsyncResult(request.GET.get('task'))

        if task.successful():
            broken_references = task.get()
            serializer = serializers.ReferenceListSerializer(
                instance=broken_references)
            return Response(serializer.data)
        elif task.failed():
            return Response({'exception': str(task.result)}, status=status.HTTP_400_BAD_REQUEST)
        elif task.state == 'PENDING' and not task_exists(task.id):
            return Response({'exception': 'task '+ task.id +' not found'}, status=status.HTTP_404_NOT_FOUND)
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


class BulkImportView(APIView):

    def initial(self, request, *args, **kwargs):
        self.permission_classes = (IsAuthenticated, )
        super(BulkImportView, self).initial(request, *args, **kwargs)

    def get(self, request, import_queue=None):
        task_id = request.GET.get('task')
        username = request.GET.get('username')
        user = self.request.user

        if task_id:
            parsed_task = parse_bulk_import_task_id(task_id)
            username = parsed_task['username']

            if not user.is_staff and user.username != username:
                return Response(status=status.HTTP_403_FORBIDDEN)

            task = AsyncResult(task_id)
            result_format = request.GET.get('result')

            if task.successful():
                result = task.get()
                if result_format == 'json':
                    response =  HttpResponse(result.json, content_type="application/json")
                    response['Content-Encoding'] = 'gzip'
                    return response
                elif result_format == 'report':
                    return HttpResponse(result.report)
                else:
                    return HttpResponse(result.detailed_summary)
            elif task.failed():
                return Response({'exception': str(task.result)}, status=status.HTTP_400_BAD_REQUEST)
            elif task.state == 'PENDING' and not task_exists(task_id):
                return Response({'exception': 'task '+ task_id +' not found'}, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({'task': task.id, 'state': task.state, 'username' : username, 'queue': parsed_task['queue']})
        else:
            flower_tasks = flower_get('api/tasks').json()
            tasks = []
            for task_id, value in flower_tasks.items():
                if not value['name'].startswith('tasks.bulk_import'):
                    continue

                task = parse_bulk_import_task_id(task_id)
                if user.is_staff or user.username == task['username']:
                    if (not import_queue or task['queue'] == import_queue) and (not username or task['username'] == username):
                        tasks.append({'task': task_id, 'state': value['state'], 'queue': task['queue'], 'username': task['username']})

            return Response(tasks)

    def post(self, request, import_queue=None):
        username = self.request.user.username
        update_if_exists = request.GET.get('update_if_exists', 'true')
        if update_if_exists == 'true':
            update_if_exists = True
        elif update_if_exists == 'false':
            update_if_exists = False
        else:
            return Response({'exception': 'update_if_exists must be either \'true\' or \'false\''}, status=status.HTTP_400_BAD_REQUEST)

        task = queue_bulk_import(request.body, import_queue, username, update_if_exists)
        parsed_task = parse_bulk_import_task_id(task.id)

        return Response({'task': task.id, 'state': task.state, 'username' : username, 'queue': parsed_task['queue']})



