from django.http import JsonResponse
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
import json


from .models import Product
from .models import Order
from .models import OrderItem


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_order(request):
    data = request.data

    try:
        order = Order.objects.create(
            phone_number=data.get('phonenumber'),
            first_name=data.get('firstname'),
            last_name=data.get('lastname'),
            address=data.get('address'),
        )

        if data.get('products', []):
            for item in data.get('products'):
                OrderItem.objects.create(
                    order=order,
                    product_id=item['product'],
                    quantity=item['quantity']
                )
        else:
            return Response({'status': 'products list cannot be empty or unexisted'})
        
        return Response({'status': 'success'}, status=201)
        
    except Exception as e:
        return Response({'error': str(e)}, status=400)

