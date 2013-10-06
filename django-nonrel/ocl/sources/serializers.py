from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.fields import DynamicHyperlinkedIdentifyField
from oclapi.models import NAMESPACE_REGEX
from sources.models import Source, SourceVersion, SRC_TYPE_CHOICES, ACCESS_TYPE_CHOICES


class SourceListSerializer(serializers.HyperlinkedModelSerializer):
    shortCode = serializers.CharField(required=True, source='mnemonic')
    name = serializers.CharField(required=True)

    class Meta:
        model = Source
        fields = ('shortCode', 'name', 'url')
        lookup_field = 'mnemonic'

    def get_default_fields(self):
        fields = super(SourceListSerializer, self).get_default_fields()
        fields.update({
            'url': DynamicHyperlinkedIdentifyField(view_name=self.opts.view_name,
                                                   lookup_field=self.Meta.lookup_field,
            )
        })
        return fields


class SourceDetailSerializer(serializers.Serializer):
    type = serializers.CharField(required=True)
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

    class Meta:
        model = Source


class SourceCreateSerializer(serializers.Serializer):
    mnemonic = serializers.CharField(required=True, max_length=100, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    name = serializers.CharField(required=True, max_length=100)
    full_name = serializers.CharField(required=False, max_length=100)
    description = serializers.CharField(required=False, max_length=255)
    source_type = serializers.ChoiceField(choices=SRC_TYPE_CHOICES)
    public_access = serializers.ChoiceField(choices=ACCESS_TYPE_CHOICES)
    default_locale = serializers.CharField(required=False, max_length=20)
    supported_locales = serializers.CharField(required=False, max_length=255)
    website = serializers.CharField(required=False, max_length=255)

    class Meta:
        model = Source
        lookup_field = 'mnemonic'


    def restore_object(self, attrs, instance=None):
        mnemonic = attrs.get(self.Meta.lookup_field, None)
        if Source.objects.filter(mnemonic=mnemonic).exists():
            self._errors['mnemonic'] = 'Source with mnemonic %s already exists.' % mnemonic
            return None
        source = Source(mnemonic=attrs.get('mnemonic'),
                        name=attrs.get('name'),
                        full_name=attrs.get('full_name'),
                        website=attrs.get('website'),
                        description=attrs.get('description'))
        if attrs.get('type'):
            source.type = attrs.get('type')
        if attrs.get('public_access'):
            source.public_access = attrs.get('public_access')
        if attrs.get('default_locale'):
            source.default_locale = attrs.get('default_locale')
        supported_locales = attrs.get('supported_locales').split(',') if attrs.get('supported_locales') else None
        source.supported_locales = supported_locales
        return source

    def save_object(self, obj, **kwargs):
        parent_resource = kwargs.pop('parent_resource')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        if Source.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic).exists():
            self._errors['mnemonic'] = 'Source with mnemonic %s already exists for parent resource %s.' % (mnemonic, parent_resource.mnemonic)
            return
        obj.parent = parent_resource
        user = kwargs.pop('owner')
        obj.owner = user
        try:
            obj.save(**kwargs)
        except Exception as e:
            raise e
        version = SourceVersion.for_source(obj, 'INITIAL')
        try:
            version.save()
        except Exception as e:
            try:
                obj.delete()
            finally: pass
            raise e
