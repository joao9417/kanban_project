"""
URL configuration for kanban_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from tasks import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/register/', views.register, name='register'),
    path('', views.BoardListView.as_view(), name='board_list'),
    path('board/new/', views.BoardCreateView.as_view(), name='board_create'),
    path('board/<int:pk>/', views.BoardDetailView.as_view(), name='board_detail'),
    path('board/<int:board_id>/column/new/', views.ColumnCreateView.as_view(), name='column_create'),
    path('column/<int:column_id>/card/new/', views.CardCreateView.as_view(), name='card_create'),
]
