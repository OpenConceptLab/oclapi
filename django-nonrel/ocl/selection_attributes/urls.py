from django.conf.urls import patterns, url, include
from selection_attributes.views import ConceptClassView, ConceptDataTypeView, NameLocaleView


urlpatterns = patterns(
    '',
    url(r'^concept-classes/', ConceptClassView.as_view(), name='concept-classes'),
    url(r'^concept-datatypes/', ConceptDataTypeView.as_view(), name='concept-datatypes'),
    url(r'^name-locales/', NameLocaleView.as_view(), name='name-locales'),
)