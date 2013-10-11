from django.contrib.auth.models import Group
from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.fields import HyperlinkedResourceIdentityField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import LinkedResourceSerializer
from orgs.models import Organization


class OrganizationListSerializer(LinkedResourceSerializer):
    id = serializers.CharField(source='mnemonic')
    name = serializers.CharField()

    class Meta:
        model = Organization


class OrganizationDetailSerializer(LinkedResourceSerializer):
    type = serializers.CharField(source='resource_type')
    uuid = serializers.CharField(source='id')
    id = serializers.CharField(source='mnemonic')
    name = serializers.CharField()
    company = serializers.CharField()
    website = serializers.CharField()
    members = serializers.IntegerField(source='num_members')
    publicSources = serializers.IntegerField(source='public_sources')
    createdOn = serializers.DateTimeField(source='created_at')
    updatedOn = serializers.DateTimeField(source='updated_at')

    class Meta:
        model = Organization

    def get_default_fields(self, *args, **kwargs):
        fields = super(OrganizationDetailSerializer, self).get_default_fields()
        fields.update({
            'members_url': HyperlinkedResourceIdentityField(view_name='organization-members'),
            'sources_url': HyperlinkedResourceIdentityField(view_name='source-list'),
        })
        return fields


class OrganizationCreateSerializer(serializers.Serializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    name = serializers.CharField(required=True)
    company = serializers.CharField(required=False)
    website = serializers.CharField(required=False)

    class Meta:
        model = Organization

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
    name = serializers.CharField(required=False)
    company = serializers.CharField(required=False)
    website = serializers.CharField(required=False)

    def restore_object(self, attrs, instance=None):
        instance.name = attrs.get('name', instance.name)
        instance.company = attrs.get('company', instance.company)
        instance.website = attrs.get('website', instance.website)
        return instance
