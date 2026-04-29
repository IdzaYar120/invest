from django.urls import path
from . import views

urlpatterns = [
    path('', views.analyze, name='analyze'),
    path('search/', views.ticker_search, name='ticker_search'),
]
