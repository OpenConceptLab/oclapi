from rest_framework import generics
from users.models import UserProfile


class SubresourceMixin(generics.GenericAPIView):
    user_is_self = False
    parent_resource = None
    parent_resource_type = None
    parent_resource_kwarg = None
    parent_resource_lookup = None
    additional_serializer_context = {}

    def initial(self, request, *args, **kwargs):
        super(SubresourceMixin, self).initial(request, *args, **kwargs)
        if kwargs.pop('user_is_self', False):
            self.user_is_self = True
            self.parent_resource = request.user.get_profile()
            self.parent_resource_type = UserProfile
        else:
            self.parent_resource_type = kwargs.pop('related_object_type', None)
            self.parent_resource_kwarg = kwargs.pop('related_object_kwarg', None)
            if self.parent_resource_type and self.parent_resource_kwarg:
                self.parent_resource_lookup = kwargs.pop(self.parent_resource_kwarg)
                self.parent_resource = self.parent_resource_type.objects.get(mnemonic=self.parent_resource_lookup)
