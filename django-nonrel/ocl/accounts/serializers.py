from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework.fields import CharField
from accounts.models import UserProfile, Organization


class UserListSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('username', 'name', 'url')

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserListSerializer, self).get_default_fields()
        fields.update({
            'username': CharField(**kwargs),
            'name': CharField(**kwargs),
        })
        return fields


class UserCreateSerializer(serializers.Serializer):
    name = serializers.CharField(required=True, max_length=100)
    email = serializers.CharField(required=True, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    location = serializers.CharField(required=False, max_length=100)
    preferredLocale = serializers.CharField(required=False, max_length=20, source='preferred_locale')

    def restore_object(self, attrs, instance=None):
        email = attrs.get('email')
        user = User(username=email, email=email)
        profile = UserProfile(full_name=attrs.get('name'))
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
    name = serializers.CharField(required=False, max_length=100, source='full_name')
    email = serializers.CharField(required=False, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    location = serializers.CharField(required=False, max_length=100)
    preferredLocale = serializers.CharField(required=False, max_length=20, source='preferred_locale')

    def restore_object(self, attrs, instance=None):
        if 'email' in attrs:
            email = attrs.pop('email')
            user = instance.user
            user.email = email
        instance.full_name = attrs.get('full_name', instance.full_name)
        instance.location = attrs.get('location', instance.location)
        instance.preferred_locale = attrs.get('preferred_locale', instance.preferred_locale)
        return instance

    def save_object(self, obj, **kwargs):
        super(UserUpdateSerializer, self).save_object(obj, **kwargs)
        user = obj.user
        user.save()


class UserDetailSerializer(serializers.HyperlinkedModelSerializer):
    class Meta(UserUpdateSerializer.Meta):
        model = UserProfile
        fields = ('type', 'uuid', 'username', 'name', 'company', 'location', 'email', 'preferred_locale', 'url', 'created_at', 'updated_at')

    def get_default_fields(self, *args, **kwargs):
        fields = super(UserDetailSerializer, self).get_default_fields()
        fields.update({
            'type': CharField(**kwargs),
            'username': CharField(**kwargs),
            'name': CharField(**kwargs),
            'email': CharField(**kwargs),
        })
        return fields


class OrganizationListSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organization
        fields = ('mnemonic', 'name', 'url')

    def get_default_fields(self, *args, **kwargs):
        fields = super(OrganizationListSerializer, self).get_default_fields()
        fields.update({
            'mnemonic': CharField(**kwargs)
        })
        return fields


class OrganizationCreateSerializer(serializers.Serializer):
    mnemonic = serializers.CharField(required=True, max_length=100)
    name = serializers.CharField(required=True, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    website = serializers.CharField(required=False, max_length=255)

    class Meta:
        model = Organization
        fields = ('mnemonic', 'name', 'company', 'website')

    def restore_object(self, attrs, instance=None):
        mnemonic = attrs.get('mnemonic', None)
        group = Group(name=mnemonic)
        organization = Organization(name=attrs.get('name'))
        organization.company = attrs.get('company', None)
        organization.website = attrs.get('website', None)
        organization._group = group
        return organization

    def save_object(self, obj, **kwargs):
        group = obj._group
        group.save()
        del obj._group
        obj.group = group
        obj.save(**kwargs)


class OrganizationUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    website = serializers.CharField(required=False, max_length=255)


    def restore_object(self, attrs, instance=None):
        instance.name = attrs.get('name', instance.name)
        instance.company = attrs.get('company', instance.company)
        instance.website = attrs.get('website', instance.website)
        return instance


class OrganizationDetailSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organization
        fields = ('type', 'uuid', 'mnemonic', 'name', 'company', 'website', 'url', 'created_at', 'updated_at')

    def get_default_fields(self, *args, **kwargs):
        fields = super(OrganizationDetailSerializer, self).get_default_fields()
        fields.update({
            'type': CharField(**kwargs),
            'mnemonic': CharField(**kwargs)
        })
        return fields
