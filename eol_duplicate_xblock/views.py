# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import six
import json
import math
from django.conf import settings
from web_fragments.fragment import Fragment
from openedx.core.djangoapps.plugin_api.views import EdxFragmentView
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError
from django.contrib.auth.models import User
from django.urls import reverse
from lms.djangoapps.courseware.access import has_access, get_user_role
from collections import OrderedDict, defaultdict, deque
from django.http import HttpResponse, Http404, HttpResponseServerError, JsonResponse
from django.views.generic.base import View
from opaque_keys.edx.locator import CourseLocator, BlockUsageLocator
from django.db import IntegrityError, transaction
from django.utils.translation import ugettext_noop
from xmodule.modulestore import EdxJSONEncoder, ModuleStoreEnum
from xmodule.modulestore.django import modulestore
from django.shortcuts import render
from common.djangoapps.student.auth import has_studio_read_access, has_studio_write_access
from xmodule.modulestore.exceptions import ItemNotFoundError
from cms.djangoapps.contentstore.views.item import StudioEditModuleRuntime
from uuid import uuid4
from xblock.fields import Scope
from common.djangoapps.edxmako.shortcuts import render_to_response
from lms.djangoapps.courseware.courses import get_course_by_id, get_course_with_access
import logging
from xmodule.modulestore.draft_and_published import DIRECT_ONLY_CATEGORIES
logger = logging.getLogger(__name__)

def require_post_action():
    """
    Checks for required parameters or renders a 400 error.
    (decorator with arguments)

    `args` is a *list of required POST parameter names.
    `kwargs` is a **dict of required POST parameter names
        to string explanations of the parameter
    """
    def decorator(func):  # pylint: disable=missing-docstring
        def wrapped(*args, **kwargs):  # pylint: disable=missing-docstring
            request = args[1]
            action = request.POST.get("action", "")
            error_response_data = {
                'error': 'Missing required query parameter(s)',
                'parameters': ["action"],
                'info': {"action": action},
            }
            if action in ["json", "html"]:
                return func(*args, **kwargs)
            else:
                return JsonResponse(error_response_data, status=400)

        return wrapped
    return decorator

class EolDuplicateXblock(View):
    def get(self, request):
        if request.user.is_anonymous:
            raise Http404()
        context = {'o_block_id': '', 'd_block_id': ''}
        return render_to_response('eol_duplicate_xblock/staff.html', context)

    @require_post_action()
    def post(self, request):
        if request.user.is_anonymous:
            raise Http404()
        origen_usage_key = request.POST.get("origin_usage_key", "")
        dest_usage_key = request.POST.get("dest_usage_key", "")
        context = {'o_block_id': origen_usage_key, 'd_block_id': dest_usage_key}
        #verify data
        context = self.verificar_datos(request, context)
        action = request.POST.get('action','')
        if len(context) > 2 and action == "html":
            return render_to_response('eol_duplicate_xblock/staff.html', context)
        if len(context) > 2 and action == "json":
            return JsonResponse(context)

        duplicar = self.usage_key_with_run(origen_usage_key)
        destino = self.usage_key_with_run(dest_usage_key)
        dest_usage_key = self._duplicate_item(
                destino,
                duplicar,
                request.user,
            )
        context['saved'] = 'saved'
        context['location'] = six.text_type(dest_usage_key)
        if action == "json":
            return JsonResponse(context)
        return render_to_response('eol_duplicate_xblock/staff.html', context)
    
    def verificar_datos(self, request, context):
        """
            Verify if data id correct and exists
        """
        action = request.POST.get('action','')
        if action == '' or action not in ["json", "html"]:
            context['action_error'] = 'true'
            logger.error("Error action param, origin_block_id:{}, dest_block_id: {}, action: {}, user: {}".format(context['o_block_id'], context['d_block_id'], action, request.user))
            return context
        if context['o_block_id'] == '' or context['d_block_id'] == '':
            context['no_block_id'] = 'true'
            logger.error("No params entered, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            return context

        try:
            duplicar = self.usage_key_with_run(context['o_block_id'])
        except InvalidKeyError:
            logger.error("Origen block id invalid, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['o_block_id_invalid'] = 'true'

        try:
            destino = self.usage_key_with_run(context['d_block_id'])
        except InvalidKeyError:
            logger.error("Destination block id invalid, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['d_block_id_invalid'] = 'true'

        if 'o_block_id_invalid' in context or 'd_block_id_invalid' in context:
            return context

        if self.type_to_int(duplicar.block_type) <= self.type_to_int(destino.block_type):
            logger.error("origin block type cant put in destination block type, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['level_error'] = 'true'
           
        if (self.type_to_int(duplicar.block_type) - self.type_to_int(destino.block_type)) != 1 :
            logger.error("origin block type cant put in destination block type, level difference, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['level_diff_error'] = 'true'

        store = modulestore()
        if not store.has_item(duplicar):
            logger.error("origin block id no exists, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['o_block_id_no_exists'] = 'true'

        if not store.has_item(destino):
            logger.error("destination block id no exists, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['d_block_id_no_exists'] = 'true'

        source_course = duplicar.course_key
        dest_course = destino.course_key
        if not self.user_have_permission(request.user, source_course, dest_course):
            logger.error("user dont have permission in some course, origin_block_id:{}, dest_block_id: {}, user: {}".format(context['o_block_id'], context['d_block_id'], request.user))
            context['block_permission'] = 'true'
        return context

    def user_have_permission(self, user, o_course_key, d_course_key):
        return (self.is_instructor(user, o_course_key) and 
            self.is_instructor(user, d_course_key) and
            has_studio_write_access(user, d_course_key) and
            has_studio_read_access(user, o_course_key))

    def type_to_int(self, block_type):
        block_type_dict = {
            'course':1,
            'chapter':2,
            'sequential':3,
            'vertical':4
        }
        #xblock: 5
        if block_type not in block_type_dict:
            return 5
        return block_type_dict[block_type]

    def is_instructor(self, user, course_key):
        """
            Verify if the user is instructor
        """
        try:
            course = get_course_with_access(user, "load", course_key)
            return bool(has_access(user, 'instructor', course))
        except Exception:
            return False
    
    def usage_key_with_run(self, usage_key_string):
        """
        Converts usage_key_string to a UsageKey, adding a course run if necessary
        """
        usage_key = UsageKey.from_string(usage_key_string)
        usage_key = usage_key.replace(course_key=modulestore().fill_in_run(usage_key.course_key))
        return usage_key
    
    def _duplicate_item(self, parent_usage_key, duplicate_source_usage_key, user, display_name=None, is_child=False):
        """
        Duplicate an existing xblock as a child of the supplied parent_usage_key.
        """
        store = modulestore()
        course_key = parent_usage_key.course_key
        with store.bulk_operations(course_key if course_key else duplicate_source_usage_key.course_key):
            source_item = store.get_item(duplicate_source_usage_key)
            ########################
            # Change the blockID to be unique.
            duplicado_de = True
            if store.has_item(duplicate_source_usage_key.replace(course_key=course_key)):
                dest_usage_key = source_item.location.replace(name=uuid4().hex)
            else:
                dest_usage_key = source_item.location
            if course_key and (str(course_key) != str(dest_usage_key.course_key)):
                duplicado_de = False
                dest_usage_key = BlockUsageLocator(
                    course_key.version_agnostic(),
                    block_type=dest_usage_key.block_type,
                    block_id=dest_usage_key.block_id,
                )
            #########################
            category = dest_usage_key.block_type

            # Update the display name to indicate this is a duplicate (unless display name provided).
            # Can't use own_metadata(), b/c it converts data for JSON serialization -
            # not suitable for setting metadata of the new block
            duplicate_metadata = {}
            for field in source_item.fields.values():
                if field.scope == Scope.settings and field.is_set_on(source_item):
                    duplicate_metadata[field.name] = field.read_from(source_item)

            if is_child:
                display_name = display_name or source_item.display_name or source_item.category

            if display_name is not None:
                duplicate_metadata['display_name'] = display_name
            else:
                if source_item.display_name is None:
                    if duplicado_de:
                        duplicate_metadata['display_name'] = (u"(1) {0}").format(source_item.category)
                    else:
                        duplicate_metadata['display_name'] = (u"{0}").format(source_item.category)
                else:
                    if duplicado_de:
                        if source_item.display_name[0] == '(' and source_item.display_name.find(')') != -1:
                            if source_item.display_name[1: source_item.display_name.find(')')].isnumeric():
                                number_copy = int(source_item.display_name[1: source_item.display_name.find(')')]) + 1
                                index_str = source_item.display_name.find(')') + 1
                                duplicate_metadata['display_name'] = (u"({}) {}").format(number_copy, source_item.display_name[index_str:].strip())
                            else:
                                duplicate_metadata['display_name'] = (u"(1) {0}").format(source_item.display_name)
                        else:
                            duplicate_metadata['display_name'] = (u"(1) {0}").format(source_item.display_name)
                    else:
                        duplicate_metadata['display_name'] = (u"{0}").format(source_item.display_name)

            asides_to_create = []
            for aside in source_item.runtime.get_asides(source_item):
                for field in aside.fields.values():
                    if field.scope in (Scope.settings, Scope.content,) and field.is_set_on(aside):
                        asides_to_create.append(aside)
                        break

            for aside in asides_to_create:
                for field in aside.fields.values():
                    if field.scope not in (Scope.settings, Scope.content,):
                        field.delete_from(aside)
            #xblock.plugin.PluginMissingError: when block to dublicate have xblock dont installed
            dest_module = store.create_item(
                user.id,
                course_key if course_key else dest_usage_key.course_key,
                dest_usage_key.block_type,
                block_id=dest_usage_key.block_id,
                definition_data=source_item.get_explicitly_set_fields_by_scope(Scope.content),
                metadata=duplicate_metadata,
                runtime=source_item.runtime,
                asides=asides_to_create
            )

            if category == 'video':
                try:
                    from eol_vimeo.vimeo_utils import duplicate_video
                    duplicate_video(source_item.edx_video_id, duplicate_source_usage_key.course_key, parent_usage_key.course_key, user)
                except ImportError:
                    logger.info('EolDuplicate - Error to import EolVimeo')

            children_handled = False

            if hasattr(dest_module, 'studio_post_duplicate'):
                # Allow an XBlock to do anything fancy it may need to when duplicated from another block.
                # These blocks may handle their own children or parenting if needed. Let them return booleans to
                # let us know if we need to handle these or not.
                dest_module.xmodule_runtime = StudioEditModuleRuntime(user)
                children_handled = dest_module.studio_post_duplicate(store, source_item)
            
            if 'detached' not in source_item.runtime.load_block_type(category)._class_tags:
                parent = store.get_item(parent_usage_key)
                # If source was already a child of the parent, add duplicate immediately afterward.
                # Otherwise, add child to end.
                if source_item.location in parent.children:
                    source_index = parent.children.index(source_item.location)
                    parent.children.insert(source_index + 1, dest_module.location)
                else:
                    parent.children.append(dest_module.location)
                store.update_item(parent, user.id)

            if dest_module.location.block_type in DIRECT_ONLY_CATEGORIES:
                store.publish(dest_module.location, user.id)
            # Children are not automatically copied over (and not all xblocks have a 'children' attribute).
            # Because DAGs are not fully supported, we need to actually duplicate each child as well.
            if source_item.has_children and not children_handled:
                dest_module.children = dest_module.children or []
                for child in source_item.children:
                    dupe = self._duplicate_item(dest_module.location, child, user=user, is_child=True)
                    if dupe not in dest_module.children:  # _duplicate_item may add the child for us.
                        dest_module.children.append(dupe)
                store.update_item(dest_module, user.id)

            return dest_module.location
