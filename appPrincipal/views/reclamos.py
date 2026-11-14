"""Reclamos del cliente sobre sus compras."""
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from appPrincipal.forms import ReclamoForm
from appPrincipal.decorators import solo_clientes
from appPrincipal.models import Reclamo, Venta


@login_required
@solo_clientes
def crear_reclamo(request, compra_id):
    usuario = request.user
    compra = get_object_or_404(Venta, id=compra_id, usuario=usuario)
    form = ReclamoForm()

    if request.method == 'POST':
        form = ReclamoForm(request.POST)
        if form.is_valid():
            Reclamo.objects.create(usuario=usuario, venta=compra, **form.cleaned_data)
            return redirect('/perfil?notif=Reclamo+enviado+con+éxito&type=success')

    return render(request, 'crear_reclamo.html', {'compra': compra, 'form': form})


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
