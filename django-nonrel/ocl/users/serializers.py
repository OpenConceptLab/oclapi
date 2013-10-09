from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.fields import CharField, IntegerField
from oclapi.serializers import HyperlinkedModelSerializer
from users.models import UserProfile
from oclapi.models import NAMESPACE_REGEX


class UserListSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('username', 'name', 'url')
        lookup_field = 'user'

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserListSerializer, self).get_default_fields()
        fields.update({
            'username': CharField(**kwargs),
            'name': CharField(**kwargs),
        })
        return fields


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, max_length=100, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    name = serializers.CharField(required=True, max_length=100)
    email = serializers.CharField(required=True, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    location = serializers.CharField(required=False, max_length=100)
    preferredLocale = serializers.CharField(required=False, max_length=20, source='preferred_locale')

    def restore_object(self, attrs, instance=None):
        username = attrs.get('username')
        if UserProfile.objects.filter(mnemonic=username).exists():
            self._errors['username'] = 'User with username %s already exists.' % username
            return None
        email = attrs.get('email')
        user = User(username=username, email=email)
        profile = UserProfile(full_name=attrs.get('name'), mnemonic=username)
        profile.company = attrs.get('company', None)
        profile.location = attrs.get('location', None)
        profile.preferred_locale = attrs.get('preferred_locale', None)
        profile._user = user
        return profile

    def save_object(self, obj, **kwargs):
        user = obj._user
        user.save()
        del obj._user
        obj.user = user
        obj.save(**kwargs)


class UserUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, max_length=100, source='mnemonic')
    name = serializers.CharField(required=False, max_length=100, source='full_name')
    email = serializers.CharField(required=False, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    location = serializers.CharField(required=False, max_length=100)
    preferredLocale = serializers.CharField(required=False, max_length=20, source='preferred_locale')

    def restore_object(self, attrs, instance=None):
        if 'email' in attrs or 'mnemonic' in attrs:
            user = instance.user
            user.email = attrs.get('email', user.email)
            user.username = attrs.get('mnemonic', user.username)
        instance.full_name = attrs.get('full_name', instance.full_name)
        instance.location = attrs.get('location', instance.location)
        instance.mnemonic = attrs.get('mnemonic', instance.mnemonic)
        instance.preferred_locale = attrs.get('preferred_locale', instance.preferred_locale)
        return instance

    def save_object(self, obj, **kwargs):
        super(UserUpdateSerializer, self).save_object(obj, **kwargs)
        user = obj.user
        user.save()


class UserDetailSerializer(HyperlinkedModelSerializer):
    class Meta(UserUpdateSerializer.Meta):
        model = UserProfile
        fields = ('resource_type', 'id', 'username', 'name', 'company', 'location', 'email', 'preferred_locale', 'url', 'orgs', 'created_at', 'updated_at')
        lookup_field = 'user'

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserDetailSerializer, self).get_default_fields()
        fields.update({
            'resource_type': CharField(**kwargs),
            'username': CharField(**kwargs),
            'name': CharField(**kwargs),
            'email': CharField(**kwargs),
            'orgs': IntegerField(**kwargs),
        })
        return fields
