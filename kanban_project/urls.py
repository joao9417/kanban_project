"""
URL configuration for kanban_project.
Routes are split between the `boards` and `teams` apps.
"""
from django.contrib import admin
from django.urls import path, include
from boards import views as boards_views

urlpatterns = [
    path('admin/doc/', include('django.contrib.admindocs.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/register/', boards_views.register, name='register'),
    # Board / Column / Card views
    path('', include('boards.urls')),
    # Team management & project lifecycle
    path('', include('teams.urls')),
]
