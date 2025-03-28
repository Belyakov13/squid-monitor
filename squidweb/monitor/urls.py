from django.urls import path
from .views import DashboardView, ConnectionsView, UserDetailView, UsersListView

app_name = 'monitor'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('connections/', ConnectionsView.as_view(), name='connections'),
    path('users/', UsersListView.as_view(), name='users_list'),
    path('user/<str:ip>/', UserDetailView.as_view(), name='user_detail'),
]
