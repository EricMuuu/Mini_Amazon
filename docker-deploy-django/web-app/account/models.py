from django.db import models
from django.contrib.auth.models import User

# Create your models here.
# TODO: A user can have multiple address?
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=20)
    first_name = models.CharField(max_length=20, default='Bob')
    last_name = models.CharField(max_length=20, default='Allen')
    phone = models.CharField(max_length=10, default='1234567890')
    email = models.EmailField(default='example@example.com')
    ups_id = models.IntegerField(default=1)
    environment_tracker = models.IntegerField(default=0)
    
    def __str__(self):
        return self.user.username

class UserAddress(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length = 100)
    address_x = models.IntegerField(default=1)
    address_y = models.IntegerField(default=1)
