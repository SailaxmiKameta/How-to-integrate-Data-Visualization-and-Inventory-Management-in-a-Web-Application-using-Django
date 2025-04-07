from django.contrib.auth.models import AbstractUser
from django.db import models

class StoreManager(AbstractUser):
    is_manager = models.BooleanField(default=True)  # Identify store managers
