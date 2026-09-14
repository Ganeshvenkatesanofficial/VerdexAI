from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def api_root(request):
    return JsonResponse({
        "project": "Verdex AI API",
        "status": "running",
        "endpoints": {
            "admin": "/admin/",
            "companies": "/api/companies/",
            "documents": "/api/documents/",
            "tenders": "/api/tenders/",
            "verdicts": "/api/verdicts/",
        },
        "message": "Welcome to Verdex AI backend. Use the endpoints above to access the API.",
    })


urlpatterns = [
    path('', api_root, name='api_root'),
    path('admin/', admin.site.urls),
    path('api/', include('companies.urls')),
    path('api/', include('vault.urls')),
    path('api/', include('tenders.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
