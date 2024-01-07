from django.contrib import admin
from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register('Report', views.ApprovalViewSet,basename="Report")
router.register('ReportComment', views.ApprovalCommentViewSet,basename="ReportComment")

urlpatterns = [
              ] + router.urls
