from django.utils import timezone
import datetime
import requests
from django.conf import settings
from .models import Location


def fetch_yandex_coordinates(address):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": settings.YANDEX_API_KEY,
        "format": "json",
    })
    response.raise_for_status()
    
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']
    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return lat, lon


def get_cached_or_fresh_coordinates(addresses):
    if not addresses:
        return {}

    locations = Location.objects.filter(address__in=addresses)
    
    coords_dict = {}
    outdated_addresses = set()
    
    cache_ttl = datetime.timedelta(days=30)
    now = timezone.now()
    
    for loc in locations:
        if now - loc.updated_at > cache_ttl:
            outdated_addresses.add(loc.address)
        else:
            coords_dict[loc.address] = (str(loc.latitude), str(loc.longitude))
            
    missing_addresses = (set(addresses) - set(coords_dict.keys())) | outdated_addresses
    
    for address in missing_addresses:
        try:
            result = fetch_yandex_coordinates(address)
            if result:
                lat, lon = result
                location, _ = Location.objects.update_or_create(
                    address=address,
                    defaults={'latitude': float(lat), 'longitude': float(lon)}
                )
                coords_dict[address] = (str(location.latitude), str(location.longitude))
        except Exception as e:
            print(f"Ошибка геокодирования адреса {address}: {e}")
            
    return coords_dict