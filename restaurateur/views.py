from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch
from django.conf import settings

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order, OrderItem
from geocache.models import Location
from geocache.utils import get_cached_or_fresh_coordinates

from geopy import distance
import requests
import datetime


class Login(forms.Form):
    username = forms.CharField(
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    orders = (Order.objects.exclude(status='DLRD')
              .select_related('restaurant')
              .with_total_cost()
              .returns_ready_restaurants())

    order_ids = [order.id for order in orders]
    all_items = (OrderItem.objects
                 .filter(order_id__in=order_ids)
                 .select_related('product')
                 .prefetch_related('product__menu_items')
                 .order_by('order_id', 'quantity'))
    
    items_by_order = {}
    for item in all_items:
        items_by_order.setdefault(item.order_id, []).append(item)

    all_addresses = set()
    for order in orders:
        all_addresses.add(order.address)
    for restaurant in restaurants:
        all_addresses.add(restaurant.address)

    coordinates = get_cached_or_fresh_coordinates(all_addresses)

    orders_with_availability = []
    for order in orders:
        items_with_availability = []
        common_restaurants = set(restaurants)
        
        order_items_list = items_by_order.get(order.id, [])
        
        for item in order_items_list:
            availability = {
                mi.restaurant_id: mi.availability
                for mi in item.product.menu_items.all()
            }
            available_restaurants = [
                restaurant for restaurant in restaurants
                if availability.get(restaurant.id, False)
            ]
            items_with_availability.append((item, available_restaurants))
            common_restaurants &= set(available_restaurants)

        common_restaurants_with_distance = []
        order_coordinates = coordinates.get(order.address)

        for restaurant in common_restaurants:
            restaurant_coordinates = coordinates.get(restaurant.address)

            if order_coordinates and restaurant_coordinates:
                order_distance = distance.distance(restaurant_coordinates, order_coordinates).km
                distance_value = round(order_distance, 2)
            else:
                distance_value = None

            common_restaurants_with_distance.append((restaurant, distance_value))

        common_restaurants_with_distance.sort(
            key=lambda x: x[1] if x[1] is not None else float('inf')
        )
        
        orders_with_availability.append((order, common_restaurants_with_distance))

    return render(request, template_name='order_items.html', context={
        'order_items': orders_with_availability,
    })