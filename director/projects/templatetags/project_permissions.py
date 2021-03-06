import typing

from django import template

from projects.permission_models import ProjectPermissionType

register = template.Library()


@register.filter
def project_permissions_contain(permissions: typing.Set[ProjectPermissionType], permission_type_name: str) -> bool:
    return ProjectPermissionType(permission_type_name) in permissions
