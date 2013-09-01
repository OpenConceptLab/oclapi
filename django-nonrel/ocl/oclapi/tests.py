import json
from datetime import tzinfo, timedelta, datetime
from encoders import JsonUTCDateEncoder
from django.test import TestCase


# 5 hours behind UTC, i.e. EST
class TZ(tzinfo):
    def utcoffset(self, date_time):
        return timedelta(hours=-5)


class JSONDateEncoderTest(TestCase):
    JSON_NULL = 'null'

    def test_none(self):
        result = json.dumps(None, cls=JsonUTCDateEncoder)
        self.assertEqual(result, self.JSON_NULL, "'None' should serialize to '%s'" % self.JSON_NULL)

    def test_date_string(self):
        now = datetime.now().isoformat()
        result = json.dumps(now, cls=JsonUTCDateEncoder)
        self.assertEqual(result, '"%s"' % now, 'Date string should serialize as self')

    def test_datetime(self):
        dt = datetime(2013, 9, 1, 12, 1, 33, tzinfo=TZ())
        result = json.dumps(dt, cls=JsonUTCDateEncoder)
        self.assertEqual(result, '"2013-09-01T17:01:33Z"', 'UTC offset should be subtracted')

    def test_datetime_no_tzinfo(self):
        dt = datetime(2013, 9, 1, 12, 1, 33)
        result = json.dumps(dt, cls=JsonUTCDateEncoder)
        self.assertEqual(result, '"2013-09-01T12:01:33Z"', 'Datetime with not UTC offset is assumed to be UTC')

