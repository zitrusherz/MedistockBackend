from django.urls import path

from .views import (
    RegionListView,
    RegionsWithComunasView,
    ComunaListView,
    ComunaChilexpressListView,
    SucursalListView,      # <-- nuevo
    SucursalDetailView,
)

urlpatterns = [
    path('regions/', RegionListView.as_view(), name='regions-list'),
    path('regions-with-comunas/', RegionsWithComunasView.as_view(), name='regions-with-comunas'),
    path('comunas/', ComunaListView.as_view(), name='comunas-list'),
    path('comunas-chilexpress/', ComunaChilexpressListView.as_view(), name='comunas-chilexpress-list'),
    path('sucursales/', SucursalListView.as_view(), name='sucursales-list'),          # <-- nuevo
    path('sucursales/<int:pk>/', SucursalDetailView.as_view(), name='sucursal-detail'),
]