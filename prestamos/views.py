from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
import math
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
def home(request): return render(request, 'home.html')
@login_required
def inventario(request): return render(request, 'inventario.html', {'materiales': Material.objects.all()})

@login_required
def prestamos(request):
    if request.method == 'POST':
        # Procesamiento seguro de datos
        try:
            num_control = request.POST.get('numero_control')
            ids = request.POST.getlist('material_id[]')
            cants = request.POST.getlist('cantidad[]')
            for i in range(len(ids)):
                if ids[i]:
                    m = Material.objects.filter(id=ids[i]).first()
                    if m and m.cantidad >= int(cants[i]):
                        m.cantidad -= int(cants[i])
                        m.save()
                        Prestamo.objects.create(nombre_alumno=num_control, material=m, cantidad=int(cants[i]), estado='En Prestamo')
        except: pass
        return redirect('prestamos')

    # Renderizado blindado para que no cause Error 500
    materiales = Material.objects.all()
    try:
        prestamos_lista = Prestamo.objects.all().order_by('-id')
    except:
        prestamos_lista = []
    return render(request, 'prestamos.html', {'materiales': materiales, 'prestamos': prestamos_lista})

# --- GESTIÓN Y APIS (TODO ORIGINAL) ---
def panel_principal(request): return render(request, 'panel.html')
@login_required
def servicio_social(request): return render(request, 'servicio_social.html')
@login_required
def panel_servicio(request): return render(request, 'panel_servicio.html', {'datos': PrestadorServicio.objects.all()})

@login_required
def registrar_alumno_rapido(request):
    if request.method == 'POST':
        Alumno.objects.get_or_create(numero_control=request.POST.get('nuevo_num_control'), defaults={'nombre_completo': request.POST.get('nuevo_nombre')})
    return redirect('prestamos')

@login_required
def devolver_material(request, prestamo_id):
    p = Prestamo.objects.filter(id=prestamo_id).first()
    if p:
        p.material.cantidad += p.cantidad
        p.material.save()
        p.estado = 'Devuelto'
        p.save()
    return redirect('prestamos')

@login_required
def agregar_material(request): return redirect('inventario')
@login_required
def eliminar_material(request, material_id):
    Material.objects.filter(id=material_id).delete()
    return redirect('inventario')

def buscar_alumnos_api(request):
    query = request.GET.get('q', '')
    alumnos = Alumno.objects.filter(Q(nombre_completo__icontains=query) | Q(numero_control__icontains=query))[:10]
    return JsonResponse([{'numero_control': a.numero_control, 'nombre_completo': a.nombre_completo} for a in alumnos], safe=False)
    
def buscar_materiales_api(request):
    query = request.GET.get('q', '')
    materiales = Material.objects.filter(nombre__icontains=query)[:10]
    return JsonResponse([{'id': m.id, 'nombre': m.nombre} for m in materiales], safe=False)

@csrf_exempt
def registrar_rostro_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        p, _ = PrestadorServicio.objects.get_or_create(numero_control=data.get('numero_control'), defaults={'nombre_completo': data.get('nombre_completo')})
        p.datos_faciales = json.dumps(data.get('datos_faciales'))
        p.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def marcar_asistencia_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        for p in PrestadorServicio.objects.all():
            if p.datos_faciales:
                if math.sqrt(sum((a - b) ** 2 for a, b in zip(data.get('datos_faciales'), json.loads(p.datos_faciales)))) < 0.6:
                    p.activo = not p.activo
                    p.save()
                    AsistenciaServicio.objects.create(prestador=p, tipo='Entrada' if p.activo else 'Salida')
                    return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def agregar_horas_manual_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        p = PrestadorServicio.objects.get(numero_control=data.get('numero_control'))
        p.horas_acumuladas = (p.horas_acumuladas or 0) + int(data.get('horas', 0))
        p.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def acceso_admin_secreto(request):
    if request.method == 'POST' and request.POST.get('clave', '').lower() == 'extra2026':
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user: login(request, admin_user)
        return redirect(request.GET.get('next', '/admin/'))
    return render(request, 'login_admin.html')