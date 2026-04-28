from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analyzer.urls')), # Перенаправляє запити на головну сторінку у ваш додаток
]
