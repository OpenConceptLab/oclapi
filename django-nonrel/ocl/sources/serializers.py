from django.core.validators import RegexValidator
from rest_framework import serializers
from oclapi.models import NAMESPACE_REGEX
from sources.models import Source, SourceVersion, SRC_TYPE_CHOICES, ACCESS_TYPE_CHOICES


class SourceCreateSerializer(serializers.Serializer):
    mnemonic = serializers.CharField(required=True, max_length=100, validators=[RegexValidator(regex=NAMESPACE_REGEX)])
    name = serializers.CharField(required=True, max_length=100)
    full_name = serializers.CharField(required=False, max_length=100)
    description = serializers.CharField(required=False, max_length=255)
    type = serializers.ChoiceField(choices=SRC_TYPE_CHOICES)
    public_access = serializers.ChoiceField(choices=ACCESS_TYPE_CHOICES)
    default_locale = serializers.CharField(required=False, max_length=20)
    supported_locales = serializers.CharField(required=False, max_length=255)
    website = serializers.CharField(required=False, max_length=255)

    class Meta:
        model = Source

    def restore_object(self, attrs, instance=None):
        mnemonic = attrs.get('mnemonic', None)
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
        version = SourceVersion(mnemonic='INITIAL')
        source._version = version
        return source

    def save_object(self, obj, **kwargs):
        user = kwargs.pop('owner')
        obj.owner = user
        owning_entity = user.get_profile()
        belongs_to_org = kwargs.pop('belongs_to_org', None)
        if belongs_to_org:
            obj.belongs_to_organization = belongs_to_org
            owning_entity = belongs_to_org
        version = obj._version
        del obj._version
        try:
            obj.save(**kwargs)
            version.source = obj
            version.save()
            owning_entity.sources.append(obj.mnemonic)
            owning_entity.save()
        except:
            owning_entity.sources.remove(obj.mnemonic)
            try:
                owning_entity.save()
            finally: pass
            try:
                version.delete()
            finally: pass
            try:
                obj.delete()
            finally: pass

