from django.urls import path, include
from movies.admin import custom_admin_site

urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('', include('movies.urls')),
]