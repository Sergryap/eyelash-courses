from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('courses.urls')),
]
if settings.DEBUG:
    import debug_toolbar
    urlpatterns.extend(
        [*static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
         path(r'__debug__/', include(debug_toolbar.urls))],
    )
