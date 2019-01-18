from rest_framework import routers

from manage.views import ManageBrokenReferencesView, BulkImportView

router = routers.DefaultRouter()
router.register(r'brokenreferences', ManageBrokenReferencesView, base_name='brokenreferences')
router.register(r'bulkimport', BulkImportView, base_name='bulkimport')

urlpatterns = router.urls

