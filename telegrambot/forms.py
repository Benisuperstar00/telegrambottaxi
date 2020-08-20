from django import forms
from telegrambot.models import Profile
from telegrambot.models import Bonus
from .models import Trip


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'external_id',
            'name',
            'surname',
            'number',
        ]
        widgets = {
            'name': forms.TextInput,
            'surname': forms.TextInput,
            'number': forms.TextInput,
        }


class BonusForm(forms.ModelForm):
    class Meta:
        model = Bonus
        fields = (
            'bonus',
            'profile',
        )


class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = (
            'departure',
            'place_of_arrival',
            'dop_trip',
            'taxi_rate',
            'profile',
        )