from django import forms
from django.shortcuts import redirect, render
from django.views import View
from django.urls import reverse_lazy
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages

from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views

from foodcartapp.models import Product, Restaurant, Order

from environs import Env
from geopy import distance
import requests

env = Env()
env.read_env()

YANDEX_API_KEY = env('YANDEX_API_KEY')


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


def fetch_coordinates(address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": YANDEX_API_KEY,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return (lat, lon)


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    orders = (Order.objects.exclude(status='DLRD')
              .select_related('restaurant')
              .prefetch_related('order_items__product__menu_items')
              .with_total_cost()
              .returns_ready_restaurants())

    orders_with_availability = []
    for order in orders:
        items_with_availability = []
        common_restaurants = set(restaurants)
        
        for item in order.order_items.all():
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


        try:
            order_coordinates = fetch_coordinates(order.address)
        except Exception:
            messages.error(request, f"Ошибка координат для заказа №{order.id} ({order.address}): {e}")
            continue

        print(order_coordinates)

        for restaraunt in common_restaurants:
            try:
                restaraunt_coordinates = fetch_coordinates(restaraunt.address)
            except Exception as e:
                messages.error(request, f"Ошибка координат для ресторана №{restaraunt.id} ({restaraunt.address}): {e}")
                continue

            print(restaraunt_coordinates)

            if order_coordinates and restaraunt_coordinates:
                order_distance = distance.distance(restaraunt_coordinates, order_coordinates).km
                restaraunt.distance_to_order = round(order_distance, 2)
            else:
                restaraunt.distance_to_order = None

            common_restaurants_with_distance.append(restaraunt)

        common_restaurants_with_distance.sort(
            key=lambda r: r.distance_to_order if r.distance_to_order is not None else float('inf')
        )

        orders_with_availability.append((order, common_restaurants_with_distance))


    return render(request, template_name='order_items.html', context={
        'order_items': orders_with_availability,
    })  