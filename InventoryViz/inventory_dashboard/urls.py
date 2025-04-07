from django.urls import path
from .views import login_view, manager_dashboard, logout_view, register, add_sales

urlpatterns = [
    path("login/", login_view, name="login"),
    #path("logout/", logout_view, name="logout"),
    path("dashboard/", manager_dashboard, name="dashboard"),
    path('register/', register, name='register'),
    path('add-sales/', add_sales, name='add_sales'), 
]
