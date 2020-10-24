from django.db import models


# Профиль
class Profile(models.Model):
    external_id = models.PositiveIntegerField(
        verbose_name='ID пользователя в боте',
    )
    name = models.TextField(
        verbose_name='Имя пользователя',
    )
    surname = models.TextField(
        verbose_name='Фамилия пользователя',
    )
    number = models.TextField(
        verbose_name='Номер телефона',
    )

    # Метод отображения

    def __str__(self):
        return f'#{self.external_id} {self.name}'

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'


# Бонусы
class Bonus(models.Model):
    profile = models.ForeignKey(
        Profile,
        verbose_name='Профиль',
        on_delete=models.SET_NULL,
        null=True,
    )
    bonus = models.PositiveIntegerField(
        verbose_name='Бонус',
    )

    # Метод отображения
    def __str__(self):
        return f'#Количество {self.bonus} для {self.profile}'

    class Meta:
        verbose_name = 'Бонус'
        verbose_name_plural = 'Бонусы'


class Trip(models.Model):
    departure = models.TextField(
        verbose_name='Место посадки'
    )
    place_of_arrival = models.TextField(
        verbose_name='Место прибытия'
    )
    dop_trip = models.TextField(
        null=True,
        verbose_name='Дополнительная точка'
    )
    taxi_rate = models.TextField(
        null=True,
        verbose_name='Рейтинг поездки'
    )

    profile = models.ForeignKey(
        Profile,
        verbose_name='Профиль',
        on_delete=models.SET_NULL,
        null=True,
    )

    def __str__(self):
        return f'#От {self.departures} до {self.place_of_arrival}'


    class Meta:
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'
