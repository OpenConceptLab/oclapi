"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
from django.contrib.auth.models import User
from django.test import TestCase


class UserProfileTest(TestCase):
    fixtures = ['user', 'userprofile']

    def test_user_attributes(self):
        user = User.objects.get(pk=2)
        profile = user.get_profile()
        self.assertEqual(profile.get_uuid(), 'ac81fb28f8c44132976fdbdc60d54e6b', 'UUID should be returned correctly')
        self.assertEqual(user.username, 'test', 'Username should be returned correctly.')
        self.assertEqual(profile.get_full_name(), "Joe Test", 'Name should be returned correctly')
        self.assertEqual(profile.company, 'Test Healthcare Clinic', 'Company should be returned correctly')
        self.assertEqual(profile.location, 'Testonia', 'Location should be returned correctly')
        self.assertEqual(user.email, 'joe@test.co', 'Email should be returned correctly')
        self.assertEqual(profile.preferred_locale, 'en', 'Preferred Locale should be returned correctly')
        self.assertEqual(profile.created_at, datetime.strptime('2013-09-02 14:06:13', "%Y-%m-%d %H:%M:%S"), 'Created at should be returned correctly')
        self.assertEqual(profile.updated_at, datetime.strptime('2013-09-02 14:06:13', "%Y-%m-%d %H:%M:%S"), 'Updated at should be returned correctly')
