from django.urls import path
from . import views
from .views import forecast_viewer, login_view, manager_dashboard, logout_view, register, add_sales, edit_sales, sales_dashboard


urlpatterns = [
     
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", manager_dashboard, name="dashboard"),
    path('register/', register, name='register'),
    path('add-sales/', add_sales, name='add_sales'), 
    path('edit/<int:store>/<str:date>/', edit_sales, name='edit_sales'),
    path("sales-dashboard/", sales_dashboard, name="sales_dashboard"),
    path('forecast-viewer/', forecast_viewer, name='forecast_viewer'),
    path('inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('inventory/edit/<int:inventory_id>/', views.edit_inventory, name='edit_inventory'),
    path('inventory/sale/<int:store_id>/<int:sold_quantity>/', views.process_sale, name='process_sale'),

]
