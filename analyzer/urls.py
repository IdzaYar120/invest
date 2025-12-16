from django.urls import path
from . import views

urlpatterns = [
    path('', views.analyze, name='home'),
    path('search/', views.ticker_search, name='ticker_search'), 
]