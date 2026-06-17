from django.db import models
from django.db.models import Sum, F
from django.db.models.functions import Coalesce
from django.core.validators import MinValueValidator
from phonenumber_field.modelfields import PhoneNumberField
from django.utils import timezone
from collections import defaultdict


class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"


class OrderQuerySet(models.QuerySet):
    def with_total_cost(self):
        return self.annotate(
            total_cost=Coalesce(
                Sum(
                    Coalesce(F('order_items__price'), F('order_items__product__price')) 
                    * F('order_items__quantity')
                ),
                models.Value(0),
                output_field=models.DecimalField()
            )
        )
    

    def returns_ready_restaurants(self):
        menu_items = RestaurantMenuItem.objects.all().select_related('restaurant',
                                                                     'product')
        restaurants_with_products = defaultdict(list)
        for item in menu_items:
            restaurants_with_products[item.restaurant].append(item.product)
        for order in self:
            order_products = [product.product for product in order.\
                              order_items.select_related('product')]
            ready_restaurants = []
            for restaurant, r_products in restaurants_with_products.items():
                if all(elem in r_products for elem in order_products):
                    ready_restaurants.append(restaurant.name)
            order.ready_restaurants = ready_restaurants
        return self



class Order(models.Model):
    ORDER_STATUES = (
        ('NPRC', 'Не обработан'),
        ('ACTD', 'Принят'),
        ('PRCD', 'Готовится'),
        ('DLVR', 'Доставляется'),
        ('DLRD', 'Выполнен')
    )
    PAYMENT_WAY_CHOICES = (
        ('CASH', 'Наличными'),
        ('ELCT', 'Электронно'),
    )
    firstname = models.CharField(
        max_length=20,
        verbose_name='Имя'
        )
    lastname = models.CharField(
        max_length=30,
        verbose_name='Фамилия'
        )
    phonenumber = PhoneNumberField(
        region="RU",
        verbose_name='Номер телефона',
        max_length=18
        )  # type: ignore
    address = models.CharField(
        max_length=70,
        verbose_name='Адрес'
        )
    status = models.CharField(
        max_length=4,
        choices=ORDER_STATUES,
        db_index=True, default='NPRC',
        verbose_name='Статус'
        )
    payment_way = models.CharField(
        max_length=5,
        choices=PAYMENT_WAY_CHOICES,
        db_index=True,
        verbose_name='Способ оплаты',
        blank=True
        )
    comment = models.TextField(
        max_length=300,
        verbose_name='Комментарий к заказу',
        blank=True
        )
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='orders',
        verbose_name='Ресторан',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )
    registrated_at = models.DateTimeField(
        db_index=True,
        default=timezone.now,
        verbose_name='Дата и время регистрации'
        )
    called_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name='Дата и время звонка'
    )
    delivered_at = models.DateTimeField(
        blank=True, 
        null=True, 
        verbose_name='Дата и время доставки'
    )

    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'

    def __str__(self):
        return f'{self.firstname} {self.lastname}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order,
                              related_name='order_items',
                              verbose_name='Заказ',
                              on_delete=models.CASCADE)
    product = models.ForeignKey(Product,
                                related_name='order_items',
                                verbose_name='Продукт',
                                on_delete=models.CASCADE)
    price = models.DecimalField(
        'Цена',
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True,
        null=True
    )
    quantity = models.PositiveIntegerField(
        db_index=True,
        verbose_name='Количество'
        )

    class Meta:
        ordering = ['quantity']