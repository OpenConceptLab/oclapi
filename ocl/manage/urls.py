from django.conf.urls import patterns, url

from manage.views import ManageBrokenReferencesView, BulkImportView
from oclapi.models import NAMESPACE_PATTERN

urlpatterns = patterns(
    '',
    url(r'^brokenreferences/$', ManageBrokenReferencesView.as_view(), name='brokenreferences-list'),
    url(r'^bulkimport/$', BulkImportView.as_view(), name='bulkimport-list'),
    url(r'^bulkimport/(?P<import_queue>' + NAMESPACE_PATTERN + ')/$', BulkImportView.as_view(), name='bulkimport-detail'),
)

