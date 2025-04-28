from django.contrib.auth.models import AbstractUser
from django.db import models

class StoreManager(AbstractUser):
    is_manager = models.BooleanField(default=True)  # Identify store managers

    def __str__(self):
        return self.username


class Store(models.Model):
    store_id = models.IntegerField(primary_key=True)
    store_type = models.CharField(max_length=1)  # A, B, C, D
    assortment = models.CharField(max_length=1)  # Basic, Extra, Extended
    competition_distance = models.IntegerField(null=True, blank=True)
    competition_open_since_month = models.IntegerField(null=True, blank=True)
    competition_open_since_year = models.IntegerField(null=True, blank=True)
    promo2 = models.BooleanField(default=False)
    promo2_since_week = models.IntegerField(null=True, blank=True)
    promo2_since_year = models.IntegerField(null=True, blank=True)
    promo_interval = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Store {self.store_id}"


class Sales(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    day_of_week = models.IntegerField()
    date = models.DateField()
    sales = models.DecimalField(max_digits=10, decimal_places=2)
    customers = models.IntegerField()
    open = models.BooleanField()
    promo = models.BooleanField()
    state_holiday = models.CharField(max_length=1)  # '0', 'a', 'b', 'c'
    school_holiday = models.BooleanField()

    def __str__(self):
        unique_together = ('store', 'date')
        return f"Sales for Store {self.store.store_id} on {self.date}"
    

class Inventory(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    category_name = models.CharField(max_length=50, null=True, blank=True)
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Inventory for Store {self.store.id}"


class Forecast(models.Model):
    store_id = models.IntegerField()
    date = models.DateField()
    forecasted_sales = models.FloatField()

    class Meta:
        # Prevent duplicates for the same store and date
        unique_together = ('store_id', 'date')  

    def __str__(self):
        return f"Store {self.store_id} - {self.date} : {self.forecasted_sales}"
    

class DummyCategoryInventory(models.Model):
    """
    Dummy categories generated dynamically
    """
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    category_name = models.CharField(max_length=50)
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category_name} - Store {self.store.store_id}"