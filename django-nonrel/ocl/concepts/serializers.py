from django.core.validators import RegexValidator
from rest_framework import serializers
from concepts.fields import LocalizedTextListField, MappingListField
from concepts.models import Concept, ConceptVersion, LocalizedText
from oclapi.fields import HyperlinkedResourceIdentityField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import ResourceVersionSerializer


class ConceptListSerializer(serializers.Serializer):
    id = serializers.CharField(source='mnemonic')
    external_id = serializers.CharField()
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    url = serializers.URLField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()

    class Meta:
        model = Concept


class ConceptDetailSerializer(serializers.Serializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    external_id = serializers.CharField(required=False)
    concept_class = serializers.CharField(required=False)
    datatype = serializers.CharField(required=False)
    display_name = serializers.CharField(read_only=True)
    display_locale = serializers.CharField(read_only=True)
    names = LocalizedTextListField(required=True)
    descriptions = LocalizedTextListField(required=False, name_override='description')
    retired = serializers.BooleanField(required=False)
    url = serializers.URLField(read_only=True)
    source = serializers.CharField(source='parent_resource', read_only=True)
    owner = serializers.CharField(source='owner_name', read_only=True)
    owner_type = serializers.CharField(read_only=True)
    owner_url = serializers.URLField(read_only=True)
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    extras = serializers.WritableField(required=False)

    class Meta:
        model = Concept
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        concept = instance if instance else Concept()
        concept.mnemonic = attrs.get(self.Meta.lookup_field, concept.mnemonic)
        concept.external_id = attrs.get('external_id', concept.external_id)
        concept.concept_class = attrs.get('concept_class', concept.concept_class)
        concept.datatype = attrs.get('datatype', concept.datatype)
        concept.extras = attrs.get('extras', concept.extras)
        concept.retired = attrs.get('retired', concept.retired)

        # Is this desired behavior??
        concept.names = attrs.get('names', concept.names)

        # Is this desired behavior??
        concept.descriptions = attrs.get('descriptions', concept.descriptions)

        concept.extras = attrs.get('extras', concept.extras)
        return concept

    def save_object(self, obj, **kwargs):
        request_user = self.context['request'].user
        errors = Concept.persist_new(obj, request_user, **kwargs)
        self._errors.update(errors)


class ConceptVersionsSerializer(serializers.Serializer):
    version = serializers.CharField(source='mnemonic')
    previous_version = serializers.CharField(source='previous_version_mnemonic')
    url = serializers.URLField()
    previous_version_url = serializers.URLField()
    version_created_on = serializers.DateTimeField(source='created_at')
    version_created_by = serializers.CharField()
    is_latest_concept_version = serializers.BooleanField(source='is_latest_version')
    is_root_concept_version = serializers.BooleanField(source='is_root_version')
    update_comment = serializers.CharField()


class ConceptVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='name')
    external_id = serializers.CharField()
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()
    version = serializers.CharField(source='mnemonic')
    mappings = MappingListField(read_only=True)

    class Meta:
        model = ConceptVersion
        versioned_object_field_name = 'url'
        versioned_object_view_name = 'concept-detail'

    def __init__(self, *args, **kwargs):
        context = kwargs.get('context', {})
        include_direct_mappings = context.get('include_direct_mappings', False)
        include_indirect_mappings = context.get('include_indirect_mappings', False)
        super(ConceptVersionListSerializer, self).__init__(*args, **kwargs)
        mappings_field = self.fields.get('mappings')
        if include_indirect_mappings:
            mappings_field.source = 'get_bidirectional_mappings'
        elif include_direct_mappings:
            mappings_field.source = 'get_unidirectional_mappings'
        else:
            mappings_field.source = 'get_empty_mappings'


class ConceptVersionDetailSerializer(ResourceVersionSerializer):
    type = serializers.CharField(source='versioned_resource_type')
    uuid = serializers.CharField(source='id')
    id = serializers.CharField(source='name')
    external_id = serializers.CharField()
    concept_class = serializers.CharField()
    datatype = serializers.CharField()
    display_name = serializers.CharField()
    display_locale = serializers.CharField()
    names = LocalizedTextListField()
    descriptions = LocalizedTextListField(name_override='description')
    extras = serializers.WritableField()
    retired = serializers.BooleanField()
    source = serializers.CharField(source='parent_resource')
    source_url = serializers.URLField(source='parent_url')
    owner = serializers.CharField(source='owner_name')
    owner_type = serializers.CharField()
    owner_url = serializers.URLField()
    version = serializers.CharField(source='mnemonic')
    created_on = serializers.DateTimeField(source='created_at', read_only=True)
    updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
    version_created_on = serializers.DateTimeField(source='created_at')
    version_created_by = serializers.CharField()
    extras = serializers.WritableField()
    mappings = MappingListField(read_only=True)

    class Meta:
        model = ConceptVersion
        versioned_object_field_name = 'url'
        versioned_object_view_name = 'concept-detail'

    def __init__(self, *args, **kwargs):
        context = kwargs.get('context', {})
        include_direct_mappings = context.get('include_direct_mappings', False)
        include_indirect_mappings = context.get('include_indirect_mappings', False)
        super(ConceptVersionDetailSerializer, self).__init__(*args, **kwargs)
        mappings_field = self.fields.get('mappings')
        if include_indirect_mappings:
            mappings_field.source = 'get_bidirectional_mappings'
        elif include_direct_mappings:
            mappings_field.source = 'get_unidirectional_mappings'
        else:
            mappings_field.source = 'get_empty_mappings'


# class ReferencesToVersionsSerializer(ConceptVersionListSerializer):
#
#     def to_native(self, obj):
#         field = obj
#         if isinstance(obj, ConceptReference):
#             concept = obj.concept
#             if obj.is_current_version:
#                 field = ConceptVersion.get_latest_version_of(concept)
#             elif obj.source_version:
#                 field = ConceptVersion.objects.get(
#                     versioned_object_id=concept.id, id__in=obj.source_version.concepts)
#             else:
#                 field = obj.concept_version
#         return super(ReferencesToVersionsSerializer, self).to_native(field)


class ConceptVersionUpdateSerializer(serializers.Serializer):
    external_id = serializers.CharField(required=False)
    concept_class = serializers.CharField(required=False)
    datatype = serializers.CharField(required=False)
    names = LocalizedTextListField(required=False)
    descriptions = LocalizedTextListField(required=False, name_override='description')
    retired = serializers.BooleanField(required=False)
    extras = serializers.WritableField(required=False)
    update_comment = serializers.CharField(required=False)

    class Meta:
        model = ConceptVersion

    def restore_object(self, attrs, instance=None):
        instance.concept_class = attrs.get('concept_class', instance.concept_class)
        instance.datatype = attrs.get('datatype', instance.datatype)
        instance.extras = attrs.get('extras', instance.extras)
        instance.external_id = attrs.get('external_id', instance.external_id)
        instance.update_comment = attrs.get('update_comment')

        # Is this desired behavior??
        instance.names = attrs.get('names', instance.names)

        # Is this desired behavior??
        instance.descriptions = attrs.get('descriptions', instance.descriptions)

        instance.retired = attrs.get('retired', instance.retired)
        return instance

    def save_object(self, obj, **kwargs):
        user = self.context['request'].user
        errors = ConceptVersion.persist_clone(obj, user, **kwargs)
        self._errors.update(errors)


class ConceptNameSerializer(serializers.Serializer):
    uuid = serializers.CharField(read_only=True)
    external_id = serializers.CharField(required=False)
    name = serializers.CharField(required=True)
    locale = serializers.CharField(required=True)
    locale_preferred = serializers.BooleanField(required=False, default=False)
    name_type = serializers.CharField(required=False, source='type')

    def to_native(self, obj):
        ret = super(ConceptNameSerializer, self).to_native(obj)
        ret.update({"type": "ConceptName"})
        return ret

    def restore_object(self, attrs, instance=None):
        concept_name = instance if instance else LocalizedText()
        concept_name.name = attrs.get('name', concept_name.name)
        concept_name.locale = attrs.get('locale', concept_name.locale)
        concept_name.locale_preferred = attrs.get('locale_preferred', concept_name.locale_preferred)
        concept_name.type = attrs.get('type', concept_name.type)
        concept_name.external_id = attrs.get('external_id', concept_name.external_id)
        return concept_name


class ConceptDescriptionSerializer(serializers.Serializer):
    uuid = serializers.CharField(read_only=True)
    external_id = serializers.CharField(required=False)
    description = serializers.CharField(required=True, source='name')
    locale = serializers.CharField(required=True)
    locale_preferred = serializers.BooleanField(required=False, default=False)
    description_type = serializers.CharField(required=False, source='type')

    def to_native(self, obj):
        ret = super(ConceptDescriptionSerializer, self).to_native(obj)
        ret.update({"type": "ConceptDescription"})
        return ret

    def restore_object(self, attrs, instance=None):
        concept_desc = instance if instance else LocalizedText()
        concept_desc.name = attrs.get('name', concept_desc.name)
        concept_desc.locale = attrs.get('locale', concept_desc.locale)
        concept_desc.locale_preferred = attrs.get(
            'locale_preferred', concept_desc.locale_preferred)
        concept_desc.type = attrs.get('type', concept_desc.type)
        concept_desc.external_id = attrs.get('external_id', concept_desc.external_id)
        return concept_desc


# class ConceptReferenceCreateSerializer(serializers.Serializer):
#     concept_reference_url = ConceptReferenceField(
#         source='concept', required=True, view_name='conceptversion-detail',
#         lookup_kwarg='concept_version', queryset=ConceptVersion.objects.all())
#     id = serializers.CharField(source='mnemonic', required=False)
#     extras = serializers.WritableField(required=False)
#
#     class Meta:
#         model = ConceptReference
#         lookup_field = 'mnemonic'
#
#     def restore_object(self, attrs, instance=None):
#         concept_reference = instance if instance else ConceptReference()
#         concept_reference.extras = attrs.get('extras', concept_reference.extras)
#         concept = attrs.get('concept', None)
#         if concept:
#             concept_reference.concept = concept
#             if hasattr(concept, '_concept_version'):
#                 concept_reference.concept_version = concept._concept_version
#             elif hasattr(concept, '_source_version'):
#                 concept_reference.source_version = concept._source_version
#         concept_reference.mnemonic = attrs.get(self.Meta.lookup_field, concept_reference.mnemonic)
#         if not concept_reference.mnemonic:
#             concept_reference.mnemonic = "%s..%s" % (concept_reference.concept.parent,
#                                                      concept_reference.concept)
#         return concept_reference
#
#     def save_object(self, obj, **kwargs):
#         errors = ConceptReference.persist_new(obj, **kwargs)
#         self._errors.update(errors)
#
#
# class ConceptReferenceDetailSerializer(serializers.Serializer):
#     concept_reference_id = serializers.CharField(source='mnemonic')
#     concept_reference_url = serializers.URLField(read_only=True)
#     url = HyperlinkedResourceIdentityField(view_name='collection-concept-detail')
#     collection = serializers.CharField(source='collection')
#     collection_owner = serializers.CharField(read_only=True, source='owner_name')
#     collection_owner_type = serializers.CharField(read_only=True, source='owner_type')
#     created_on = serializers.DateTimeField(source='created_at', read_only=True)
#     updated_on = serializers.DateTimeField(source='updated_at', read_only=True)
#
#     class Meta:
#         model = ConceptReference
#         lookup_field = 'mnemonic'
