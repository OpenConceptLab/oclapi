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


class UserCreateSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    username = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    name = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    company = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    preferred_locale = serializers.CharField(required=False)
    orgs = serializers.IntegerField(read_only=True)
    public_collections = serializers.IntegerField(read_only=True)
    public_sources = serializers.IntegerField(read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)

    def restore_object(self, attrs, instance=None):
        request_user = self.context['request'].user
        username = attrs.get('username')
        if UserProfile.objects.filter(mnemonic=username).exists():
            self._errors['username'] = 'User with username %s already exists.' % username
            return None
        email = attrs.get('email')
        user = User(username=username, email=email)
        profile = UserProfile(full_name=attrs.get('name'), mnemonic=username)
        profile.created_by = request_user
        profile.updated_by = request_user
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


class UserDetailSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    username = serializers.CharField(required=False)
    name = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    company = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    preferred_locale = serializers.CharField(required=False)
    orgs = serializers.IntegerField(read_only=True)
    public_collections = serializers.IntegerField(read_only=True)
    public_sources = serializers.IntegerField(read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)
    url = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)

    class Meta:
        model = UserProfile

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserDetailSerializer, self).get_default_fields()
        fields.update({
            'sources_url': HyperlinkedResourceIdentityField(view_name='source-list'),
            'collections_url': HyperlinkedResourceIdentityField(view_name='collection-list'),
            'orgs_url': HyperlinkedResourceIdentityField(view_name='userprofile-orgs'),
        })
        return fields

    def restore_object(self, attrs, instance=None):
        request_user = self.context['request'].user
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
        instance.updated_by = request_user
        return instance

    def save_object(self, obj, **kwargs):
        super(UserDetailSerializer, self).save_object(obj, **kwargs)
        user = obj.user
        user.save()
