from django.contrib import admin
from django.contrib.admin import site
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from vatcomply.users.forms import UserChangeForm, UserCreationForm
from vatcomply.users.models import User


@admin.register(User, site=site)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ["email", "is_active", "is_staff", "is_superuser", "last_login"]
    list_filter = ["is_staff", "is_superuser", "is_active", "last_login"]
    filter_horizontal = ["groups", "user_permissions"]
    search_fields = ["email"]
    fieldsets = [
        (None, {"fields": ["email", "password", "last_login"]}),
        ("Personal info", {"fields": ["date_of_birth"]}),
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
    search_fields = ["email"]
    ordering = ["email"]
    readonly_fields = ["last_login"]
