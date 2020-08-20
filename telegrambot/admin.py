from django.contrib import admin
from .forms import ProfileForm
from .forms import BonusForm
from .forms import TripForm
from .models import Profile
from .models import Bonus
from .models import Trip


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'external_id', 'name', 'surname', 'number')
    list_display_links = ('external_id',)
    list_filter = ('external_id', 'surname', 'number')
    search_fields = ('external_id', 'number')
    form = ProfileForm


@admin.register(Bonus)
class BonusAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'bonus')
    list_display_links = ('profile',)
    list_filter = ('profile', 'bonus')
    search_fields = ('profile__external_id', 'profile__name')
    form = BonusForm


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'departure', 'place_of_arrival', 'dop_trip', 'taxi_rate')
    list_display_links = ('profile',)
    list_filter = ('departure', 'place_of_arrival')
    search_fields = ('departure', 'place_of_arrival')


admin.site.site_title = "Телеграм бот"
admin.site.site_title = "Телеграм бот"
