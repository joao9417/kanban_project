"""
boards/admin.py
Registers Board, Column, Card, and BoardAnalytics with the Django admin.
"""
from django.contrib import admin
from .models import Board, Column, Card, BoardAnalytics


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display  = ('title', 'owner', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('title', 'owner__username')


@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display  = ('title', 'board', 'order')
    list_filter   = ('board',)


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display  = ('title', 'column', 'status', 'discipline', 'assignee', 'progress')
    list_filter   = ('status', 'discipline')
    search_fields = ('title', 'assignee__username')


@admin.register(BoardAnalytics)
class BoardAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('board', 'total_cards', 'completed_cards', 'avg_progress', 'finished_at')
    readonly_fields = ('finished_at',)
