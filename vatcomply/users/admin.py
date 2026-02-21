from django.contrib import admin
from django.contrib.admin import site
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from vatcomply.users.forms import UserChangeAdminForm, UserCreationAdminForm
from vatcomply.users.models import User


@admin.register(User, site=site)
class UserAdmin(BaseUserAdmin):
    form = UserChangeAdminForm
    add_form = UserCreationAdminForm

    list_display = ["email", "is_active", "is_staff", "is_superuser", "last_login"]
    list_filter = ["is_staff", "is_superuser", "is_active", "last_login"]
    filter_horizontal = ["groups", "user_permissions"]
    search_fields = ["email"]
    fieldsets = [
        (None, {"fields": ["email", "password", "last_login"]}),
        ("Permissions", {"fields": ["is_active", "is_staff", "is_superuser"]}),
    ]
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["email", "password1", "password2"],
            },
        ),
    ]
    ordering = ["email"]
    readonly_fields = ["last_login"]
