"""
boards/urls.py
URL patterns for board, column, and card CRUD views.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Board CRUD
    path('', views.BoardListView.as_view(), name='board_list'),
    path('board/new/', views.BoardCreateView.as_view(), name='board_create'),
    path('board/<int:pk>/', views.BoardDetailView.as_view(), name='board_detail'),
    path('board/<int:pk>/update/', views.BoardUpdateView.as_view(), name='board_update'),
    path('board/<int:pk>/delete/', views.BoardDeleteView.as_view(), name='board_delete'),

    # Analytics (accessible once finished)
    path('board/<int:pk>/analytics/', views.BoardAnalyticsView.as_view(), name='board_analytics'),

    # Bulk creation of predefined tasks (owner only)
    path('board/<int:pk>/default-tasks/', views.BoardDefaultTasksView.as_view(), name='board_default_tasks'),

    # Column CRUD
    path('board/<int:board_id>/column/new/', views.ColumnCreateView.as_view(), name='column_create'),
    path('column/<int:pk>/update/', views.ColumnUpdateView.as_view(), name='column_update'),
    path('column/<int:pk>/delete/', views.ColumnDeleteView.as_view(), name='column_delete'),

    # Card CRUD
    path('column/<int:column_id>/card/new/', views.CardCreateView.as_view(), name='card_create'),
    path('card/<int:pk>/update/', views.CardUpdateView.as_view(), name='card_update'),
    path('card/<int:pk>/delete/', views.CardDeleteView.as_view(), name='card_delete'),
]
