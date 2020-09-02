from django.contrib import admin
from django.conf.urls import url
from django.contrib.admin.views.decorators import staff_member_required
from .views import *


urlpatterns = [
    url('duplicate/', EolDuplicateXblock.as_view(), name='duplicate'),
]
