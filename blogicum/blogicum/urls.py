from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from blog import views as blog_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/registration/', blog_views.registration, name='registration'),
    path('auth/', include('django.contrib.auth.urls')),
    path('pages/', include('pages.urls')),
    path('', include('blog.urls')),
]

handler404 = 'pages.views.page_not_found'
handler500 = 'pages.views.server_error'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
