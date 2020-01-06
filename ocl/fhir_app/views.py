import json
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response

from oclapi.views import BaseAPIView
from fhir_app.mixins import BaseFhirMixin
from fhir_app.mixins import CodeSystemFhirMixin
from fhir_app.mixins import ValueSetFhirMixin
from fhir_app.mixins import ConceptMapFhirMixin

__author__ = 'davetrig'

class BaseFhirView(BaseAPIView, BaseFhirMixin,):
    permission_classes = (AllowAny,)

    def get(self, object_type_values, request, *args, **kwargs):
        self.ocl_username = self.request.user.username

        ocl_object = None
        object_url = request.QUERY_PARAMS.get('url')
        if (object_url == None):
            return Response({'detail': 'must supply object url'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ocl_object = self.get_from_api(object_url)
        except:
            return Response({'detail': 'specified object url not found'}, status=status.HTTP_400_BAD_REQUEST)

        valid_type = True
        for type_value_key in object_type_values:
            if (object_type_values[type_value_key] != ocl_object.get(type_value_key)):
                valid_type = False

        if (not valid_type):
            expected_type = "/".join(object_type_values.values())
            return Response({'detail': 'specified object not of expected type %s'% expected_type}, status=status.HTTP_400_BAD_REQUEST)

        fhir_object = self.build_from_dictionary(ocl_object)

        return HttpResponse(json.dumps(fhir_object.as_json()))


class FhirCodeSystemView(BaseFhirView, CodeSystemFhirMixin,):
    def get(self, request, *args, **kwargs):
        object_type_values = {'type': 'Source'}
        return super(FhirCodeSystemView, self).get(object_type_values, request, *args, **kwargs)


class FhirValueSetView(BaseFhirView, ValueSetFhirMixin,):
    def get(self, request, *args, **kwargs):
        object_type_values = {'type': 'Collection'}
        return super(FhirValueSetView, self).get(object_type_values, request, *args, **kwargs)

class FhirConceptMapView(BaseFhirView, ConceptMapFhirMixin,):
    def get(self, request, *args, **kwargs):
        object_type_values = {'type': 'Source', 'source_type': 'ConceptMap'}
        return super(FhirConceptMapView, self).get(object_type_values, request, *args, **kwargs)

