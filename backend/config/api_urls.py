from django.urls import path, include

urlpatterns = [
    path('auth/', include('accounts.urls')),
    path('policies/', include('policies.urls')),
    path('claims/', include('claims.urls')),
]
