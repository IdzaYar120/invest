from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('analyzer.urls')),
    path('sw.js', TemplateView.as_view(template_name='analyzer/sw.js', content_type='application/javascript'), name='sw.js'),
]