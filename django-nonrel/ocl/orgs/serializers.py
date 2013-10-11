from django.contrib.auth.models import Group
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.fields import CharField, IntegerField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import LinkedResourceSerializer
from orgs.models import Organization


class OrganizationListSerializer(LinkedResourceSerializer):
    class Meta:
        model = Organization
        fields = ('mnemonic', 'name', 'url')
        lookup_field = 'org'


class OrganizationCreateSerializer(serializers.Serializer):
    mnemonic = serializers.CharField(required=True, max_length=100, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    name = serializers.CharField(required=True, max_length=100)
    company = serializers.CharField(required=False, max_length=100)
    website = serializers.CharField(required=False, max_length=255)

    class Meta:
        model = Organization
        fields = ('mnemonic', 'name', 'company', 'website')

    def restore_object(self, attrs, instance=None):
        mnemonic = attrs.get('mnemonic', None)
        if Organization.objects.filter(mnemonic=mnemonic).exists():
            self._errors['mnemonic'] = 'Organization with mnemonic %s already exists.' % mnemonic
            return None
        group = Group(name=mnemonic)
        organization = Organization(name=attrs.get('name'), mnemonic=mnemonic)
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


class OrganizationDetailSerializer(LinkedResourceSerializer):
    class Meta:
        model = Organization
        fields = ('resource_type', 'id', 'mnemonic', 'name', 'company', 'website', 'url', 'num_members', 'created_at', 'updated_at')
        lookup_field = 'org'

    def get_default_fields(self, *args, **kwargs):
        fields = super(OrganizationDetailSerializer, self).get_default_fields()
        fields.update({
            'resource_type': CharField(**kwargs),
            'num_members': IntegerField(**kwargs)
        })
        return fields
