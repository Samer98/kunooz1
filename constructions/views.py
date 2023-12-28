from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from .models import Project, ProjectMembers
from members.models import User
from .serializers import ProjectSerializers, ProjectMembersSerializers
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from django.utils.translation import gettext as _
from kunooz.permissions import IsConsultant


# Create your views here.


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializers
    permission_classes = [IsConsultant]

    def list(self, request, *args, **kwargs):
        user = self.request.user
        projects = Project.objects.filter(project_owner=user)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user = self.request.user
        projects = Project.objects.filter(project_owner=user)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        user = self.request.user
        print(user)
        projects_count = Project.objects.filter(project_owner=user).count()
        if projects_count >= user.projects_limits:
            return Response(_("The user reached the limit of projects"), status=status.HTTP_406_NOT_ACCEPTABLE)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(project_owner=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        user = request.user

        if project.project_owner != user:
            return Response(_("You are not the owner of this project"), status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        project = self.get_object()
        user = request.user

        if project.project_owner != user:
            return Response(_("You are not the owner of this project"), status=status.HTTP_403_FORBIDDEN)

        project.delete()
        return Response(_("Project deleted successfully"), status=status.HTTP_204_NO_CONTENT)


class ProjectMembersViewSet(CreateModelMixin, RetrieveModelMixin,DestroyModelMixin, GenericViewSet):
    queryset = ProjectMembers.objects.all()
    serializer_class = ProjectMembersSerializers
    permission_classes = [IsConsultant]

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        project_id = self.kwargs.get('pk')  # Get project_name from URL
        print(project_id)
        # Getting the Project object using the provided project_name
        project = get_object_or_404(Project, id=project_id)
        print(project)
        if project.project_owner != user:
            return Response(_("You are not the owner of this project"), status=status.HTTP_403_FORBIDDEN)

        # Filtering ProjectMembers by the Project's ID
        project_members = ProjectMembers.objects.filter(project_id=project_id)
        users = []
        for member in project_members:
            user_data = {
                "id": member.member.id,
                "first_name": member.member.first_name,
                "phone_number": str(member.member.phone_number)
            }
            users.append(user_data)
        return Response(users, status=status.HTTP_200_OK)


    def create(self, request, *args, **kwargs):
        phone_number = self.request.data.get('phone_number')
        project_id = self.request.data.get('project')

        # Fetch the project
        project = get_object_or_404(Project, id=project_id)

        # Retrieve the user based on the phone number
        user = get_object_or_404(User, phone_number=phone_number)

        # Check if the requesting user is trying to add themselves
        if request.user == user:
            return Response("Can't add yourself", status=status.HTTP_400_BAD_REQUEST)

        # Check if the user exists in the system
        if not user:
            return Response("User does not exist in the system", status=status.HTTP_400_BAD_REQUEST)

        if ProjectMembers.objects.filter(project=project, member=user).exists():
            return Response("the user already exist", status=status.HTTP_400_BAD_REQUEST)

        # Check if the user has the 'Consultant' role
        # Modify this logic as per your actual user model
        if user.role == "Consultant":
            return Response("Can't add a consultant to your project", status=status.HTTP_400_BAD_REQUEST)

        # Create a new ProjectMembers entry
        project_member = ProjectMembers.objects.create(project=project, member=user,phone_number=phone_number)
        serializer = ProjectMembersSerializers(project_member)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        phone_number = self.request.data.get('phone_number')
        project_id = self.request.data.get('project')

        # Fetch the project
        project = get_object_or_404(Project, id=project_id)

        # Check if the requesting user is the owner of the project
        if project.project_owner != request.user:
            return Response("You are not the owner of this project", status=status.HTTP_403_FORBIDDEN)

        # Retrieve the user based on the phone number
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response("User does not exist", status=status.HTTP_400_BAD_REQUEST)

        # Check if the user is a member of the project
        try:
            project_member = ProjectMembers.objects.get(project=project, member=user)
        except ProjectMembers.DoesNotExist:
            return Response("User is not a member of this project", status=status.HTTP_400_BAD_REQUEST)

        # Delete the project member association
        project_member.delete()

        return Response(f"{user.first_name} {user.phone_number} Member removed from the project", status=status.HTTP_200_OK)