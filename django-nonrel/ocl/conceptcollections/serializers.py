from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from rest_framework import serializers
from conceptcollections.models import Collection, DEFAULT_ACCESS_TYPE, ACCESS_TYPE_CHOICES, CollectionVersion
from oclapi.fields import HyperlinkedResourceVersionIdentityField
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import HyperlinkedResourceSerializer, HyperlinkedSubResourceSerializer, ResourceVersionSerializer
from settings import DEFAULT_LOCALE


class CollectionListSerializer(HyperlinkedResourceSerializer):
    shortCode = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)

    class Meta:
        model = Collection
        fields = ('shortCode', 'name', 'url')


class CollectionDetailSerializer(HyperlinkedSubResourceSerializer):
    type = serializers.CharField(required=True, source='resource_type')
    uuid = serializers.CharField(required=True, source='id')
    id = serializers.CharField(required=True, source='mnemonic')
    shortCode = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)
    fullName = serializers.CharField(source='full_name')
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
        collection.public_access = attrs.get('public_access', collection.public_access or DEFAULT_ACCESS_TYPE)
        collection.default_locale=attrs.get('default_locale', collection.default_locale or DEFAULT_LOCALE)
        collection.website = attrs.get('website', collection.website)
        collection.supported_locales = attrs.get('supported_locales').split(',') if attrs.get('supported_locales') else collection.supported_locales
        return collection


class CollectionCreateSerializer(CollectionCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    name = serializers.CharField(required=True)
    fullName = serializers.CharField(required=False, source='full_name')
    description = serializers.CharField(required=False)
    publicAccess = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES, source='public_access')
    defaultLocale = serializers.CharField(required=False, source='default_locale')
    supportedLocales = serializers.CharField(required=False, source='supported_locales')
    website = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        parent_resource = kwargs.pop('parent_resource')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        if Collection.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic).exists():
            self._errors['mnemonic'] = 'Collection with mnemonic %s already exists for parent resource %s.' % (mnemonic, parent_resource.mnemonic)
            return
        obj.parent = parent_resource
        user = kwargs.pop('owner')
        obj.owner = user
        try:
            obj.save(**kwargs)
        except Exception as e:
            raise e
        version = CollectionVersion.for_collection(obj, 'INITIAL')
        version.released = True
        try:
            version.save()
        except Exception as e:
            try:
                obj.delete()
            finally: pass
            raise e


class CollectionUpdateSerializer(CollectionCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    name = serializers.CharField(required=True)
    fullName = serializers.CharField(required=False, source='full_name')
    description = serializers.CharField(required=False)
    publicAccess = serializers.ChoiceField(required=False, choices=ACCESS_TYPE_CHOICES, source='public_access')
    defaultLocale = serializers.CharField(required=False, source='default_locale')
    supportedLocales = serializers.CharField(required=False, source='supported_locales')
    website = serializers.CharField(required=False)

    def save_object(self, obj, **kwargs):
        parent_resource = kwargs.pop('parent_resource')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        matching_collections = Collection.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic)
        if matching_collections.exists():
            if matching_collections[0] != obj:
                self._errors['mnemonic'] = 'Collection with mnemonic %s already exists for parent resource %s.' % (mnemonic, parent_resource.mnemonic)
                return
        obj.save(**kwargs)


class CollectionVersionListSerializer(ResourceVersionSerializer):
    id = serializers.CharField(source='mnemonic')
    released = serializers.CharField()

    class Meta:
        model = CollectionVersion
        fields = ('id', 'released', 'url')


class CollectionVersionDetailSerializer(ResourceVersionSerializer):
    type = serializers.CharField(required=True, source='resource_type')
    id = serializers.CharField(required=True, source='mnemonic')
    description = serializers.CharField()
    released = serializers.BooleanField()
    createdOn = serializers.DateTimeField(source='created_at')
    updatedOn = serializers.DateTimeField(source='updated_at')

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


class CollectionVersionCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = CollectionVersion
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        was_released = instance.released
        instance.released = attrs.get('released', instance.released)
        if was_released and not instance.released:
            self._errors['released'] = ['Cannot set this field to "false".  (Releasing another version will cause this field to become false.)']
        instance._release_version = instance.released and not was_released
        instance.description = attrs.get('description', instance.description)
        instance._previous_version_mnemonic = attrs.get('previous_version_mnemonic', instance.previous_version_mnemonic)
        instance._parent_version_mnemonic = attrs.get('parent_version_mnemonic', instance.parent_version_mnemonic)
        return instance

    def save_object(self, obj, **kwargs):
        versioned_object = kwargs.pop('versioned_object', None)
        if versioned_object is None:
            self._errors['non_field_errors'] = ['Must specify a versioned object.']
            return
        if obj._previous_version_mnemonic:
            previous_version_queryset = CollectionVersion.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._previous_version_mnemonic)
            if not previous_version_queryset.exists():
                self._errors['previousVersion'] = ["Previous version %s does not exist." % obj._previous_version_mnemonic]
            elif obj.mnemonic == obj._previous_version_mnemonic:
                self._errors['previousVersion'] = ["Previous version cannot be the same as current version."]
            else:
                obj.previous_version = previous_version_queryset[0]
                del(obj._previous_version_mnemonic)
        if obj._parent_version_mnemonic:
            parent_version_queryset = CollectionVersion.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj._parent_version_mnemonic)
            if not parent_version_queryset.exists():
                self._errors['parentVersion'] = ["Parent version %s does not exist." % obj._parent_version_mnemonic]
            elif obj.mnemonic == obj._parent_version_mnemonic:
                self._errors['parentVersion'] = ["Parent version cannot be the same as current version."]
            else:
                obj.parent_version = parent_version_queryset[0]
                del(obj._parent_version_mnemonic)
        if self._errors:
            return
        obj.versioned_object = versioned_object
        error_cause = 'updating version'
        try:
            release_version = obj._release_version
            del(obj._release_version)
            obj.save(**kwargs)
            if release_version:
                error_cause = 'updating released statuses'
                for v in CollectionVersion.objects.filter(versioned_object_id=versioned_object.id, released=True).exclude(mnemonic=obj.mnemonic):
                    v.released = False
                    v.save()
        except:
            self._errors['non_field_errors'] = ["Encountered an error while %s." % error_cause]


class CollectionVersionUpdateSerializer(CollectionVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=False, source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previousVersion = serializers.CharField(required=False, source='previous_version_mnemonic')
    parentVersion = serializers.CharField(required=False, source='parent_version_mnemonic')


class CollectionVersionCreateSerializer(CollectionVersionCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    released = serializers.BooleanField(required=False)
    description = serializers.CharField(required=False)
    previousVersion = serializers.CharField(required=False, source='previous_version_mnemonic')
    parentVersion = serializers.CharField(required=False, source='parent_version_mnemonic')

    def restore_object(self, attrs, instance=None):
        version = CollectionVersion()
        version.mnemonic = attrs.get(self.Meta.lookup_field)
        return super(CollectionVersionCreateSerializer, self).restore_object(attrs, instance=version)

    def save_object(self, obj, **kwargs):
        versioned_object = kwargs.get('versioned_object', None)
        if versioned_object is None:
            self._errors['non_field_errors'] = ['Must specify a versioned object.']
            return
        if CollectionVersion.objects.filter(versioned_object_id=versioned_object.id, mnemonic=obj.mnemonic).exists():
            self._errors['mnemonic'] = ["Version with mnemonic %s already exists for source %s." % (obj.mnemonic, versioned_object.mnemonic)]
            return
        super(CollectionVersionCreateSerializer, self).save_object(obj, **kwargs)
