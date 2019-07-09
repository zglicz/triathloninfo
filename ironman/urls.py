from django.urls import include, path

from . import views

app_name = 'ironman'
urlpatterns = [
    path(r'', views.IndexView.as_view(), name='index'),
    path('race/<int:race_id>/', views.RaceView.as_view(), name='race'),
    path('stats/', views.StatsView.as_view(), name='stats'),
]