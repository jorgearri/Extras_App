from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
import math
from datetime import date
from .models import Material, Prestamo, Alumno, PrestadorServicio, AsistenciaServicio

# --- AUTENTICACIÓN ---
def login_principal(request): 
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            return redirect('home')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login_principal')

# --- VISTAS PROTEGIDAS ---
@login_required
def home(request): 
    return render(request, 'home.html')

@login_required
def inventario(request):
    return render(request, 'inventario.html', {'materiales': Material.objects.all()})

@login_required
def prestamos(request):
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                nombre_alumno = data.get('nombre_alumno')
                material_id = data.get('material_id')
                cantidad = int(data.get('cantidad', 1))
            else:
                nombre_alumno = request.POST.get('nombre_alumno')
                material_id = request.POST.get('material')
                cantidad = int(request.POST.get('cantidad', 1))

            material = Material.objects.get(id=material_id)

            if material.cantidad < cantidad:
                if request.content_type == 'application/json':
                    return JsonResponse({'status': 'error', 'mensaje': f'No hay suficiente {material.nombre} en inventario.'})
                return redirect('prestamos')

            material.cantidad -= cantidad
            material.save()

            Prestamo.objects.create(
                nombre_alumno=nombre_alumno,
                material=material,
                cantidad=cantidad
            )

            if request.content_type == 'application/json':
                return JsonResponse({'status': 'success', 'mensaje': 'Préstamo registrado exitosamente.'})
            return redirect('prestamos')

        except Material.DoesNotExist:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'mensaje': 'El material no existe.'})
        except Exception as e:
            if request.content_type == 'application/json':
                return JsonResponse({'status': 'error', 'mensaje': str(e)})

    # Esta parte se ejecuta siempre, asegurando que la página cargue los datos correctamente
    materiales_disponibles = Material.objects.filter(cantidad__gt=0)
    prestamos_activos = Prestamo.objects.exclude(estado='Devuelto').order_by('-id')

    contexto = {
        'materiales': materiales_disponibles,
        'prestamos': prestamos_activos
    }
    return render(request, 'prestamos.html', contexto)

def panel_principal(request): 
    return render(request, 'panel.html')

@login_required
def servicio_social(request): 
    return render(request, 'servicio_social.html')

@login_required
def panel_servicio(request):
    return render(request, 'panel_servicio.html', {'datos': PrestadorServicio.objects.all()})

# --- GESTIÓN RÁPIDA ---
@login_required
def registrar_alumno_rapido(request):
    if request.method == 'POST':
        no_control = request.POST.get('nuevo_num_control')
        nombre = request.POST.get('nuevo_nombre')
        if no_control and nombre:
            Alumno.objects.get_or_create(numero_control=no_control, defaults={'nombre_completo': nombre})
    return redirect('prestamos')

@login_required
def devolver_material(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, id=prestamo_id)
    prestamo.material.cantidad += prestamo.cantidad
    prestamo.material.save()
    prestamo.estado = 'Devuelto'
    prestamo.save()
    return redirect('prestamos')

@login_required
def agregar_material(request): 
    return redirect('inventario')

@login_required
def eliminar_material(request, material_id):
    get_object_or_404(Material, id=material_id).delete()
    return redirect('inventario')

# --- APIS Y RECONOCIMIENTO FACIAL ---
def buscar_alumnos_api(request):
    query = request.GET.get('q', '')
    if query:
        alumnos = Alumno.objects.filter(Q(nombre_completo__icontains=query) | Q(numero_control__icontains=query))[:10]
        resultados = [{'numero_control': a.numero_control, 'nombre_completo': a.nombre_completo} for a in alumnos]
        return JsonResponse(resultados, safe=False)
    return JsonResponse([], safe=False)
    
def buscar_materiales_api(request):
    query = request.GET.get('q', '')
    if query:
        materiales = Material.objects.filter(nombre__icontains=query)[:10]
        resultados = [{'id': m.id, 'nombre': m.nombre} for m in materiales]
        return JsonResponse(resultados, safe=False)
    return JsonResponse([], safe=False)

@csrf_exempt
def registrar_rostro_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            no_control = data.get('numero_control')
            nombre = data.get('nombre_completo')
            descriptor = data.get('datos_faciales')
            prestador, _ = PrestadorServicio.objects.get_or_create(numero_control=no_control, defaults={'nombre_completo': nombre})
            prestador.datos_faciales = json.dumps(descriptor)
            prestador.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def marcar_asistencia_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            descriptor_recibido = data.get('datos_faciales')
            prestadores = PrestadorServicio.objects.all()
            
            mejor_match = None
            for p in prestadores:
                if p.datos_faciales:
                    descriptor_db = json.loads(p.datos_faciales)
                    distancia = math.sqrt(sum((a - b) ** 2 for a, b in zip(descriptor_recibido, descriptor_db)))
                    if distancia < 0.6:
                        mejor_match = p
                        break
            
            if mejor_match:
                if mejor_match.activo:
                    AsistenciaServicio.objects.create(prestador=mejor_match, tipo='Salida')
                    mejor_match.activo = False
                    mejor_match.save()
                    return JsonResponse({'status': 'success', 'mensaje': f'Salida registrada. ¡Hasta luego, {mejor_match.nombre_completo}!'})
                else:
                    AsistenciaServicio.objects.create(prestador=mejor_match, tipo='Entrada')
                    mejor_match.activo = True
                    mejor_match.save()
                    return JsonResponse({'status': 'success', 'mensaje': f'Entrada registrada. ¡Bienvenido, {mejor_match.nombre_completo}!'})
                    
            return JsonResponse({'status': 'error', 'mensaje': 'Rostro no reconocido'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def agregar_horas_manual_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            no_control = data.get('numero_control')
            horas_nuevas = data.get('horas', 0)

            prestador = PrestadorServicio.objects.get(numero_control=no_control)

            if not prestador.horas_acumuladas:
                prestador.horas_acumuladas = 0
                
            prestador.horas_acumuladas += int(horas_nuevas)
            prestador.save()

            return JsonResponse({'status': 'success', 'mensaje': f'¡Éxito! Se agregaron {horas_nuevas} horas a {prestador.nombre_completo}.'})
            
        except PrestadorServicio.DoesNotExist:
            return JsonResponse({'status': 'error', 'mensaje': 'Alumno no encontrado. Verifica el Número de Control.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
            
    return JsonResponse({'status': 'error', 'mensaje': 'Método inválido.'})

def acceso_admin_secreto(request):
    if request.method == 'POST':
        if request.POST.get('clave', '').lower() == 'extra2026':
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                login(request, admin_user)
                return redirect(request.GET.get('next', '/admin/'))
    return render(request, 'login_admin.html')