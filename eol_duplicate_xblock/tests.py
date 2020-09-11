# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from openedx.core.lib.tests.tools import assert_true
from mock import patch, Mock


from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from util.testing import UrlResetMixin
from xmodule.modulestore import ModuleStoreEnum
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from xmodule.modulestore.django import modulestore
from xmodule.modulestore.tests.factories import CourseFactory, ItemFactory
from student.roles import CourseInstructorRole, CourseStaffRole
from student.tests.factories import UserFactory, CourseEnrollmentFactory
from capa.tests.response_xml_factory import StringResponseXMLFactory
from lms.djangoapps.courseware.tests.factories import StudentModuleFactory
from opaque_keys.edx.keys import CourseKey
from courseware.courses import get_course_with_access
from six import text_type
from six.moves import range
import json
import views
import time

USER_COUNT= 11

class TestEolDuplicateXblockView(UrlResetMixin, ModuleStoreTestCase):
    def setUp(self):
        super(TestEolDuplicateXblockView, self).setUp()
        # create a course
        self.course = CourseFactory.create(
            org='mss', course='999', display_name='eol_test_course')
        
        self.course2 = CourseFactory.create(
            org='mss', course='222', display_name='eol_test2_course')

        # Now give it some content
        with self.store.bulk_operations(self.course.id, emit_signals=False):
            self.chapter = ItemFactory.create(
                parent_location=self.course.location,
                category="chapter",
            )
            self.section = ItemFactory.create(
                parent_location=self.chapter.location,
                category="sequential",
            )
            self.subsection = ItemFactory.create(
                parent_location=self.section.location,
                category="vertical",
            )
            self.items = [
                ItemFactory.create(
                    parent_location=self.subsection.location,
                    category="problem"
                )
                for __ in range(USER_COUNT - 1)
            ]
        with self.store.bulk_operations(self.course2.id, emit_signals=False):
            self.chapter2 = ItemFactory.create(
                parent_location=self.course2.location,
                category="chapter",
            )
            self.section2 = ItemFactory.create(
                parent_location=self.chapter2.location,
                category="sequential",
            )
            self.subsection2 = ItemFactory.create(
                parent_location=self.section2.location,
                category="vertical",
            )
            self.item2 = ItemFactory.create(
                parent_location=self.subsection2.location,
                category="problem"
            )

        # Patch the comment client user save method so it does not try
        # to create a new cc user when creating a django user
        with patch('student.models.cc.User.save'):
            # Create the student
            self.student = UserFactory(
                username='student',
                password='test',
                email='student@edx.org')
            # Enroll the student in the course
            CourseEnrollmentFactory(
                user=self.student, course_id=self.course.id)

            # Create and Enroll staff user
            self.staff_user = UserFactory(
                username='staff_user',
                password='test',
                email='staff@edx.org')
            CourseEnrollmentFactory(
                user=self.staff_user,
                course_id=self.course.id)
            CourseStaffRole(self.course.id).add_users(self.staff_user)
            CourseEnrollmentFactory(
                user=self.staff_user,
                course_id=self.course2.id)
            role = CourseInstructorRole(self.course.id)
            role.add_users(self.staff_user)
            role2 = CourseInstructorRole(self.course2.id)
            role2.add_users(self.staff_user)
            # Log the student in
            self.client = Client()
            assert_true(self.client.login(username='student', password='test'))

            # Log the user staff in
            self.staff_client = Client()
            assert_true(
                self.staff_client.login(
                    username='staff_user',
                    password='test'))

    def test_duplicate_xblock_get(self):
        """
            Test duplicate xblock GET normal process
        """
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.get(url)
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_get_user_anonymous(self):
        """
            Test duplicate xblock GET when user is anonymous
        """
        client = Client()
        url = reverse('duplicate-xblock:duplicate')
        response = client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_duplicate_xblock_post(self):
        """
            Test duplicate xblock POST normal process
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.subsection.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        view = views.EolDuplicateXblock()
        new_id = view.usage_key_with_run(str(self.item2.location))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('id="saved_duplicate"' in response._container[0].decode('utf-8'))
        self.assertTrue(str(new_id.replace(course_key=self.course.id)) in response._container[0].decode('utf-8'))
        store = modulestore()
        self.assertTrue(store.has_item(new_id.replace(course_key=self.course.id)))
    
    def test_duplicate_xblock_post_user_anonymous(self):
        """
            Test duplicate xblock POST when user is anonymous
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.subsection.location)
        }
        client = Client()
        url = reverse('duplicate-xblock:duplicate')
        response = client.post(url, post_data)
        self.assertEqual(response.status_code, 404)
    
    def test_duplicate_xblock_post_no_params(self):
        """
            Test duplicate xblock POST no params
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': '',
            'dest_usage_key': ''
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="no_block_id"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_invalid_o_block_id(self):
        """
            Test duplicate xblock POST when origin block id is invalid
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': 'asdfgh',
            'dest_usage_key': str(self.subsection.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="o_block_id_invalid"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_invalid_d_block_id(self):
        """
            Test duplicate xblock POST when destination block id is invalid
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.subsection.location),
            'dest_usage_key': 'asdfghjkl'
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="d_block_id_invalid"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_same_block_id(self):
        """
            Test duplicate xblock POST when origin and destination block id are equals
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.item2.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="level_error"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_wrong_level_xblock(self):
        """
            Test duplicate xblock POST when block_type are inverted
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.subsection2.location),
            'dest_usage_key': str(self.item2.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="level_error"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_wrong_level_xblock_2(self):
        """
            Test duplicate xblock POST when the difference of block_type are very different
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.course.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="level_diff_error"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_o_block_no_exists(self):
        """
            Test duplicate xblock POST origin block_id no exists
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': 'block-v1:eol+test202+2020+type@html+block@824be1f5b5cf4ca0865778adda5bf143',
            'dest_usage_key': str(self.course.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        self.assertTrue('id="o_block_id_no_exists"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_d_block_no_exists(self):
        """
            Test duplicate xblock POST destination block_id no exists
        """
        post_data = {
            'action': 'html',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.subsection.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.client.post(url, post_data)
        self.assertTrue('id="block_permission"' in response._container[0].decode('utf-8'))
        self.assertEqual(response.status_code, 200)
    
    def test_duplicate_xblock_post_no_action(self):
        """
            Test duplicate xblock POST no action param
        """
        post_data = {
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.subsection.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 400)
    
    def test_duplicate_xblock_post_wrong_action(self):
        """
            Test duplicate xblock POST no action param
        """
        post_data = {
            'action': 'asd',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.subsection.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 400)

    def test_duplicate_xblock_post_json(self):
        """
            Test duplicate xblock POST JSON normal process
        """
        post_data = {
            'action': 'json',
            'origin_usage_key': str(self.item2.location),
            'dest_usage_key': str(self.subsection.location)
        }
        url = reverse('duplicate-xblock:duplicate')
        response = self.staff_client.post(url, post_data)
        view = views.EolDuplicateXblock()
        new_id = view.usage_key_with_run(str(self.item2.location))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response._container[0])
        self.assertEqual(data['saved'], 'saved')
        self.assertEqual(data['location'], str(new_id.replace(course_key=self.course.id)))
        store = modulestore()
        self.assertTrue(store.has_item(new_id.replace(course_key=self.course.id)))