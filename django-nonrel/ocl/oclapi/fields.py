import warnings
from django.core.urlresolvers import NoReverseMatch
from rest_framework.fields import Field
from rest_framework.reverse import reverse


class HyperlinkedIdentityField(Field):
    """
    Represents the instance, or a property on the instance, using hyperlinking.
    """
    pk_field = 'mnemonic'
    read_only = True

    def __init__(self, *args, **kwargs):
        try:
            self.view_name = kwargs.pop('view_name')
        except KeyError:
            msg = "HyperlinkedIdentityField requires 'view_name' argument"
            raise ValueError(msg)

        self.format = kwargs.pop('format', None)
        lookup_field = kwargs.pop('lookup_field', None)
        self.lookup_field = lookup_field or self.lookup_field

        super(HyperlinkedIdentityField, self).__init__(*args, **kwargs)

    def field_to_native(self, obj, field_name):
        request = self.context.get('request', None)
        format = self.context.get('format', None)
        view_name = self.view_name

        if request is None:
            warnings.warn("Using `HyperlinkedIdentityField` without including the "
                          "request in the serializer context is deprecated. "
                          "Add `context={'request': request}` when instantiating the serializer.",
                          DeprecationWarning, stacklevel=4)

        # By default use whatever format is given for the current context
        # unless the target is a different type to the source.
        #
        # Eg. Consider a HyperlinkedIdentityField pointing from a json
        # representation to an html property of that representation...
        #
        # '/snippets/1/' should link to '/snippets/1/highlight/'
        # ...but...
        # '/snippets/1/.json' should link to '/snippets/1/highlight/.html'
        if format and self.format and self.format != format:
            format = self.format

        # Return the hyperlink, or error if incorrectly configured.
        try:
            return self.get_url(obj, view_name, request, format)
        except NoReverseMatch:
            msg = (
                'Could not resolve URL for hyperlinked relationship using '
                'view name "%s". You may have failed to include the related '
                'model in your API, or incorrectly configured the '
                '`lookup_field` attribute on this field.'
            )
            raise Exception(msg % view_name)

    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        lookup_value = getattr(obj, self.pk_field)
        kwargs = {self.lookup_field: lookup_value}
        return reverse(view_name, kwargs=kwargs, request=request, format=format)


class DynamicHyperlinkedIdentifyField(HyperlinkedIdentityField):

    def get_url(self, obj, view_name, request, fmt):
        kwargs = {
            obj.get_url_kwarg(): obj.mnemonic
        }
        if hasattr(obj, 'parent'):
            parent = obj.parent
            while parent:
                kwargs.update({
                    parent.get_url_kwarg(): parent.mnemonic
                })
                parent = parent.parent if hasattr(parent, 'parent') else None
        return reverse(view_name, kwargs=kwargs, request=request, format=fmt)

