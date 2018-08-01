import os
import re
import six

# PyCharm remote debugging requires importer.install call
try:
    if os.environ.get('JETBRAINS_REMOTE_RUN'):
        from configurations import importer
        importer.install()
except KeyError:
    pass

HAYSTACK_IDENTIFIER_REGEX = re.compile('^[\w\d_]+\.[\w\d_]+\.[\w\d_]+$')

def get_identifier(obj_or_string):
    """
    Overridden to fix the regex check as Mongo identifiers are not only digits.
    """
    if isinstance(obj_or_string, six.string_types):
        if not HAYSTACK_IDENTIFIER_REGEX.match(obj_or_string):
            raise AttributeError(u"Provided string '%s' is not a valid identifier." % obj_or_string)

        return obj_or_string

    return u"%s.%s.%s" % (
        obj_or_string._meta.app_label,
        obj_or_string._meta.module_name,
        obj_or_string._get_pk_val()
    )

