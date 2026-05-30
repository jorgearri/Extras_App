from django.db import models
from django.apps import apps

class Material(models.Model):
    ESTADOS_FISICOS = [
        ('Bueno', 'Buen Estado'),
        ('Medio', 'Estado Medio'),
        ('Malo', 'Mal Estado'),
    ]

    nombre = models.CharField(max_length=200)
    cantidad = models.IntegerField(default=1)
    caracteristicas = models.JSONField(default=dict, blank=True)
    estado_fisico = models.CharField(max_length=10, choices=ESTADOS_FISICOS, default='Bueno')
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    fecha_llegada = models.DateField(null=True, blank=True)

    @property
    def en_prestamo(self):
        Prestamo = apps.get_model('prestamos', 'Prestamo')
        prestamos_activos = Prestamo.objects.exclude(estado='Devuelto').filter(material=self)
        return sum(p.cantidad for p in prestamos_activos)

    @property
    def disponibles(self):
        return self.cantidad - self.en_prestamo

    def __str__(self):
        return f"{self.nombre} ({self.estado_fisico})"

class Alumno(models.Model):
    numero_control = models.CharField(max_length=20, unique=True)
    nombre_completo = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.numero_control} - {self.nombre_completo}"

class Prestamo(models.Model):
    ESTADOS = (
        ('Entregado', 'Entregado'),
        ('Pendiente', 'Pendiente'),
        ('No Entregado', 'No Entregado'),
    )
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    fecha_salida = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    fecha = models.DateField(auto_now_add=True, null=True, blank=True)
    cantidad = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.alumno} - {self.material} ({self.cantidad})"
    
class RegistroServicio(models.Model):
    alumno = models.OneToOneField(Alumno, on_delete=models.CASCADE)
    horas_acumuladas = models.IntegerField(default=0)
    estado = models.CharField(max_length=20, choices=[('Activo', 'Activo'), ('Terminado', 'Terminado')], default='Activo')

    def __str__(self):
        return f"Servicio Social: {self.alumno.nombre_completo} - {self.horas_acumuladas} hrs"

# --- SERVICIO SOCIAL FACIAL ---

class PrestadorServicio(models.Model):
    numero_control = models.CharField(max_length=20, unique=True)
    nombre_completo = models.CharField(max_length=200)
    datos_faciales = models.JSONField(null=True, blank=True, help_text="Vectores matemáticos del rostro")
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_completo

class AsistenciaServicio(models.Model):
    TIPO_REGISTRO = [('Entrada', 'Entrada'), ('Salida', 'Salida')]
    
    prestador = models.ForeignKey(PrestadorServicio, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True) # Cambiamos a DateTime para mayor precisión
    tipo = models.CharField(max_length=20, choices=TIPO_REGISTRO, default='Entrada')

    def __str__(self):
        return f"{self.prestador.nombre_completo} - {self.tipo} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"
