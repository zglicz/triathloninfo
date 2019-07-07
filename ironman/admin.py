from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Race, RaceResult

admin.site.register(Race)
admin.site.register(RaceResult)
# admin.site.register(ComputedRaceData)