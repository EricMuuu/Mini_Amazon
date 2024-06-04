from django import forms
from django.contrib.auth.models import User
from .models import *


class OrderForm(forms.ModelForm):
    quantity = forms.IntegerField(min_value=1, label='Quantity')
    address = forms.ModelChoiceField(queryset=UserAddress.objects.none(), label='Delivery Address', required=True)
    ups_account_name = forms.CharField(max_length=100, required=False, label='UPS Account Name (optional)')
    eco_friendly = forms.BooleanField(required=False, label='Eco-Friendly Packaging')

    class Meta:
        model = Order
        fields = ['quantity', 'ups_account_name', 'eco_friendly']

    def __init__(self, *args, **kwargs):
        user_profile = kwargs.pop('user_profile', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if user_profile:
            self.fields['address'].queryset = user_profile.useraddress_set.all()
            self.fields['address'].label_from_instance = lambda obj: f"{obj.name} ({obj.address_x}, {obj.address_y})"

    def save(self, commit=True):
        instance = super(OrderForm, self).save(commit=False)
        selected_address = self.cleaned_data['address']
        instance.address_x = selected_address.address_x
        instance.address_y = selected_address.address_y
        if commit:
            instance.save()
        return instance