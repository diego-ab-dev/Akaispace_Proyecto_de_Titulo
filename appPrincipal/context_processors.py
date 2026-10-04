def usuario_context(request):
    # los templates usan {{ usuario }}: es el usuario autenticado, o None si no inició sesión
    usuario = request.user if request.user.is_authenticated else None
    return {'usuario': usuario}
