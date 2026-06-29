from django.db import models

class Location(models.Model):
    address = models.CharField('Адрес', max_length=255, unique=True)
    latitude = models.FloatField('Широта', null=True)
    longitude = models.FloatField('Долгота', null=True)
    
    updated_at = models.DateTimeField('Дата последнего запроса', auto_now=True)

    def __str__(self):
        return self.address