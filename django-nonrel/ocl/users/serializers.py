import json

from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.fields import HyperlinkedResourceIdentityField
from users.models import UserProfile
from oclapi.models import NAMESPACE_REGEX


class UserListSerializer(serializers.Serializer):
    username = serializers.CharField()
    name = serializers.CharField()
    url = serializers.CharField()

    class Meta:
        model = UserProfile


class UserDetailSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type')
    uuid = serializers.CharField(source='id')
    username = serializers.CharField()
    name = serializers.CharField()
    company = serializers.CharField()
    location = serializers.CharField()
    email = serializers.CharField()
    orgs = serializers.IntegerField()
    publicSources = serializers.IntegerField(source='public_sources')
    createdOn = serializers.DateTimeField(source='created_at')
    updatedOn = serializers.DateTimeField(source='updated_at')
    url = serializers.CharField()
    extras = serializers.WritableField()

    class Meta:
        model = UserProfile

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserDetailSerializer, self).get_default_fields()
        fields.update({
            'sources_url': HyperlinkedResourceIdentityField(view_name='source-list'),
            'orgs_url': HyperlinkedResourceIdentityField(view_name='userprofile-orgs'),
        })
        return fields


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    company = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    preferredLocale = serializers.CharField(required=False, source='preferred_locale')
    extras = serializers.WritableField(required=False)

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
        profile.extras = attrs.get('extras', None)
        profile._user = user
        return profile

    def save_object(self, obj, **kwargs):
        user = obj._user
        user.save()
        del obj._user
        obj.user = user
        obj.save(**kwargs)


class UserUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, source='mnemonic')
    name = serializers.CharField(required=False, source='full_name')
    email = serializers.CharField(required=False)
    company = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    preferredLocale = serializers.CharField(required=False, source='preferred_locale')
    extras = serializers.WritableField(required=False)

    def restore_object(self, attrs, instance=None):
        if 'email' in attrs or 'mnemonic' in attrs:
            user = instance.user
            user.email = attrs.get('email', user.email)
            user.username = attrs.get('mnemonic', user.username)
        instance.full_name = attrs.get('full_name', instance.full_name)
        instance.company = attrs.get('company', instance.company)
        instance.location = attrs.get('location', instance.location)
        instance.mnemonic = attrs.get('mnemonic', instance.mnemonic)
        instance.preferred_locale = attrs.get('preferred_locale', instance.preferred_locale)
        instance.extras = attrs.get('extras', instance.extras)
        return instance

    def save_object(self, obj, **kwargs):
        super(UserUpdateSerializer, self).save_object(obj, **kwargs)
        user = obj.user
        user.save()
