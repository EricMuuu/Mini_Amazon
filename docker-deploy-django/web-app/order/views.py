from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from .forms import *
import socket
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .utility import *

# Initialize product table
def initialize_products():
    Product.objects.bulk_create([
        Product(category='Fruit', description='Apple', quantity=1),
        Product(category='Fruit', description='Banana', quantity=1),
        Product(category='Fruit', description='Orange', quantity=1),
        Product(category='Pop', description='Pepsi', quantity=1),
        Product(category='Pop', description='Coca-Cola', quantity=1),
        Product(category='Pop', description='Dr.Pepper', quantity=1),
        Product(category='Electronics', description='MacBook Pro', quantity=1),
        Product(category='Electronics', description='MacBook Air', quantity=1),
        Product(category='Electronics', description='Microwave', quantity=1),
        Product(category='Cloth', description='Jeans', quantity=1),
        Product(category='Cloth', description='Hoodie', quantity=1),
        Product(category='Cloth', description='Shorts', quantity=1)
    ])


@login_required
@csrf_exempt
def product_catalog(request):
    if not Product.objects.exists():
        initialize_products()
    products = Product.objects.all()
    if 'search' in request.GET:
        search_term = request.GET['search']
        products = Product.objects.filter(category__icontains=search_term)
    else:
        products = Product.objects.all()
    return render(request, 'order/product_catalog.html', {'products': products})

@login_required
@csrf_exempt
def order_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    user_profile = request.user.userprofile

    if request.method == 'POST':
        form = OrderForm(request.POST, user_profile=user_profile)
        if form.is_valid():
            new_order = form.save(commit=False)
            new_order.product = product
            new_order.buyer = user_profile
            new_order.save()
            # Increment environment tracker of this user
            if form.cleaned_data['eco_friendly']:
                user_profile.environment_tracker += 1
                user_profile.save()

            send_confirmation_email(new_order.id)
            # Send the order id to the socket
            send_message(str(new_order.id))
            return redirect('order_confirmation', order_id=new_order.id)
    else:
        form = OrderForm(request.POST, user_profile=user_profile)
        print(form.errors)
        form = OrderForm(user_profile=user_profile)

    return render(request, 'order/order_product.html', {'form': form, 'product': product})

@login_required
@csrf_exempt
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    return render(request, 'order/order_confirmation.html', {'order': order})

@login_required
@csrf_exempt
def track_order_form(request):
    return render(request, 'order/track_order_form.html')


@login_required
@csrf_exempt
def track_order(request):
    if request.method == 'POST':
        tracking_number = request.POST.get('tracking_number')
        try:
            order = Order.objects.get(pk=tracking_number)
            return redirect('order_confirmation', order_id=order.id)
        except Order.DoesNotExist:
            return render(request, 'order/track_order_form.html', {
                'error_message': "No order found with that tracking number."
            })
    else:
        return redirect('track_order_form')
    
# For sending msg to the protocal part
def send_message(message):
    host = '152.3.53.96'
    port = 45678
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    client_socket.send(message.encode())
    client_socket.close()



# Sending email
def send_confirmation_email(order_id):
    current_order = Order.objects.get(pk=order_id)

    # Use Gmail API for sending emails
    service = gmail_authenticate()

    # Email content
    sender_email = "m271693043@gmail.com"
    owner_email = current_order.buyer.email

    username = current_order.buyer.username

    status = current_order.status

    subject = "Order Update From Amazon"

    message_body = f"Dear {owner_email},\n\nYour order from Amazon, order id {order_id}, has been updated to {status}.\n\n"

    message_body += "Thank you for choosing Amazon."

    # Send emails
    send_message_gmail(service, sender_email, owner_email, subject, message_body)

def order_list(request):
    user_profile = request.user.userprofile
    orders = Order.objects.filter(buyer=user_profile)
    return render(request, 'order/order_list.html', {'orders': orders})