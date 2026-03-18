"""
teams/urls.py
URL patterns for team/member management and project lifecycle.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Team management (owner only)
    path('board/<int:pk>/members/', views.BoardMembersView.as_view(), name='board_members'),
    # Project lifecycle: mark board finished (triggers analytics signal)
    path('board/<int:pk>/finish/', views.BoardFinishView.as_view(), name='board_finish'),
    
    # Ownership transfer
    path('board/<int:pk>/transfer-leadership/', views.BoardTransferLeadershipView.as_view(), name='board_transfer_leadership'),
]
