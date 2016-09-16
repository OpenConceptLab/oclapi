from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.fields import HyperlinkedResourceVersionIdentityField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import ResourceVersionSerializer
from collection.models import Collection, CollectionVersion, CollectionReference
from oclapi.models import ACCESS_TYPE_CHOICES, DEFAULT_ACCESS_TYPE
from oclapi.settings.common import Common
from tasks import update_children_for_resource_version

class CollectionListSerializer(serializers.Serializer):
    # TODO id and short code are same .. remove one of them
    id = serializers.CharField(required=True, source='mnemonic')
    short_code = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)
    url = serializers.CharField()
    owner = serializers.CharField(source='parent_resource')
    owner_type = serializers.CharField(source='parent_resource_type')
    owner_url = serializers.CharField(source='parent_url')

    class Meta:
        model = Collection


class CollectionCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = Collection
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        collection = instance if instance else Collection()
        collection.mnemonic = attrs.get(self.Meta.lookup_field, collection.mnemonic)
        collection.name = attrs.get('name', collection.name)
        collection.full_name = attrs.get('full_name', collection.full_name)
        collection.description = attrs.get('description', collection.description)
        collection.collection_type = attrs.get('collection_type', collection.collection_type)
        collection.public_access = attrs.get('public_access', collection.public_access or DEFAULT_ACCESS_TYPE)
        collection.default_locale=attrs.get('default_locale', collection.default_locale or Common.DEFAULT_LOCALE)
        collection.website = attrs.get('website', collection.website)
        collection.supported_locales = attrs.get('supported_locales').split(',') if attrs.get('supported_locales') else collection.supported_locales
        collection.extras = attrs.get('extras', collection.extras)
        collection.external_id = attrs.get('external_id', collection.external_id)
        return collection


class CollectionCreateSerializer(CollectionCreateOrUpdateSerializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    short_code = serializers.CharField(source='mnemonic', read_only=True)
    name = serializers.CharField(required=True)
    full_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    collection_type = serializers.CharField(required=False)
    public_access = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES)
    default_locale = serializers.CharField(required=False)
    supported_locales = serializers.CharField(required=False)
    website = serializers.CharField(required=False)
    url = serializers.CharField(read_only=True)
    versions_url = serializers.CharField(read_only=True)
    concepts_url = serializers.CharField(read_only=True)
    mappings_url = serializers.CharField(read_only=True)
    owner = serializers.CharField(source='parent_resource', read_only=True)
    owner_type = serializers.CharField(source='parent_resource_type', read_only=True)
    owner_url = serializers.CharField(source='parent_url', read_only=True)
    versions = serializers.IntegerField(source='num_versions', read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Collection.persist_new(obj, request_user, **kwargs)
        self._errors.update(errors)


class CollectionReferenceSerializer(serializers.ModelSerializer):
    reference_type = serializers.CharField(read_only=True)

    class Meta:
        fields = ('expression', 'reference_type',)
        model = CollectionReference


class CollectionDetailSerializer(CollectionCreateOrUpdateSerializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    id = serializers.CharField(required=False, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    short_code = serializers.CharField(source='mnemonic', read_only=True)
    name = serializers.CharField(required=False)
    full_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    external_id = serializers.CharField(required=False)
    collection_type = serializers.CharField(required=False)
    public_access = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES)
    default_locale = serializers.CharField(required=False)
    supported_locales = serializers.CharField(required=False)
    website = serializers.CharField(required=False)
    url = serializers.CharField(read_only=True)
    versions_url = serializers.CharField(read_only=True)
    concepts_url = serializers.CharField(read_only=True)
    mappings_url = serializers.CharField(read_only=True)
    owner = serializers.CharField(source='parent_resource', read_only=True)
    owner_type = serializers.CharField(source='parent_resource_type', read_only=True)
    owner_url = serializers.CharField(source='parent_url', read_only=True)
    versions = serializers.IntegerField(source='num_versions', read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)
    references = CollectionReferenceSerializer(many=True)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Collection.persist_changes(obj, request_user, **kwargs)
        if errors:
            self._errors.update(errors)
        else:
            head_obj = obj.get_head();
            head_obj.update_version_data(obj)
            head_obj.save();


class CollectionVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='mnemonic')
    released = serializers.CharField()
    owner = serializers.CharField(source='parent_resource')
    owner_type = serializers.CharField(source='parent_resource_type')
    owner_url = serializers.CharField(source='parent_url')

    class Meta:
        model = CollectionVersion
        versioned_object_view_name = 'collection-detail'
        versioned_object_field_name = 'url'


class CollectionVersionCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = CollectionVersion
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        instance.mnemonic = attrs.get(self.Meta.lookup_field, instance.mnemonic)
        instance.description = attrs.get('description', instance.description)
        instance.released = attrs.get('released', instance.released)
        instance._previous_version_mnemonic = attrs.get('previous_version_mnemonic', instance.previous_version_mnemonic)
        instance._parent_version_mnemonic = attrs.get('parent_version_mnemonic', instance.parent_version_mnemonic)
        instance.extras = attrs.get('extras', instance.extras)
        instance.external_id = attrs.get('external_id', instance.external_id)
        return instance

    def save_object(self, obj, **kwargs):
        errors = CollectionVersion.persist_changes(obj, **kwargs)
        self._errors.update(errors)


class CollectionVersionUpdateSerializer(CollectionVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=False, source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previous_version = serializers.CharField(required=False, source='previous_version_mnemonic')
    parent_version = serializers.CharField(required=False, source='parent_version_mnemonic')
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)


class CollectionVersionDetailSerializer(ResourceVersionSerializer):
    type = serializers.CharField(required=True, source='resource_type')
    id = serializers.CharField(required=True, source='mnemonic')
    description = serializers.CharField()
    released = serializers.BooleanField()
    owner = serializers.CharField(source='parent_resource')
    owner_type = serializers.CharField(source='parent_resource_type')
    owner_url = serializers.CharField(source='parent_url')
    created_on = serializers.DateTimeField(source='created_at')
    updated_on = serializers.DateTimeField(source='updated_at')
    extras = serializers.WritableField()
    external_id = serializers.CharField(required=False)
    references = CollectionReferenceSerializer(many=True)

    class Meta:
        model = CollectionVersion
        versioned_object_view_name = 'collection-detail'
        versioned_object_field_name = 'collectionUrl'

    def get_default_fields(self):
        default_fields = super(CollectionVersionDetailSerializer, self).get_default_fields()
        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)
        default_fields.update(
            {
                'parentVersionUrl': HyperlinkedResourceVersionIdentityField(related_attr='parent_version', view_name=self.opts.view_name),
                'previousVersionUrl': HyperlinkedResourceVersionIdentityField(related_attr='previous_version', view_name=self.opts.view_name),
            }
        )
        return default_fields


class CollectionVersionCreateSerializer(CollectionVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previous_version = serializers.CharField(required=False, source='previous_version_mnemonic')
    parent_version = serializers.CharField(required=False, source='parent_version_mnemonic')
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)

    def restore_object(self, attrs, instance=None):
        version = CollectionVersion()
        version.mnemonic = attrs.get(self.Meta.lookup_field)
        return super(CollectionVersionCreateSerializer, self).restore_object(attrs, instance=version)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = CollectionVersion.persist_new(obj, user=request_user, **kwargs)
        if errors:
            self._errors.update(errors)
        else:
            update_children_for_resource_version.delay(obj.id, 'collection')
