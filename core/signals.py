"""Signals do app core.

Limpeza de arquivos orfaos do modulo Requisicoes (nomes tecnicos internos com
prefixo `Contrato`): ao excluir uma requisicao, o cascade (`on_delete=CASCADE`)
apaga os orcamentos, suborcamentos e seus documentos no banco. Estes signals
`post_delete` removem do disco (MEDIA_ROOT) os arquivos vinculados a cada
registro apagado (fotos de produto e documentos anexos), evitando arquivos
orfaos. Tambem cobre exclusoes parciais (um orcamento/suborcamento/documento
apagado isoladamente).
"""

from __future__ import annotations

import os

from django.conf import settings
from django.db.models import FileField
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import (
    OrcamentoContrato,
    OrcamentoDocumento,
    SuborcamentoContrato,
    SuborcamentoDocumento,
)


def _remover_diretorios_vazios(caminho: str) -> None:
    """Remove diretorios vazios subindo a partir de `caminho`, sem nunca
    ultrapassar (nem apagar) o proprio MEDIA_ROOT."""
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    atual = os.path.abspath(caminho)
    while atual.startswith(media_root) and atual != media_root:
        try:
            if os.listdir(atual):
                break
            os.rmdir(atual)
        except OSError:
            break
        atual = os.path.dirname(atual)


def _remover_arquivos_do_instance(instance) -> None:
    """Apaga do disco todos os arquivos (FileField/ImageField) da instancia e
    limpa os diretorios que ficarem vazios."""
    diretorios: set[str] = set()
    for field in instance._meta.get_fields():
        if isinstance(field, FileField):
            arquivo = getattr(instance, field.name, None)
            if arquivo and arquivo.name:
                try:
                    diretorios.add(os.path.dirname(arquivo.path))
                except (ValueError, NotImplementedError):
                    # Storage sem caminho local: apenas apaga via storage.
                    pass
                # save=False: o registro ja foi (ou esta sendo) excluido.
                arquivo.delete(save=False)
    for diretorio in diretorios:
        _remover_diretorios_vazios(diretorio)


@receiver(post_delete, sender=OrcamentoContrato)
@receiver(post_delete, sender=OrcamentoDocumento)
@receiver(post_delete, sender=SuborcamentoContrato)
@receiver(post_delete, sender=SuborcamentoDocumento)
def remover_arquivos_contratos(sender, instance, **kwargs) -> None:
    _remover_arquivos_do_instance(instance)
