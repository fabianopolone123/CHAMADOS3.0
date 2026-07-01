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


class AberturaChamadoForm(forms.ModelForm):
    class Meta:
        model = Chamado
        fields = ["titulo", "categoria", "prioridade", "descricao"]
        widgets = {
            "titulo": forms.TextInput(
                attrs={
                    "class": "form-control form-control-lg",
                    "placeholder": "Resuma o problema em uma frase",
                    "maxlength": 255,
                }
            ),
            "categoria": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex.: Acesso, E-mail, Impressao",
                }
            ),
            "prioridade": forms.Select(attrs={"class": "form-select"}),
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
            "categoria": "Categoria",
            "prioridade": "Prioridade",
            "descricao": "Descricao",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["prioridade"].choices = [
            ("", "Selecione a prioridade"),
            *Chamado.PRIORIDADE_CHOICES,
        ]
        self.fields["prioridade"].initial = Chamado.PRIORIDADE_MEDIA
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
