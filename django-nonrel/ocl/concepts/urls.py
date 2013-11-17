from django.conf.urls.defaults import patterns, url
from concepts.views import ConceptCreateView, ConceptRetrieveUpdateDestroyView, ConceptVersionRetrieveView

__author__ = 'misternando'

urlpatterns = patterns('',
    url(r'^$', ConceptCreateView.as_view(), name='concept-create'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/$', ConceptRetrieveUpdateDestroyView.as_view(), name='concept-detail'),
    url(r'^(?P<concept>[a-zA-Z0-9\-\.]+)/(?P<concept_version>[a-zA-Z0-9\-\.]+)/$', ConceptVersionRetrieveView.as_view(), name='conceptversion-detail'),
)

