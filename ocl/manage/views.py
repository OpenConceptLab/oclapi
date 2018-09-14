import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from manage import serializers
from manage.models import Reference

logger = logging.getLogger('oclapi')

class ManageBrokenReferencesView(viewsets.ViewSet):

    serializer_class = serializers.ReferenceSerializer

    def initial(self, request, *args, **kwargs):
        self.permission_classes = (IsAdminUser, )
        super(ManageBrokenReferencesView, self).initial(request, *args, **kwargs)

    def list(self, request):
        broken_references = Reference.find_broken_references()

        serializer = serializers.ReferenceListSerializer(
             instance=broken_references)
        return Response(serializer.data)

