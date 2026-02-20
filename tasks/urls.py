from django.urls import path
from . import views

urlpatterns = [
    # Board CRUD
    path('', views.BoardListView.as_view(), name='board_list'),
    path('board/new/', views.BoardCreateView.as_view(), name='board_create'),
    path('board/<int:pk>/', views.BoardDetailView.as_view(), name='board_detail'),
    path('board/<int:pk>/update/', views.BoardUpdateView.as_view(), name='board_update'),
    path('board/<int:pk>/delete/', views.BoardDeleteView.as_view(), name='board_delete'),

    # Board team management & project lifecycle
    path('board/<int:pk>/members/', views.BoardMembersView.as_view(), name='board_members'),
    path('board/<int:pk>/finish/', views.BoardFinishView.as_view(), name='board_finish'),
    path('board/<int:pk>/analytics/', views.BoardAnalyticsView.as_view(), name='board_analytics'),

    # Column CRUD
    path('board/<int:board_id>/column/new/', views.ColumnCreateView.as_view(), name='column_create'),
    path('column/<int:pk>/update/', views.ColumnUpdateView.as_view(), name='column_update'),
    path('column/<int:pk>/delete/', views.ColumnDeleteView.as_view(), name='column_delete'),

    # Card CRUD
    path('column/<int:column_id>/card/new/', views.CardCreateView.as_view(), name='card_create'),
    path('card/<int:pk>/update/', views.CardUpdateView.as_view(), name='card_update'),
    path('card/<int:pk>/delete/', views.CardDeleteView.as_view(), name='card_delete'),
]
