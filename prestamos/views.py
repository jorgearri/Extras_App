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
# ¡IMPORTANTE! Se añadió RegistroServicio al import
from .models import Material, Prestamo, Alumno, PrestadorServicio, AsistenciaServicio, RegistroServicio 

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
            num_control = request.POST.get('numero_control')
            material_ids = request.POST.getlist('material_id[]')
            cantidades = request.POST.getlist('cantidad[]')

            alumno_obj = Alumno.objects.filter(numero_control=num_control).first()

            for i in range(len(material_ids)):
                m_id = material_ids[i]
                cant = cantidades[i]

                if m_id and cant:
                    material = Material.objects.filter(id=m_id).first()

                    if material and material.cantidad >= int(cant):
                        material.cantidad -= int(cant)
                        material.save()

                        try:
                            Prestamo.objects.create(alumno=alumno_obj, material=material, cantidad=int(cant), estado='En Prestamo')
                        except TypeError:
                            try:
                                Prestamo.objects.create(nombre_alumno=alumno_obj.nombre_completo if alumno_obj else num_control, material=material, cantidad=int(cant))
                            except TypeError:
                                Prestamo.objects.create(alumno=alumno_obj, material=material, cantidad=int(cant))
        except Exception as e:
            pass 

        return redirect('prestamos')

    # --- LÓGICA DEL CALENDARIO AÑADIDA ---
    materiales_disponibles = Material.objects.filter(cantidad__gt=0)
    fecha_busqueda = request.GET.get('fecha_busqueda') # Captura la fecha del calendario

    if fecha_busqueda:
        # Si elegiste una fecha, filtra por ese día exacto
        prestamos_activos = Prestamo.objects.filter(fecha=fecha_busqueda).order_by('-id')
    else:
        # Si no, muestra los normales
        try:
            prestamos_activos = Prestamo.objects.exclude(estado='Devuelto').order_by('-id')
        except:
            prestamos_activos = Prestamo.objects.all().order_by('-id')

    return render(request, 'prestamos.html', {
        'materiales': materiales_disponibles,
        'prestamos': prestamos_activos,
        'fecha_seleccionada': fecha_busqueda # Para que el calendario no se borre al recargar
    })

def panel_principal(request): 
    return render(request, 'panel.html')

@login_required
def servicio_social(request): 
    return render(request, 'servicio_social.html')

@login_required
def panel_servicio(request):
    prestadores = PrestadorServicio.objects.all()
    for p in prestadores:
        # Buscamos el Alumno asociado para acceder al RegistroServicio
        alumno = Alumno.objects.filter(numero_control=p.numero_control).first()
        total_minutos = 0
        if alumno:
            registro, _ = RegistroServicio.objects.get_or_create(alumno=alumno)
            total_minutos = registro.horas_acumuladas # Lo usamos como minutos totales
        
        # Le pegamos las horas y minutos calculados para que el HTML los pueda leer
        p.horas_calculadas = total_minutos // 60
        p.minutos_calculados = total_minutos % 60
        
    return render(request, 'panel_servicio.html', {'datos': prestadores})

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
    try:
        prestamo.estado = 'Devuelto'
    except:
        pass
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
                    return JsonResponse({'status': 'success', 'mensaje': f'Salida registrada para {mejor_match.nombre_completo}'})
                else:
                    AsistenciaServicio.objects.create(prestador=mejor_match, tipo='Entrada')
                    mejor_match.activo = True
                    mejor_match.save()
                    return JsonResponse({'status': 'success', 'mensaje': f'Entrada registrada para {mejor_match.nombre_completo}'})
                    
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
            horas_nuevas = int(data.get('horas', 0))
            minutos_nuevos = int(data.get('minutos', 0))

            # Buscamos o creamos al Alumno
            alumno, created = Alumno.objects.get_or_create(numero_control=no_control, defaults={'nombre_completo': 'Prestador'})
            if created:
                p_existente = PrestadorServicio.objects.filter(numero_control=no_control).first()
                if p_existente:
                    alumno.nombre_completo = p_existente.nombre_completo
                    alumno.save()

            # Guardamos todo en minutos en el campo horas_acumuladas
            registro, _ = RegistroServicio.objects.get_or_create(alumno=alumno)
            minutos_totales_a_sumar = (horas_nuevas * 60) + minutos_nuevos
            registro.horas_acumuladas += minutos_totales_a_sumar
            registro.save()

            return JsonResponse({'status': 'success', 'mensaje': f'Agregados {horas_nuevas}h {minutos_nuevos}m con éxito.'})
            
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