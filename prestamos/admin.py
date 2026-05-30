from django.contrib import admin
from .models import Material, Alumno, Prestamo, RegistroServicio

# Aquí registramos las tablas para que aparezcan en el panel
admin.site.register(Material)
admin.site.register(Alumno)
admin.site.register(Prestamo)
admin.site.register(RegistroServicio)