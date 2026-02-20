from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError


class UserCreationAdminForm(UserCreationForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = get_user_model()
        fields = ["email"]

    def clean_email(self):
        return self.cleaned_data["email"].lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        if password2:
            password_validation.validate_password(password2, self.instance)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeAdminForm(UserChangeForm):
    class Meta:
        model = get_user_model()
        fields = ("email", "password", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")

    def clean_email(self):
        return self.cleaned_data["email"].lower()
