from django.db import models
from account.models import *

# Create your models here.
class Warehouse(models.Model):
    address_x = models.IntegerField(default=1)
    address_y = models.IntegerField(default=1)
    
    def __str__(self):
        return f'({self.address_x}, {self.address_y})'

class Product(models.Model):
    category = models.CharField(max_length = 100, null = False)
    description = models.CharField(max_length = 100, null = False)
    quantity = models.IntegerField(default = 1)
    

# 1 order is one package
class Order(models.Model):
    buyer = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    status = models.CharField(max_length = 100, default = "Order Received")
    # Updated to make it optional
    ups_account_name = models.CharField(max_length=100, blank=True, null=True)
    # delivery address
    address_x = models.IntegerField(default=1)
    address_y = models.IntegerField(default=1)
    quantity = models.IntegerField(default = 1)
    truck_id = models.IntegerField(default = 1)

