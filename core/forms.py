from django import forms

from .models import Chamado


class LoginForm(forms.Form):
    username = forms.CharField(
        label="Usuario",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Digite seu usuario",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Digite sua senha",
                "autocomplete": "current-password",
            }
        ),
    )


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Campo de arquivo que aceita multiplos anexos, sem limite de tamanho ou extensao."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"class": "form-control", "multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        if data in self.empty_values:
            return []
        return [single_clean(data, initial)]


class AberturaChamadoForm(forms.ModelForm):
    anexos = MultipleFileField(
        label="Anexos",
        required=False,
        help_text="Voce pode anexar um ou mais arquivos (opcional).",
    )

    class Meta:
        model = Chamado
        fields = ["titulo", "descricao"]
        widgets = {
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Resuma o problema em uma frase",
                    "maxlength": 255,
                }
            ),
            "descricao": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 6,
                    "placeholder": "Descreva com detalhes o que esta acontecendo, mensagens de erro e passos ja tentados.",
                }
            ),
        }
        labels = {
            "titulo": "Titulo",
            "descricao": "Descricao",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["descricao"].required = True

    def clean_titulo(self):
        titulo = (self.cleaned_data.get("titulo") or "").strip()
        if len(titulo) < 5:
            raise forms.ValidationError("Descreva o titulo com pelo menos 5 caracteres.")
        return titulo

    def clean_descricao(self):
        descricao = (self.cleaned_data.get("descricao") or "").strip()
        if len(descricao) < 10:
            raise forms.ValidationError("Detalhe melhor o chamado com pelo menos 10 caracteres.")
        return descricao


class MensagemChamadoForm(forms.Form):
    """Mensagem da conversa do chamado, com anexos opcionais.

    Regra: e obrigatorio informar um texto OU pelo menos um anexo (nao permite
    mensagem completamente vazia).
    """

    texto = forms.CharField(
        label="Mensagem",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Escreva uma mensagem para a equipe...",
            }
        ),
    )
    anexos = MultipleFileField(
        label="Anexos",
        required=False,
        help_text="Voce pode anexar um ou mais arquivos (opcional).",
    )

    def clean(self):
        cleaned = super().clean()
        texto = (cleaned.get("texto") or "").strip()
        anexos = cleaned.get("anexos") or []
        if not texto and not anexos:
            raise forms.ValidationError("Escreva uma mensagem ou anexe ao menos um arquivo.")
        cleaned["texto"] = texto
        return cleaned
