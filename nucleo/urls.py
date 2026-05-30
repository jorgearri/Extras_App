from django.contrib import admin
from django.urls import path
from prestamos import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_principal, name='login_principal'),
    path('inicio/', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('checador/', views.panel_principal, name='panel_principal'),
    path('inventario/', views.inventario, name='inventario'),
    path('prestamos/', views.prestamos, name='prestamos'),
    path('servicio-social/', views.servicio_social, name='servicio_social'),
    path('panel-servicio/', views.panel_servicio, name='panel_servicio'),
    path('registrar-alumno/', views.registrar_alumno_rapido, name='registrar_alumno_rapido'),
    path('devolver-material/<int:prestamo_id>/', views.devolver_material, name='devolver_material'),
    path('agregar-material/', views.agregar_material, name='agregar_material'),
    path('eliminar-material/<int:material_id>/', views.eliminar_material, name='eliminar_material'),
    path('acceso-restringido/', views.acceso_admin_secreto, name='acceso_restringido'),
    path('login-inventario/', views.login_principal, name='login_inventario'),
    path('login-servicio/', views.login_principal, name='login_servicio'),
    path('api/buscar-alumnos/', views.buscar_alumnos_api, name='buscar_alumnos_api'),
    path('api/buscar-materiales/', views.buscar_materiales_api, name='buscar_materiales_api'),
    path('api/registrar-rostro/', views.registrar_rostro_api, name='registrar_rostro_api'),
    path('api/marcar-asistencia/', views.marcar_asistencia_api, name='marcar_asistencia_api'),
    path('api/agregar-horas-manual/', views.agregar_horas_manual_api, name='agregar_horas_manual_api'),
]