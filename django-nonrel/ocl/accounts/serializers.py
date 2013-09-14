from django.contrib.auth.models import Group, User
from rest_framework import serializers
from rest_framework.fields import CharField
from accounts.models import UserProfile


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
        profile.preferred_locale = attrs.get('preferredLocale', None)
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


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')
