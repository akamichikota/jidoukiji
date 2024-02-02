# kijisakusei/urls.py

from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.wordpress_settings, name='wordpress_settings'),
    path('titlekiji_form/', views.titlekiji_form, name='titlekiji_form'),
    path('generate_articles/', views.generate_articles, name='generate_articles'),
    path('settings_form/', views.settings_form, name='settings_form'),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

