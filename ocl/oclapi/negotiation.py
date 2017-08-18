from rest_framework.negotiation import DefaultContentNegotiation

__author__ = 'misternando'


class OptionallyCompressContentNegotiation(DefaultContentNegotiation):
    def select_renderer(self, request, renderers, format_suffix=None):
        meta = request._request.META
        compress = meta.get('HTTP_COMPRESS')
        if compress:
            renderers = self.filter_renderers(renderers, 'zip')
            if renderers:
                return renderers[0], 'application/zip'
        return super(OptionallyCompressContentNegotiation, self).select_renderer(request, renderers, format_suffix)