from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import Group

ADMIN_GROUP_NAME = "Administrador"
ATTENDANT_GROUP_NAME = "Atendente TI"
PRIMARY_ADMIN_USERNAME = "fabiano.polone"


@dataclass(frozen=True)
class PermissionGroups:
    admin: Group
    attendant: Group


def ensure_permission_groups() -> PermissionGroups:
    admin_group, _ = Group.objects.get_or_create(name=ADMIN_GROUP_NAME)
    attendant_group, _ = Group.objects.get_or_create(name=ATTENDANT_GROUP_NAME)
    return PermissionGroups(admin=admin_group, attendant=attendant_group)


def ensure_user_permission_defaults(user):
    groups = ensure_permission_groups()

    if user.username.lower() == PRIMARY_ADMIN_USERNAME.lower():
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save(update_fields=["is_staff", "is_superuser", "is_active"])
        user.groups.add(groups.admin)

    return groups


def is_admin_user(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False

    if getattr(user, "is_superuser", False):
        return True

    return user.groups.filter(name=ADMIN_GROUP_NAME).exists()


def is_attendant_user(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return user.groups.filter(name=ATTENDANT_GROUP_NAME).exists()
