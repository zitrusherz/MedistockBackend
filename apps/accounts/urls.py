# apps/accounts/urls.py
from django.urls import path
from .views import CustomTokenObtainPairView, RegisterView, MeView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('login/',   CustomTokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(),          name='token_refresh'),
    path('register/', RegisterView.as_view(),             name='register'),
    path('me/',      MeView.as_view(),                    name='me'),
]