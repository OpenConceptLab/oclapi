import re
import logging
from time import time
from django.utils.termcolors import colorize
from rest_framework.authtoken.models import Token

request_logger = logging.getLogger('request_logger')
MAX_BODY_LENGTH = 50000


class RequestLogMiddleware(object):
    """
    Middleware for logging the API requests
    """

    def process_request(self, request):
        request.request_start_time = time()
        remote_addr = request.META.get('REMOTE_ADDR')
        user = self.get_user(request)
        username = user.username
        request_logger.info(colorize("{} {} {} {}".format(
            username, remote_addr, request.method, request.get_full_path()), fg="cyan")
        )
        self.log_body(self.chunked_to_max(request.body))

    def process_response(self, request, response):
        response_time = time() - getattr(request, 'request_start_time', time())
        resp_log = "{} sec {} {} : {}".format(
            response_time, request.method, request.get_full_path(), response.status_code
        )
        if (response.status_code in range(400, 600)):
            request_logger.info(colorize(resp_log, fg="magenta"))
            self.log_resp_body(response, level=logging.ERROR)
        else:
            request_logger.info(colorize(resp_log, fg="cyan"))
            self.log_resp_body(response)
        return response

    def get_user(self, request):
        """ Rest framework user can be identified only from the token """
        header_token = request.META.get('HTTP_AUTHORIZATION', None)
        if header_token is not None:
            try:
                token = re.sub('Token ', '', request.META.get('HTTP_AUTHORIZATION', None))
                token_obj = Token.objects.get(key=token)
                return token_obj.user
            except Token.DoesNotExist:
                pass
        return request.user

    def log_resp_body(self, response, level=logging.DEBUG):
        if (not re.match('^application/json', response.get('Content-Type', ''), re.I)):  # only log content type: 'application/xxx'
            return
        self.log_body('{}, - {}'.format(self.chunked_to_max(response.content), response.status_code), level)

    def log_body(self, msg, level=logging.DEBUG):
        for line in str(msg).split('\n'):
            line = colorize(line, fg="magenta") if (level >= logging.ERROR) else colorize(line, fg="cyan")
            request_logger.log(level, line)

    def chunked_to_max(self, msg):
        if (len(msg) > MAX_BODY_LENGTH):
            return "{0}\n...\n".format(msg[0:MAX_BODY_LENGTH])
        else:
            return msg


class FixMalformedLimitParamMiddleware(object):
    """
    Why this was necessary: https://github.com/OpenConceptLab/ocl_issues/issues/151
    """
    @staticmethod
    def process_request(request):
        to_remove = '?limit=100'
        if request.get_full_path()[-10:] == to_remove and request.method == 'GET':
            query_dict_copy = request.GET.copy()
            for key, value in query_dict_copy.iteritems():
                query_dict_copy[key] = value.replace(to_remove, '')
            if 'limit' not in query_dict_copy:
                query_dict_copy['limit'] = 100
            request.GET = query_dict_copy
