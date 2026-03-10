"""
teams/admin.py
Registers BoardMembership in the Django admin.
"""
from django.contrib import admin
from .models import BoardMembership


@admin.register(BoardMembership)
class BoardMembershipAdmin(admin.ModelAdmin):
    list_display  = ('user', 'board', 'specialty_role', 'joined_at')
    list_filter   = ('specialty_role', 'board')
    search_fields = ('user__username', 'board__title')
    readonly_fields = ('joined_at',)
