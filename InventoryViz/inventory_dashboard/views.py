from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import SalesForm  
from .models import Sales, Store, Inventory  
from datetime import datetime  
from django.urls import reverse
from django.http import JsonResponse


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

