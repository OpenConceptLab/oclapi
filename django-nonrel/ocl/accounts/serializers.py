from django.contrib.auth.models import Group
from rest_framework import serializers
from rest_framework.fields import CharField
from accounts.models import UserProfile


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('type', 'uuid', 'username', 'name', 'company', 'location', 'email', 'preferred_locale', 'url', 'created_at', 'updated_at')

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserSerializer, self).get_default_fields()
        fields.update({
            'type': CharField(**kwargs),
            'username': CharField(**kwargs),
            'name': CharField(**kwargs),
            'company': CharField(**kwargs),
            'location': CharField(**kwargs),
            'email': CharField(**kwargs),
        })
        return fields

class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
