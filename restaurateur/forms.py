from django import forms
from django.forms import inlineformset_factory

from foodcartapp.models import Order, OrderItem


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'firstname',
            'lastname',
            'phonenumber',
            'address',
            'status',
            'payment_way',
            'comment',
        ]
        widgets = {
            'firstname': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'lastname': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'phonenumber': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'status': forms.Select(attrs={
                'class': 'form-control',
            }),
            'payment_way': forms.Select(attrs={
                'class': 'form-control',
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
        }


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
            }),
        }


OrderItemFormSet = inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    extra=0,
)