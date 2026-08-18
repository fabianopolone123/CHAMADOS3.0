"""Context processors globais dos templates."""
from .menu import itens_menu_ti
from .permissions import is_admin_user, is_attendant_user, is_titular_user


def ti_flags(request):
    """Disponibiliza em todos os templates:

    - `is_ti_user`: liga as notificacoes em tempo real apenas para a TI;
    - `is_titular_user`: mostra o botao do Painel do Titular ao lado da marca;
    - `menu_itens`: o menu lateral de TI ja resolvido (rotulo, ordem e
      visibilidade conforme o Painel), consultado so para quem ve o menu.
    """
    user = getattr(request, "user", None)
    is_ti = bool(user and user.is_authenticated and (is_admin_user(user) or is_attendant_user(user)))
    contexto = {"is_ti_user": is_ti, "is_titular_user": is_titular_user(user)}
    if is_ti:
        contexto["menu_itens"] = itens_menu_ti()
    return contexto
