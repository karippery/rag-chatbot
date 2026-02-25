# app/admin.py
from django.contrib import admin
from .models import User




# Register your models here.
class UserAdmin(User):
    list_display = ("email", "full_name", "is_staff")
    search_fields = ("email", "full_name")
    ordering = ("email",)


admin.site.register(User)
