from django.http import JsonResponse
from django.templatetags.static import static
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, IntegerField, Serializer, ValidationError
from rest_framework.permissions import AllowAny
from phonenumber_field.phonenumber import PhoneNumber
from phonenumber_field.serializerfields import PhoneNumberField
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


class OrderItemSerializer(Serializer):
    product = IntegerField(min_value=1)
    quantity = IntegerField(min_value=1)


class OrderSerializer(ModelSerializer):
    products = OrderItemSerializer(many=True, write_only=True, allow_empty=False)

    class Meta:
        model = Order
        fields = ['id', 'firstname', 'lastname', 'phonenumber', 'address', 'products']

    def validate_products(self, value):
        if not value:
            raise ValidationError("Список товаров не может быть пустым")
        
        product_ids = {item['product'] for item in value}
        existing_ids = set(Product.objects.filter(id__in=product_ids).values_list('id', flat=True))
        missing = product_ids - existing_ids
        if missing:
            raise ValidationError(
                f"Продукты с ID {', '.join(map(str, missing))} не существуют"
            )
        return value

    def create(self, validated_data):
        products_data = validated_data.pop('products')
        order = Order.objects.create(**validated_data)
        
        product_ids = [item['product'] for item in products_data]
        products = {p.id: p for p in Product.objects.filter(id__in=product_ids)}
        
        order_items = []
        for item in products_data:
            product = products[item['product']]
            order_items.append(OrderItem(
                order=order,
                product=product,
                quantity=item['quantity']
            ))
        OrderItem.objects.bulk_create(order_items)
        return order


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
@transaction.atomic
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    order = serializer.save()
    return Response(OrderSerializer(order).data)