from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import SalesForm  
from .models import Sales, Store, Inventory  
from datetime import datetime  
from django.db.models.functions import ExtractYear, ExtractMonth
from django.db.models import Sum, Avg
from django.urls import reverse
from django.http import JsonResponse
import logging
import pandas as pd
import plotly.express as px


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
    # 1. Total Sales Over Time
    daily_sales = Sales.objects.values('date').annotate(total_sales=Sum('sales')).order_by('date')
    df_sales = pd.DataFrame(list(daily_sales))
    df_sales['date'] = pd.to_datetime(df_sales['date'])
    sales_time_fig = px.line(df_sales, x='date', y='total_sales', title='Sales Trend Over Time', labels={'date': 'Date', 'total_sales': 'Total Sales'})
    
    # 2. Sales with/without Promotion
    promo_sales = Sales.objects.values('promo').annotate(total_sales=Sum('sales')).order_by('promo')
    df_promo_sales = pd.DataFrame(list(promo_sales))
    promo_sales_fig = px.bar(df_promo_sales, x='promo', y='total_sales', title='Sales with/without Promotion', labels={'promo': 'Promotion Status', 'total_sales': 'Total Sales'})
    promo_sales_fig.update_xaxes(tickmode='array', tickvals=[0, 1], ticktext=['No Promo', 'Promo'])

    # 3. Seasonal Trends (Monthly and Yearly)
    monthly_sales = Sales.objects.annotate(year=ExtractYear('date'), month=ExtractMonth('date')) \
                                 .values('year', 'month') \
                                 .annotate(total_sales=Sum('sales')) \
                                 .order_by('year', 'month')
    df_monthly_sales = pd.DataFrame(list(monthly_sales))
    pivot_sales = df_monthly_sales.pivot(index='month', columns='year', values='total_sales')
    seasonal_sales_fig = px.imshow(pivot_sales, title='Sales Trend Heatmap (Monthly and Yearly)', labels=dict(x="Year", y="Month", color="Total Sales"))

    # 4. Average Sales by Store Type
    avg_sales_by_type = Sales.objects.select_related('store').values('store__store_type') \
                                     .annotate(avg_sales=Avg('sales')).order_by('store__store_type')
    df_avg_sales = pd.DataFrame(list(avg_sales_by_type))
    avg_sales_fig = px.bar(df_avg_sales, x='store__store_type', y='avg_sales', title='Average Sales by Store Type', labels={'store__store_type': 'Store Type', 'avg_sales': 'Average Sales'})

    # 5. Sales Distribution Histogram
    all_sales = Sales.objects.values_list('sales', flat=True)
    df_sales_dist = pd.DataFrame({'sales': list(all_sales)})
    sales_dist_fig = px.histogram(df_sales_dist, x='sales', nbins=20, title='Sales Distribution Histogram')

    # 6. Promotion vs No Promotion (Box Plot)
    promo_vs_non = Sales.objects.values('promo', 'sales')
    df_promo_box = pd.DataFrame(list(promo_vs_non))
    df_promo_box['promo'] = df_promo_box['promo'].replace({0: 'No Promo', 1: 'Promo'})
    promo_box_fig = px.box(df_promo_box, x='promo', y='sales', title='Sales Spread: Promotion vs No Promotion', labels={'promo': 'Promotion Status', 'sales': 'Sales'})

    # 7. Yearly Sales Overview
    yearly_sales = Sales.objects.annotate(year=ExtractYear('date')) \
                                .values('year') \
                                .annotate(total_sales=Sum('sales')) \
                                .order_by('year')
    df_yearly = pd.DataFrame(list(yearly_sales))
    yearly_sales_fig = px.bar(df_yearly, x='year', y='total_sales', title='Yearly Sales Overview', labels={'year': 'Year', 'total_sales': 'Total Sales'})

    # 8. Monthly Average Sales
    monthly_avg_sales = Sales.objects.annotate(month=ExtractMonth('date')) \
                                     .values('month') \
                                     .annotate(avg_sales=Avg('sales')) \
                                     .order_by('month')
    df_monthly_avg = pd.DataFrame(list(monthly_avg_sales))
    monthly_avg_fig = px.line(df_monthly_avg, x='month', y='avg_sales', title='Average Sales per Month', labels={'month': 'Month', 'avg_sales': 'Average Sales'})

    return render(request, 'inventory_dashboard/dashboard.html', {
        'sales_time_fig': sales_time_fig.to_html(full_html=False),
        'promo_sales_fig': promo_sales_fig.to_html(full_html=False),
        'seasonal_sales_fig': seasonal_sales_fig.to_html(full_html=False),
        'avg_sales_fig': avg_sales_fig.to_html(full_html=False),
        'sales_dist_fig': sales_dist_fig.to_html(full_html=False),
        'promo_box_fig': promo_box_fig.to_html(full_html=False),
        'yearly_sales_fig': yearly_sales_fig.to_html(full_html=False),
        'monthly_avg_fig': monthly_avg_fig.to_html(full_html=False),
        'stores': Store.objects.all(),
    })
    
