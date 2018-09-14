from rest_framework import routers

from manage.views import ManageBrokenReferencesView

router = routers.DefaultRouter()
router.register(r'brokenreferences', ManageBrokenReferencesView, base_name='brokenreferences')

urlpatterns = router.urls

