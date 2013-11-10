from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator
from rest_framework import serializers
from concepts.fields import LocalizedTextListField
from concepts.models import Concept, ConceptVersion
from oclapi.models import NAMESPACE_REGEX
from oclapi.serializers import HyperlinkedResourceSerializer, HyperlinkedSubResourceSerializer


class ConceptListSerializer(HyperlinkedResourceSerializer):
    name = serializers.CharField(required=True, source='mnemonic')

    class Meta:
        model = Concept
        fields = ('name', 'url')


class ConceptDetailSerializer(HyperlinkedSubResourceSerializer):
    conceptClass = serializers.CharField(source='concept_class')
    datatype = serializers.CharField()
    displayName = serializers.CharField(source='display_name')
    displayLocale = serializers.CharField(source='display_locale')
    names = LocalizedTextListField()
    descriptions = LocalizedTextListField()

    class Meta:
        model = Concept


class ConceptCreateOrUpdateSerializer(serializers.Serializer):
    class Meta:
        model = Concept
        lookup_field = 'mnemonic'

    def restore_object(self, attrs, instance=None):
        concept = instance if instance else Concept()
        concept.mnemonic = attrs.get(self.Meta.lookup_field, concept.mnemonic)
        concept.concept_class = attrs.get('concept_class', concept.concept_class)
        concept.datatype = attrs.get('datatype', concept.datatype)
        concept.names = attrs.get('names', concept.names)  # Is this desired behavior??
        concept.descriptions = attrs.get('descriptions', concept.descriptions)  # Is this desired behavior??
        return concept


class ConceptCreateSerializer(ConceptCreateOrUpdateSerializer):
    id = serializers.CharField(required=True, validators=[RegexValidator(regex=NAMESPACE_REGEX)], source='mnemonic')
    conceptClass = serializers.CharField(required=True, source='concept_class')
    datatype = serializers.CharField(required=False)
    names = LocalizedTextListField(required=True)
    descriptions = LocalizedTextListField(required=False)

    def save_object(self, obj, **kwargs):
        parent_resource = kwargs.pop('parent_resource')
        mnemonic = obj.mnemonic
        parent_resource_type = ContentType.objects.get_for_model(parent_resource)
        if Concept.objects.filter(parent_type__pk=parent_resource_type.id, parent_id=parent_resource.id, mnemonic=mnemonic).exists():
            self._errors['mnemonic'] = 'Concept with mnemonic %s already exists for parent resource %s.' % (mnemonic, parent_resource.mnemonic)
            return
        obj.parent = parent_resource
        user = kwargs.pop('owner')
        obj.owner = user
        try:
            obj.save(**kwargs)
        except Exception as e:
            raise e
        version = ConceptVersion.for_concept(obj, 'INITIAL')
        version.released = True
        try:
            version.save()
        except Exception as e:
            try:
                obj.delete()
            finally: pass
            raise e


