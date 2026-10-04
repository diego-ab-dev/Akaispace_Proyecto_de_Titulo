"""Reclamos del cliente sobre sus compras."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from appPrincipal.models import Reclamo, Venta


@login_required
def crear_reclamo(request, compra_id):
    usuario = request.user
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)

    if request.method == 'POST':
        asunto = request.POST.get('asunto', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()

        MAX_LENGTH_ASUNTO = 50

        if not asunto or not descripcion:
            return render(request, 'crear_reclamo.html', {
                'compra': compra,
                'error': "Todos los campos son obligatorios."
            })
        
        if len(asunto) > MAX_LENGTH_ASUNTO:
            return render(request, 'crear_reclamo.html', {
                'compra': compra,
                'error': f"El Asunto no puede exceder los {MAX_LENGTH_ASUNTO} caracteres."
            })
        
        else:
            Reclamo.objects.create(
                usuario=usuario,
                venta=compra,
                asunto=asunto,
                descripcion=descripcion
            )
            return redirect('/perfil?notif=Reclamo+enviado+con+éxito&type=success')

    return render(request, 'crear_reclamo.html', {
        'compra': compra
    })


@login_required
def lista_reclamos(request):
    usuario = request.user
    todos_reclamos = Reclamo.objects.filter(usuario=usuario).order_by('-id')

    paginator = Paginator(todos_reclamos, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lista_reclamos.html', {
        'todos_reclamos': todos_reclamos,
        'page_obj': page_obj,
    })

@login_required
def ver_detalle_reclamo(request, reclamo_id):
    usuario = request.user
    
    reclamo = get_object_or_404(Reclamo, id=reclamo_id, usuario=usuario)
    
    return render(request, 'detalle_reclamo.html', {
        'reclamo': reclamo
    })
