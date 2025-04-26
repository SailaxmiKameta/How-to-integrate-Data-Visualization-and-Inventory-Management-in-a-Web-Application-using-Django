import os
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import InventoryForm, SalesForm  
from .models import Sales, Store, Inventory  
from datetime import datetime  
from django.db.models.functions import ExtractYear, ExtractMonth, ExtractDay
from django.db.models import Sum, Avg
from django.urls import reverse
from django.http import JsonResponse
import logging
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def home(request):
    return render(request, 'home.html')

@ratelimit(key="ip", rate="5/m", method="POST", block=True)  # Rate limit to prevent brute-force
def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_manager:
            login(request, user)
            return redirect("dashboard")  # Redirect to manager dashboard
        else:
            messages.error(request, "Invalid credentials or not a manager")
    return render(request, "inventory_dashboard/login.html")

def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def manager_dashboard(request):
    return render(request, "inventory_dashboard/dashboard.html")

def register(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        # Check if passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match!")
            return redirect('register')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return redirect('register')

        # Check if email is already used
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return redirect('register')

        # Create new manager account
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Manager registered successfully! You can now log in.")
        return redirect('login')

    return render(request, 'inventory_dashboard/register.html')


def add_sales(request):
    if request.method == 'POST':
        form = SalesForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)

            # Automatically compute the day_of_week from the selected date
            if sale.date:
                sale.day_of_week = sale.date.weekday() + 1  # Monday = 0 → Sunday = 7

            sale.save()
            messages.success(request, 'Sales data has been successfully added!')
            return redirect('add_sales')  # Or your desired redirect
    else:
        form = SalesForm()
    return render(request, 'inventory_dashboard/add_sales.html', {'form': form})


def edit_sales(request, store, date):
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        return render(request, 'inventory_dashboard/error.html', {
            'error_message': 'Invalid date format. Please use YYYY-MM-DD.'
        })

    sales = Sales.objects.filter(store=store, date=date_obj)

    if not sales.exists():
        return render(request, 'inventory_dashboard/error.html', {
            'error_message': 'No sales data found for the given store and date.'
        })

    sale = sales.first()

    if request.method == 'POST':
        form = SalesForm(request.POST, instance=sale)
        if form.is_valid():
            form.save()
            messages.success(request, "Sales data updated successfully!") 
            return redirect(reverse('edit_sales', kwargs={'store': store, 'date': date}))
    else:
        form = SalesForm(instance=sale)

    return render(request, 'inventory_dashboard/edit_sales.html', {
        'form': form,
        'sales': sale,
        'store': store,
        'date': date,
    })

def process_sale(store_id, sold_quantity):
    try:
        # Retrieve store and its inventory
        store = Store.objects.get(id=store_id)
        inventory_item = Inventory.objects.get(store=store)
        
        # Update inventory quantity
        inventory_item.quantity -= sold_quantity
        inventory_item.save()

        return JsonResponse({'success': True, 'message': 'Inventory updated successfully'})
    except Inventory.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Inventory for the store not found'})
    except Store.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Store not found'})
    

def sales_dashboard(request):
    # 1. Sales Trend Over Time (Daily + 7-day Moving Average)
    daily_sales = Sales.objects.values('date').annotate(total_sales=Sum('sales')).order_by('date')
    df_sales = pd.DataFrame(list(daily_sales))
    df_sales['date'] = pd.to_datetime(df_sales['date'])
    df_sales['moving_avg'] = df_sales['total_sales'].rolling(window=7).mean()

    sales_time_fig = go.Figure()
    sales_time_fig.add_trace(go.Scatter(x=df_sales['date'], y=df_sales['total_sales'], mode='lines', name='Daily Sales'))
    sales_time_fig.add_trace(go.Scatter(x=df_sales['date'], y=df_sales['moving_avg'], mode='lines', name='7-Day Avg', line=dict(dash='dash')))
    sales_time_fig.update_layout(title='Sales Trend Over Time with Moving Average', xaxis_title='Date', yaxis_title='Total Sales')

    # 2. Sales with/without Promotion Status (Bar Chart)
    promo_sales = Sales.objects.values('promo').annotate(total_sales=Sum('sales')).order_by('promo')
    df_promo_sales = pd.DataFrame(list(promo_sales))
    promo_sales_fig = px.bar(df_promo_sales, x='promo', y='total_sales', title='Sales with/without Promotion', labels={'promo': 'Promotion Status', 'total_sales': 'Total Sales'})
    promo_sales_fig.update_xaxes(tickmode='array', tickvals=[0, 1], ticktext=['No Promo', 'Promo'])


    # 3. Monthly Sales Trend (Year-over-Year Line Plot)
    monthly_sales = Sales.objects.annotate(year=ExtractYear('date'), month=ExtractMonth('date')) \
                                 .values('year', 'month') \
                                 .annotate(total_sales=Sum('sales')) \
                                 .order_by('year', 'month')
    df_monthly_sales = pd.DataFrame(list(monthly_sales))
    df_monthly_sales['month_name'] = pd.to_datetime(df_monthly_sales['month'], format='%m').dt.strftime('%b')
    monthly_sales_fig = px.line(df_monthly_sales, x='month_name', y='total_sales', color='year',
                                title='Monthly Sales Trend by Year', markers=True)

    # 4. Store Type vs Average Sales
    avg_sales_by_type = Sales.objects.select_related('store').values('store__store_type') \
                                     .annotate(avg_sales=Avg('sales')).order_by('store__store_type')
    df_avg_sales = pd.DataFrame(list(avg_sales_by_type))
    avg_sales_fig = px.bar(df_avg_sales, x='store__store_type', y='avg_sales', color='store__store_type',
                           title='Average Sales by Store Type', labels={'store__store_type': 'Store Type'})

    # 5. Sales Distribution Histogram with Boxplot
    all_sales = Sales.objects.values_list('sales', flat=True)
    df_sales_dist = pd.DataFrame({'sales': list(all_sales)})
    sales_dist_fig = px.histogram(df_sales_dist, x='sales', nbins=30, marginal='box',
                                  title='Sales Distribution with Box Plot', labels={'sales': 'Sales Amount'})


    # 6. Yearly Total Sales (Bar)
    yearly_sales = Sales.objects.annotate(year=ExtractYear('date')) \
                                .values('year') \
                                .annotate(total_sales=Sum('sales')) \
                                .order_by('year')
    df_yearly = pd.DataFrame(list(yearly_sales))
    yearly_sales_fig = px.bar(df_yearly, x='year', y='total_sales', text='total_sales',
                              title='Total Sales per Year', labels={'year': 'Year', 'total_sales': 'Total Sales'})

    # 8. Monthly Average Sales (Line Plot)
    monthly_avg_sales = Sales.objects.annotate(month=ExtractMonth('date')) \
                                     .values('month') \
                                     .annotate(avg_sales=Avg('sales')) \
                                     .order_by('month')
    df_monthly_avg = pd.DataFrame(list(monthly_avg_sales))
    df_monthly_avg['month_name'] = pd.to_datetime(df_monthly_avg['month'], format='%m').dt.strftime('%b')
    monthly_avg_fig = px.line(df_monthly_avg, x='month_name', y='avg_sales', markers=True,
                              title='Average Sales by Month', labels={'month_name': 'Month', 'avg_sales': 'Average Sales'})

    # 8. Daily Sales Heatmap (Day vs Month)
    day_month_sales = Sales.objects.annotate(day=ExtractDay('date'), month=ExtractMonth('date')) \
                                   .values('day', 'month') \
                                   .annotate(total_sales=Sum('sales')) \
                                   .order_by('month', 'day')
    df_day_month = pd.DataFrame(list(day_month_sales))
    pivot_heatmap = df_day_month.pivot(index='day', columns='month', values='total_sales')
    heatmap_fig = px.imshow(pivot_heatmap, labels=dict(x="Month", y="Day", color="Total Sales"),
                            title="Daily Sales Heatmap by Month")

    return render(request, 'inventory_dashboard/dashboard.html', {
        'sales_time_fig': sales_time_fig.to_html(full_html=False),
        'promo_sales_fig': promo_sales_fig.to_html(full_html=False),
        'monthly_sales_fig': monthly_sales_fig.to_html(full_html=False),
        'avg_sales_fig': avg_sales_fig.to_html(full_html=False),
        'sales_dist_fig': sales_dist_fig.to_html(full_html=False),
        'yearly_sales_fig': yearly_sales_fig.to_html(full_html=False),
        'monthly_avg_fig': monthly_avg_fig.to_html(full_html=False),
        'heatmap_fig': heatmap_fig.to_html(full_html=False),
        'stores': Store.objects.all(),
    })



@login_required
def forecast_viewer(request):
    plots_dir = os.path.join(settings.MEDIA_ROOT, 'forecast_plots')
    csv_dir = os.path.join(settings.MEDIA_ROOT, 'forecast_csv')

    stores = []
    for file in os.listdir(plots_dir):
        if file.startswith('store_') and file.endswith('.png'):
            store_id = file.split('_')[1]
            stores.append(store_id)

    selected_store = request.GET.get('store')
    plot_url = csv_url = None

    if selected_store:
        plot_url = os.path.join(settings.MEDIA_URL, f'forecast_plots/store_{selected_store}_forecast.png')
        csv_url = os.path.join(settings.MEDIA_URL, f'forecast_csv/store_{selected_store}_forecast.csv')

    return render(request, 'inventory_dashboard/forecast_viewer.html', {
        'stores': sorted(set(stores)),
        'selected_store': selected_store,
        'plot_url': plot_url,
        'csv_url': csv_url,
    })

LOW_STOCK_THRESHOLD = 15000
def inventory_dashboard(request):
    inventories = Inventory.objects.select_related('store').all()
    low_stock_alerts = inventories.filter(quantity__lt=LOW_STOCK_THRESHOLD)
    context = {
        'inventories': inventories,
        'low_stock_alerts': low_stock_alerts,
    }
    return render(request, 'inventory_dashboard.html', context)


def edit_inventory(request, inventory_id):
    inventory = get_object_or_404(Inventory, id=inventory_id)
    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(request, 'Inventory updated successfully!')
            return redirect('inventory_dashboard')
    else:
        form = InventoryForm(instance=inventory)
    return render(request, 'edit_inventory.html', {'form': form, 'inventory': inventory})

def delete_inventory(request, inventory_id):
    inventory = get_object_or_404(Inventory, id=inventory_id)
    if request.method == 'POST':
        inventory.delete()
        messages.success(request, 'Inventory deleted successfully!')
        return redirect('inventory_dashboard')
    return render(request, 'confirm_delete_inventory.html', {'inventory': inventory})