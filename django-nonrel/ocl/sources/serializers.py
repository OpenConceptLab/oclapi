from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.fields import HyperlinkedResourceVersionIdentityField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import HyperlinkedResourceSerializer, HyperlinkedSubResourceSerializer, ResourceVersionSerializer
from settings import DEFAULT_LOCALE
from sources.models import Source, SourceVersion, SRC_TYPE_CHOICES, ACCESS_TYPE_CHOICES, DEFAULT_ACCESS_TYPE, DEFAULT_SRC_TYPE


class SourceListSerializer(HyperlinkedResourceSerializer):
    shortCode = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)

    class Meta:
        model = Source
        fields = ('shortCode', 'name', 'url')


class SourceDetailSerializer(HyperlinkedSubResourceSerializer):
    type = serializers.CharField(required=True, source='resource_type')
    uuid = serializers.CharField(required=True, source='id')
    id = serializers.CharField(required=True, source='mnemonic')
    shortCode = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)
    fullName = serializers.CharField(source='full_name')
    sourceType = serializers.CharField(required=True, source='source_type')
    publicAccess = serializers.CharField(source='public_access')
    defaultLocale = serializers.CharField(source='default_locale')
    supportedLocales = serializers.CharField(source='supported_locales')
    website = serializers.CharField()
    description = serializers.CharField()
    owner = serializers.CharField(source='parent_resource')
    ownerType = serializers.CharField(source='parent_resource_type')
    versions = serializers.IntegerField(source='num_versions')
    createdOn = serializers.DateTimeField(source='created_at')
    updatedOn = serializers.DateTimeField(source='updated_at')

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
        source.source_type = attrs.get('source_type', source.source_type or DEFAULT_SRC_TYPE)
        source.public_access = attrs.get('public_access', source.public_access or DEFAULT_ACCESS_TYPE)
        source.default_locale=attrs.get('default_locale', source.default_locale or DEFAULT_LOCALE)
        source.website = attrs.get('website', source.website)
        source.supported_locales = attrs.get('supported_locales').split(',') if attrs.get('supported_locales') else source.supported_locales
        return source


class SourceCreateSerializer(SourceCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    name = serializers.CharField(required=True)
    fullName = serializers.CharField(required=False, source='full_name')
    description = serializers.CharField(required=False)
    sourceType = serializers.ChoiceField(required=False, choices=SRC_TYPE_CHOICES, source='source_type')
    publicAccess = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES, source='public_access')
    defaultLocale = serializers.CharField(required=False, source='default_locale')
    supportedLocales = serializers.CharField(required=False, source='supported_locales')
    website = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        errors = Source.persist_new(obj, **kwargs)
        self._errors.update(errors)


class SourceUpdateSerializer(SourceCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    name = serializers.CharField(required=True)
    fullName = serializers.CharField(required=False, source='full_name')
    description = serializers.CharField(required=False)
    sourceType = serializers.ChoiceField(required=False, choices=SRC_TYPE_CHOICES, source='source_type')
    publicAccess = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES, source='public_access')
    defaultLocale = serializers.CharField(required=False, source='default_locale')
    supportedLocales = serializers.CharField(required=False, source='supported_locales')
    website = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        errors = Source.persist_changes(obj, **kwargs)
        self._errors.update(errors)


class SourceVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='mnemonic')
    released = serializers.CharField()

    class Meta:
        model = SourceVersion
        versioned_object_view_name = 'source-detail'
        versioned_object_field_name = 'url'
        fields = ('id', 'released', 'url', 'versionUrl')


class SourceVersionDetailSerializer(ResourceVersionSerializer):
    type = serializers.CharField(required=True, source='resource_type')
    id = serializers.CharField(required=True, source='mnemonic')
    description = serializers.CharField()
    released = serializers.BooleanField()
    createdOn = serializers.DateTimeField(source='created_at')
    updatedOn = serializers.DateTimeField(source='updated_at')

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


class SourceVersionCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = SourceVersion
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        was_released = instance.released
        instance.released = attrs.get('released', instance.released)
        if was_released and not instance.released:
            self._errors['released'] = ['Cannot set this field to "false".  (Releasing another version will cause this field to become false.)']
        instance.description = attrs.get('description', instance.description)
        instance._previous_version_mnemonic = attrs.get('previous_version_mnemonic', instance.previous_version_mnemonic)
        instance._parent_version_mnemonic = attrs.get('parent_version_mnemonic', instance.parent_version_mnemonic)
        return instance

    def save_object(self, obj, **kwargs):
        errors = SourceVersion.persist_changes(obj, **kwargs)
        self._errors.update(errors)


class SourceVersionUpdateSerializer(SourceVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=False, source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previousVersion = serializers.CharField(required=False, source='previous_version_mnemonic')
    parentVersion = serializers.CharField(required=False, source='parent_version_mnemonic')


class SourceVersionCreateSerializer(SourceVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previousVersion = serializers.CharField(required=False, source='previous_version_mnemonic')
    parentVersion = serializers.CharField(required=False, source='parent_version_mnemonic')

    def restore_object(self, attrs, instance=None):
        version = SourceVersion()
        version.mnemonic = attrs.get(self.Meta.lookup_field)
        return super(SourceVersionCreateSerializer, self).restore_object(attrs, instance=version)

    def save_object(self, obj, **kwargs):
        errors = SourceVersion.persist_new(obj, **kwargs)
        self._errors.update(errors)
