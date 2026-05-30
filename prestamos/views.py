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

# --- INVENTARIO Y PRÉSTAMOS ---
@login_required
def home(request): return render(request, 'home.html')

@login_required
def inventario(request):
    return render(request, 'inventario.html', {'materiales': Material.objects.all()})

@login_required
def prestamos(request):
    return render(request, 'prestamos.html', {'prestamos': Prestamo.objects.filter(fecha_prestamo__date=date.today()).order_by('-id')})

# --- ACCESO SECRETO ADMIN ---
def acceso_admin_secreto(request):
    if request.method == 'POST':
        if request.POST.get('clave', '').lower() == 'extra2026':
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                login(request, admin_user)
                return redirect(request.GET.get('next', '/admin/'))
    return render(request, 'login_admin.html')

# --- APIS (RECONOCIMIENTO FACIAL) ---
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
            
            # Lógica simple de comparación
            mejor_match = None
            for p in prestadores:
                if p.datos_faciales:
                    descriptor_db = json.loads(p.datos_faciales)
                    distancia = math.sqrt(sum((a - b) ** 2 for a, b in zip(descriptor_recibido, descriptor_db)))
                    if distancia < 0.6:
                        mejor_match = p
                        break
            
            if mejor_match:
                AsistenciaServicio.objects.create(prestador=mejor_match, tipo='Entrada')
                return JsonResponse({'status': 'success', 'mensaje': f'Bienvenido {mejor_match.nombre_completo}'})
            return JsonResponse({'status': 'error', 'mensaje': 'Rostro no reconocido'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=400)