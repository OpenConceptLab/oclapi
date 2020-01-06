from django.conf.urls import patterns, url, include
from fhir_app.views import FhirCodeSystemView
from fhir_app.views import FhirValueSetView
from fhir_app.views import FhirConceptMapView

__author__ = 'davetrig'

urlpatterns = patterns('',
    url(r'^CodeSystem/$', FhirCodeSystemView.as_view(), name='fhir-codesystem'),
    url(r'^ValueSet/$', FhirValueSetView.as_view(), name='fhir-valueset'),
    url(r'^ConceptMap/$', FhirConceptMapView.as_view(), name='fhir-conceptmap'),
)
