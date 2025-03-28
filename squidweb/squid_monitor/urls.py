from django.urls import path
from monitor.views import DashboardView, ConnectionsView, UsersListView, UserDetailView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('connections/', ConnectionsView.as_view(), name='connections'),
    path('users/', UsersListView.as_view(), name='users'),
    path('user/<str:ip>/', UserDetailView.as_view(), name='user_detail'),
]
