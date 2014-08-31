from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.fields import HyperlinkedResourceIdentityField
from oclapi.models import NAMESPACE_REGEX, DEFAULT_ACCESS_TYPE, ACCESS_TYPE_CHOICES
from orgs.models import Organization


class OrganizationListSerializer(serializers.Serializer):
    id = serializers.CharField(source='mnemonic')
    name = serializers.CharField()
    url = serializers.CharField()

    class Meta:
        model = Organization


class OrganizationCreateSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    public_access = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE)
    name = serializers.CharField(required=True)
    company = serializers.CharField(required=False)
    website = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    members = serializers.IntegerField(source='num_members', read_only=True)
    public_collections = serializers.IntegerField(read_only=True)
    public_sources = serializers.IntegerField(read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    url = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)

    class Meta:
        model = Organization

    def restore_object(self, attrs, instance=None):
        request_user = self.context['request'].user
        mnemonic = attrs.get('mnemonic', None)
        if Organization.objects.filter(mnemonic=mnemonic).exists():
            self._errors['mnemonic'] = 'Organization with mnemonic %s already exists.' % mnemonic
            return None
        organization = Organization(name=attrs.get('name'), mnemonic=mnemonic)
        organization.created_by = request_user
        organization.updated_by = request_user
        organization.public_access = attrs.get('public_access', DEFAULT_ACCESS_TYPE)
        organization.company = attrs.get('company', None)
        organization.website = attrs.get('website', None)
        organization.location = attrs.get('location', None)
        organization.extras = attrs.get('extras', None)
        return organization


class OrganizationDetailSerializer(serializers.Serializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    id = serializers.CharField(source='mnemonic', read_only=True)
    public_access = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES, default=DEFAULT_ACCESS_TYPE)
    name = serializers.CharField(required=False)
    company = serializers.CharField(required=False)
    website = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    members = serializers.IntegerField(source='num_members', read_only=True)
    public_collections = serializers.IntegerField(read_only=True)
    public_sources = serializers.IntegerField(read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    url = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)

    class Meta:
        model = Organization

    def get_default_fields(self, *args, **kwargs):
        fields = super(OrganizationDetailSerializer, self).get_default_fields()
        fields.update({
            'members_url': HyperlinkedResourceIdentityField(view_name='organization-members'),
            'sources_url': HyperlinkedResourceIdentityField(view_name='source-list'),
            'collections_url': HyperlinkedResourceIdentityField(view_name='collection-list')
        })
        return fields

    def restore_object(self, attrs, instance=None):
        request_user = self.context['request'].user
        instance.public_access = attrs.get('public_access', instance.public_access)
        instance.name = attrs.get('name', instance.name)
        instance.company = attrs.get('company', instance.company)
        instance.website = attrs.get('website', instance.website)
        instance.location = attrs.get('location', instance.website)
        instance.extras = attrs.get('extras', instance.extras)
        instance.updated_by = request_user
        return instance
