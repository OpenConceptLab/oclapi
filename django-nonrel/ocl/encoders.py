import datetime
import json


class JsonUTCDateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            utctime = o - o.utcoffset() if o.utcoffset() else o
            utctime = utctime.replace(tzinfo=None)
            return "%sZ" % utctime.isoformat()
        return json.JSONEncoder.default(self, o)
