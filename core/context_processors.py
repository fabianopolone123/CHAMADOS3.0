"""Context processors globais dos templates."""
from .permissions import is_admin_user, is_attendant_user


def ti_flags(request):
    """Disponibiliza `is_ti_user` em todos os templates (usado para ligar as
    notificacoes em tempo real apenas para a equipe de TI)."""
    user = getattr(request, "user", None)
    is_ti = bool(user and user.is_authenticated and (is_admin_user(user) or is_attendant_user(user)))
    return {"is_ti_user": is_ti}
