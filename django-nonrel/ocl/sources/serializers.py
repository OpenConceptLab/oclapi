from django.core.validators import RegexValidator
from rest_framework import serializers
from concepts.models import Concept
from mappings.models import Mapping
from oclapi.fields import HyperlinkedResourceVersionIdentityField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import ResourceVersionSerializer
from sources.models import Source, SourceVersion
from oclapi.models import ACCESS_TYPE_CHOICES, DEFAULT_ACCESS_TYPE
from tasks import update_children_for_resource_version
from oclapi.settings.common import Common


class SourceListSerializer(serializers.Serializer):
    short_code = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)
    url = serializers.CharField()
    owner = serializers.CharField(source='parent_resource')
    owner_type = serializers.CharField(source='parent_resource_type')
    owner_url = serializers.CharField(source='parent_url')

    class Meta:
        model = Source


class SourceCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = Source
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        source = instance if instance else Source()
        source.mnemonic = attrs.get(self.Meta.lookup_field, source.mnemonic)
        source.name = attrs.get('name', source.name)
        source.full_name = attrs.get('full_name', source.full_name)
        source.description = attrs.get('description', source.description)
        source.source_type = attrs.get('source_type', source.source_type)
        source.custom_validation_type = attrs.get('custom_validation_type', source.custom_validation_type)
        source.public_access = attrs.get('public_access', source.public_access or DEFAULT_ACCESS_TYPE)
        source.default_locale = attrs.get('default_locale', source.default_locale or Common.DEFAULT_LOCALE)
        source.website = attrs.get('website', source.website)
        source.supported_locales = attrs.get('supported_locales').split(',') if attrs.get('supported_locales') else source.supported_locales
        source.extras = attrs.get('extras', source.extras)
        source.external_id = attrs.get('external_id', source.external_id)
        return source

    def get_active_concepts(self, obj):
        return Concept.objects.filter(
            is_active=True, retired=False, parent_id=obj.id
        ).count()


class SourceCreateSerializer(SourceCreateOrUpdateSerializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    short_code = serializers.CharField(source='mnemonic', read_only=True)
    name = serializers.CharField(required=True)
    full_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    source_type = serializers.CharField(required=False)
    custom_validation_type = serializers.CharField(required=False)
    public_access = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES)
    default_locale = serializers.CharField(required=False)
    supported_locales = serializers.CharField(required=False)
    website = serializers.CharField(required=False)
    url = serializers.CharField(read_only=True)
    versions_url = serializers.CharField(read_only=True)
    concepts_url = serializers.CharField(read_only=True)
    active_concepts = serializers.SerializerMethodField(method_name='get_active_concepts')
    owner = serializers.CharField(source='parent_resource', read_only=True)
    owner_type = serializers.CharField(source='parent_resource_type', read_only=True)
    owner_url = serializers.CharField(source='parent_url', read_only=True)
    versions = serializers.IntegerField(source='num_versions', read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    created_by = serializers.CharField(source='owner', read_only=True)
    updated_by = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Source.persist_new(obj, request_user, **kwargs)
        self._errors.update(errors)


class SourceDetailSerializer(SourceCreateOrUpdateSerializer):
    type = serializers.CharField(source='resource_type', read_only=True)
    uuid = serializers.CharField(source='id', read_only=True)
    id = serializers.CharField(required=False, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    short_code = serializers.CharField(required=False, source='mnemonic')
    name = serializers.CharField(required=False)
    full_name = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    source_type = serializers.CharField(required=False)
    custom_validation_type = serializers.CharField(required=False)
    public_access = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES)
    default_locale = serializers.CharField(required=False)
    supported_locales = serializers.CharField(required=False)
    website = serializers.CharField(required=False)
    url = serializers.CharField(read_only=True)
    versions_url = serializers.CharField(read_only=True)
    concepts_url = serializers.CharField(read_only=True)
    active_concepts = serializers.SerializerMethodField(method_name='get_active_concepts')
    owner = serializers.CharField(source='parent_resource', read_only=True)
    owner_type = serializers.CharField(source='parent_resource_type', read_only=True)
    owner_url = serializers.CharField(source='parent_url', read_only=True)
    versions = serializers.IntegerField(source='num_versions', read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    created_by = serializers.CharField(source='owner', read_only=True)
    updated_by = serializers.CharField(read_only=True)
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Source.persist_changes(obj, request_user, **kwargs)
        if errors:
            self._errors.update(errors)
        else:
            head_obj = obj.get_head();
            head_obj.update_version_data(obj)
            head_obj.save();



class SourceVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='mnemonic')
    released = serializers.CharField()
    retired = serializers.BooleanField()
    owner = serializers.CharField(source='parent_resource')
    owner_type = serializers.CharField(source='parent_resource_type')
    owner_url = serializers.CharField(source='parent_url')
    created_on = serializers.DateTimeField(source='created_at')
    updated_on = serializers.DateTimeField(source='updated_at')

    class Meta:
        model = SourceVersion
        versioned_object_view_name = 'source-detail'
        versioned_object_field_name = 'url'


class SourceVersionDetailSerializer(ResourceVersionSerializer):
    type = serializers.CharField(required=True, source='resource_type')
    id = serializers.CharField(required=True, source='mnemonic')
    description = serializers.CharField()
    released = serializers.BooleanField()
    retired = serializers.BooleanField()
    owner = serializers.CharField(source='parent_resource')
    owner_type = serializers.CharField(source='parent_resource_type')
    owner_url = serializers.CharField(source='parent_url')
    created_on = serializers.DateTimeField(source='created_at')
    updated_on = serializers.DateTimeField(source='updated_at')
    extras = serializers.WritableField()
    external_id = serializers.CharField(required=False)
    active_mappings = serializers.IntegerField(required=False)
    active_concepts = serializers.IntegerField(required=False)

    class Meta:
        model = SourceVersion
        versioned_object_view_name = 'source-detail'
        versioned_object_field_name = 'sourceUrl'

    def get_default_fields(self):
        default_fields = super(SourceVersionDetailSerializer, self).get_default_fields()
        if self.opts.view_name is None:
            self.opts.view_name = self._get_default_view_name(self.opts.model)
        default_fields.update(
            {
                'parentVersionUrl': HyperlinkedResourceVersionIdentityField(related_attr='parent_version', view_name=self.opts.view_name),
                'previousVersionUrl': HyperlinkedResourceVersionIdentityField(related_attr='previous_version', view_name=self.opts.view_name),
            }
        )
        return default_fields

    def to_native(self, obj):
        ret = super(SourceVersionDetailSerializer, self).to_native(obj)
        if obj._ocl_processing:
            ret['_ocl_processing'] = True
        return ret


class SourceVersionCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = SourceVersion
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        instance.mnemonic = attrs.get(self.Meta.lookup_field, instance.mnemonic)
        instance.description = attrs.get('description', instance.description)
        instance.released = attrs.get('released', instance.released)
        instance.retired = attrs.get('retired', instance.retired)
        instance._previous_version_mnemonic = attrs.get('previous_version_mnemonic', instance.previous_version_mnemonic)
        instance._parent_version_mnemonic = attrs.get('parent_version_mnemonic', instance.parent_version_mnemonic)
        instance.extras = attrs.get('extras', instance.extras)
        instance.external_id = attrs.get('external_id', instance.external_id)
        return instance

    def save_object(self, obj, **kwargs):
        errors = SourceVersion.persist_changes(obj, **kwargs)
        self._errors.update(errors)


class SourceVersionUpdateSerializer(SourceVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=False, source='mnemonic')
    released = serializers.BooleanField(required=False)
    retired = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previous_version = serializers.CharField(required=False, source='previous_version_mnemonic')
    parent_version = serializers.CharField(required=False, source='parent_version_mnemonic')
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)


class SourceVersionCreateSerializer(SourceVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previous_version = serializers.CharField(required=False, source='previous_version_mnemonic')
    parent_version = serializers.CharField(required=False, source='parent_version_mnemonic')
    extras = serializers.WritableField(required=False)
    external_id = serializers.CharField(required=False)

    def restore_object(self, attrs, instance=None):
        version = SourceVersion()
        version.mnemonic = attrs.get(self.Meta.lookup_field)
        return super(SourceVersionCreateSerializer, self).restore_object(attrs, instance=version)

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = SourceVersion.persist_new(obj, user=request_user, **kwargs)
        if errors:
            self._errors.update(errors)
        else:
            update_children_for_resource_version.delay(obj.id, 'source')
