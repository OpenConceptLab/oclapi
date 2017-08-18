import tempfile
import zipfile
from django.core.servers.basehttp import FileWrapper
from rest_framework.renderers import JSONRenderer

__author__ = 'misternando'


class ZippedJSONRenderer(JSONRenderer):
    media_type = 'application/zip'
    format = 'zip'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        ret = super(ZippedJSONRenderer, self).render(data, accepted_media_type, renderer_context)
        temp = tempfile.TemporaryFile()
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        archive.writestr('export.json', ret)
        archive.close()
        wrapper = FileWrapper(temp)
        temp.seek(0)
        return wrapper

