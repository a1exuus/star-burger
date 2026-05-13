from django.http import JsonResponse
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
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


@csrf_exempt
def register_order(request):
    try:
        raw_body = request.body.decode('utf-8')
        print(f"REPR BODY: {repr(raw_body)}")
        data = json.loads(raw_body, strict=False)
        print(f'REPR DATA: {repr(data)}')
    except json.JSONDecodeError as e:
        return JsonResponse(
            {'error': 'invalid_json', 'details': str(e)},
            status=400
        )

    if request.method == 'POST':
        try:
            order = Order.objects.create(
                phone_number=data.get('phonenumber'),
                first_name=data.get('firstname'),
                last_name=data.get('lastname'),
                address=data.get('address'),
            )

            for item in data.get('products', []):
                OrderItem.objects.create(
                    order=order,
                    product_id=item['product'],
                    quantity=item['quantity']
                )
            
            return JsonResponse({'status': 'success'}, status=201)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'Invalid method'}, status=405)
