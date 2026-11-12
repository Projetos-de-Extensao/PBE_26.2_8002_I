from datetime import date, datetime, time, timedelta
import re

from django.apps import apps
from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import URLPattern, URLResolver, get_resolver, reverse, reverse_lazy
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from agendamento.models import (
    Agendamento,
    Cliente,
    DIAS_SEMANA,
    Perfil,
    Profissional,
    Recepcionista,
    Recorrencia,
    Recurso,
    Sala,
    Servico,
    Usuario,
    horarios_livres,
)


def api_index(request):
    """Documenta os endpoints do sistema que retornam JSON."""
    return JsonResponse(
        {
            "nome": "API Equilibra",
            "descricao": "Endpoints JSON disponíveis no sistema de agendamento.",
            "base_url": request.build_absolute_uri("/"),
            "autenticacao": (
                "As operações exigem sessão autenticada. Requisições POST também "
                "precisam do token CSRF."
            ),
            "endpoints": [
                {
                    "nome": "Prévia de agendamento recorrente",
                    "metodo": "POST",
                    "caminho": "/agendar/{servico_id}/previa-recorrencia/",
                    "acesso": "Requer login como cliente.",
                    "content_type": "application/x-www-form-urlencoded",
                    "parametros": {
                        "horario": "Obrigatório; horário ISO escolhido no formulário.",
                        "data_termino": "Obrigatório; data final no formato AAAA-MM-DD.",
                        "dias_semana": "Opcional; dias da semana selecionados.",
                        "sala": "Opcional; ID da sala.",
                        "recursos": "Opcional; IDs dos equipamentos.",
                    },
                    "resposta_sucesso": (
                        "JSON com valido, total, total_validas, total_conflitos "
                        "e sessoes."
                    ),
                },
                {
                    "nome": "Consultar horários para reagendamento",
                    "metodo": "GET",
                    "caminho": "/agendamentos/{pk}/horarios/?data=AAAA-MM-DD",
                    "acesso": "Requer login e permissão sobre o agendamento.",
                    "parametros": {
                        "data": "Obrigatório; data consultada no formato AAAA-MM-DD."
                    },
                    "resposta_sucesso": (
                        "JSON com horarios, data e duracao_minutos."
                    ),
                },
                {
                    "nome": "Reagendar atendimento",
                    "metodo": "POST",
                    "caminho": "/agendamentos/{pk}/reagendar/",
                    "acesso": "Requer login e permissão sobre o agendamento.",
                    "content_type": "application/x-www-form-urlencoded",
                    "parametros": {
                        "data": "Obrigatório; nova data no formato AAAA-MM-DD.",
                        "hora_inicio": "Obrigatório; novo horário no formato HH:MM.",
                    },
                    "resposta_sucesso": (
                        "JSON com ok, data, hora_inicio e hora_fim."
                    ),
                },
            ],
        }
    )


def api_schema(request):
    """Publica o schema OpenAPI usado pela interface Swagger."""
    session_security = [{"sessao": []}]
    post_security = [{"sessao": [], "csrf": []}]
    schema = {
            "openapi": "3.0.3",
            "info": {
                "title": "API Equilibra",
                "version": "1.0.0",
                "description": (
                    "Endpoints JSON de agendamento. As rotas exigem sessão "
                    "autenticada; operações POST também exigem token CSRF."
                ),
            },
            "tags": [
                {
                    "name": "Profissionais",
                    "description": (
                        "Rotas do perfil e da agenda profissional. Modelo principal: "
                        "`Profissional`."
                    ),
                },
                {
                    "name": "Alunos (Clientes)",
                    "description": (
                        "Cadastro, perfil e agendamentos do aluno/cliente. Modelos "
                        "principais: `Cliente`, `Usuario` e `Agendamento`."
                    ),
                },
                {
                    "name": "Recepção",
                    "description": (
                        "Operações realizadas por recepcionistas. Modelo principal: "
                        "`Recepcionista`."
                    ),
                },
                {
                    "name": "Administração",
                    "description": (
                        "Gerenciamento dos modelos `Servico`, `Sala`, `Recurso` e "
                        "demais dados administrativos."
                    ),
                },
                {
                    "name": "Administração Django",
                    "description": "Rotas internas do admin Django; não são endpoints REST.",
                },
                {
                    "name": "Sistema",
                    "description": "Autenticação, recuperação de senha e documentação.",
                },
            ],
            "servers": [{"url": request.build_absolute_uri("/").rstrip("/")}],
            "components": {
                "securitySchemes": {
                    "sessao": {
                        "type": "apiKey",
                        "in": "cookie",
                        "name": "sessionid",
                        "description": "Cookie de sessão obtido ao fazer login.",
                    },
                    "csrf": {
                        "type": "apiKey",
                        "in": "header",
                        "name": "X-CSRFToken",
                        "description": (
                            "Token CSRF do cookie csrftoken, necessário em POST."
                        ),
                    },
                }
            },
            "paths": {
                "/agendar/{servico_id}/previa-recorrencia/": {
                    "post": {
                        "operationId": "previewRecurringAppointments",
                        "tags": ["Alunos (Clientes)"],
                        "summary": "Prévia de agendamento recorrente",
                        "description": "Avalia as datas da recorrência sem salvar agendamentos.",
                        "security": post_security,
                        "parameters": [
                            {
                                "name": "servico_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/x-www-form-urlencoded": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["horario", "data_termino"],
                                        "properties": {
                                            "horario": {
                                                "type": "string",
                                                "description": "Horário ISO disponibilizado pelo sistema.",
                                            },
                                            "data_termino": {
                                                "type": "string",
                                                "format": "date",
                                            },
                                            "dias_semana": {
                                                "type": "array",
                                                "items": {"type": "integer"},
                                                "description": "Dias selecionados: 0 (segunda-feira) a 6 (domingo).",
                                            },
                                            "sala": {"type": "integer"},
                                            "recursos": {
                                                "type": "array",
                                                "items": {"type": "integer"},
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Prévia calculada.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "valido": {"type": "boolean"},
                                                "total": {"type": "integer"},
                                                "total_validas": {"type": "integer"},
                                                "total_conflitos": {"type": "integer"},
                                                "sessoes": {
                                                    "type": "array",
                                                    "items": {"type": "object"},
                                                },
                                            },
                                        }
                                    }
                                },
                            },
                            "400": {"description": "Dados inválidos ou recorrência incompatível."},
                            "403": {"description": "Usuário não tem perfil de cliente."},
                        },
                    }
                },
                "/agendamentos/{pk}/horarios/": {
                    "get": {
                        "operationId": "getRescheduleSlots",
                        "tags": ["Alunos (Clientes)"],
                        "summary": "Consultar horários para reagendamento",
                        "security": session_security,
                        "parameters": [
                            {
                                "name": "pk",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            },
                            {
                                "name": "data",
                                "in": "query",
                                "required": True,
                                "schema": {"type": "string", "format": "date"},
                            },
                        ],
                        "responses": {
                            "200": {
                                "description": "Horários livres na data.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "horarios": {
                                                    "type": "array",
                                                    "items": {"type": "string"},
                                                },
                                                "data": {"type": "string", "format": "date"},
                                                "duracao_minutos": {"type": "integer"},
                                            },
                                        }
                                    }
                                },
                            },
                            "400": {"description": "Data ausente, inválida ou agendamento não reagendável."},
                            "404": {"description": "Agendamento não encontrado ou sem permissão."},
                        },
                    }
                },
                "/agendamentos/{pk}/reagendar/": {
                    "post": {
                        "operationId": "rescheduleAppointment",
                        "tags": ["Alunos (Clientes)"],
                        "summary": "Reagendar atendimento",
                        "security": post_security,
                        "parameters": [
                            {
                                "name": "pk",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "integer"},
                            }
                        ],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/x-www-form-urlencoded": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["data", "hora_inicio"],
                                        "properties": {
                                            "data": {
                                                "type": "string",
                                                "format": "date",
                                            },
                                            "hora_inicio": {
                                                "type": "string",
                                                "format": "time",
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "Agendamento reagendado.",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "ok": {"type": "boolean"},
                                                "data": {"type": "string"},
                                                "hora_inicio": {"type": "string"},
                                                "hora_fim": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            },
                            "400": {"description": "Dados inválidos, conflito ou agendamento não reagendável."},
                            "404": {"description": "Agendamento não encontrado ou sem permissão."},
                        },
                    }
                },
            },
        }
    paths = _openapi_paths()
    paths.update(schema["paths"])
    schema["paths"] = paths
    schema["components"]["schemas"] = _model_schemas()
    return JsonResponse(schema)


def _openapi_paths():
    """Converte todas as rotas Django registradas em operações OpenAPI."""
    paths = {}
    supported_methods = ("get", "post")
    json_views = {
        "api_index",
        "api_schema",
        "PreviaRecorrenciaView",
        "HorariosReagendamentoView",
        "ReagendarAgendamentoView",
    }

    def route_string(pattern):
        route_pattern = pattern.pattern
        if hasattr(route_pattern, "_route"):
            return route_pattern._route
        route = route_pattern.regex.pattern.lstrip("^")
        if route.endswith("$"):
            route = route[:-1]
        return re.sub(r"\(\?P<([a-zA-Z_][a-zA-Z0-9_]*)>[^)]+\)", r"{\1}", route)

    def add_routes(patterns, prefix=""):
        for pattern in patterns:
            route = prefix + route_string(pattern)
            if isinstance(pattern, URLResolver):
                add_routes(pattern.url_patterns, route)
                continue
            if not isinstance(pattern, URLPattern):
                continue

            path = "/" + re.sub(
                r"<(?:(?:[a-zA-Z_][a-zA-Z0-9_]*):)?([a-zA-Z_][a-zA-Z0-9_]*)>",
                r"{\1}",
                route,
            )
            callback = pattern.callback
            view_class = getattr(callback, "view_class", None)
            if view_class is not None:
                methods = [
                    method
                    for method in supported_methods
                    if method in view_class.http_method_names
                    and callable(getattr(view_class, method, None))
                ]
                view_name = view_class.__name__
            else:
                view_name = getattr(callback, "__name__", "view")
                if route.startswith("admin/"):
                    admin_methods = {
                        "index": ("get",),
                        "login": ("get", "post"),
                        "logout": ("post",),
                        "password_change": ("get", "post"),
                        "password_change_done": ("get",),
                        "autocomplete_view": ("get",),
                        "i18n_javascript": ("get",),
                        "shortcut": ("get",),
                        "user_change_password": ("get", "post"),
                        "changelist_view": ("get", "post"),
                        "add_view": ("get", "post"),
                        "history_view": ("get",),
                        "delete_view": ("get", "post"),
                        "change_view": ("get", "post"),
                        "app_index": ("get",),
                        "catch_all_view": ("get",),
                    }
                    view_name = getattr(callback, "__qualname__", view_name).split(".")[-1]
                    methods = list(admin_methods.get(view_name, ("get",)))
                else:
                    methods = ["get"]

            if not methods:
                methods = ["get"]
            endpoint_name = pattern.name or view_name
            if route.startswith("admin/"):
                tag = "Administração Django"
            elif route.startswith("administracao/profissionais/"):
                tag = "Profissionais"
            elif route.startswith("administracao/"):
                tag = "Administração"
            elif route.startswith("profissional/") or route.startswith("profissionais/"):
                tag = "Profissionais"
            elif route.startswith(
                ("agendar/", "minha-agenda/", "agendamentos/", "cadastrar/", "perfil/")
            ):
                tag = "Alunos (Clientes)"
            elif route.startswith("recepcao/"):
                tag = "Recepção"
            else:
                tag = "Sistema"
            is_json = view_name in json_views or endpoint_name in json_views
            requires_session = not (
                route in ("", "api/", "api/schema/", "docs/", "cadastrar/")
                or route.startswith("senha/redefinir")
            )

            path_item = paths.setdefault(path, {})
            path_parameters = [
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string" if converter == "path" else "integer"},
                }
                for converter, name in re.findall(
                    r"<(?:(\w+):)?(\w+)>", route
                )
            ]
            path_parameters.extend(
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
                for name in re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", route)
                if name not in {parameter["name"] for parameter in path_parameters}
            )
            query_parameters = {
                "profissionais/": [
                    ("especialidade", "string"),
                    ("servico", "string"),
                    ("modalidade", "string"),
                ],
                "recepcao/agenda/": [("dia", "string", "date")],
                "minha-agenda/": [
                    ("data_inicio", "string", "date"),
                    ("data_fim", "string", "date"),
                ],
                "agendamentos/<int:pk>/horarios/": [
                    ("data", "string", "date"),
                ],
            }.get(route, [])
            for parameter in query_parameters:
                name, value_type = parameter[:2]
                item = {
                    "name": name,
                    "in": "query",
                    "required": False,
                    "schema": {"type": value_type},
                }
                if len(parameter) == 3:
                    item["schema"]["format"] = parameter[2]
                    item["required"] = True
                path_parameters.append(item)
            for method in methods:
                operation = {
                    "tags": [tag],
                    "summary": endpoint_name.replace("_", " "),
                    "operationId": re.sub(
                        r"[^a-zA-Z0-9_]",
                        "_",
                        f"{route}_{endpoint_name}_{method}",
                    ),
                    "description": (
                        f"Rota Django `{route}`. "
                        + (
                            "Retorna dados JSON."
                            if is_json
                            else "Rota do sistema web; retorna uma página HTML ou redireciona."
                        )
                    ),
                    "parameters": path_parameters,
                    "responses": {
                        "200": {
                            "description": (
                                "Resposta JSON."
                                if is_json
                                else "Página HTML ou redirecionamento."
                            ),
                            "content": {
                                ("application/json" if is_json else "text/html"): {
                                    "schema": (
                                        {"type": "object"}
                                        if is_json
                                        else {"type": "string"}
                                    )
                                }
                            },
                        }
                    },
                }
                if route == "cadastrar/" and method == "post":
                    operation["summary"] = "Criar conta"
                    operation["description"] = (
                        "Envia o formulário de cadastro do sistema web. A conta é "
                        "criada e a sessão é iniciada automaticamente. Não é uma "
                        "resposta JSON."
                    )
                    operation["security"] = [{"csrf": []}]
                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                    "required": [
                                        "nome",
                                        "email",
                                        "papel",
                                        "senha",
                                        "confirmar_senha",
                                    ],
                                    "properties": {
                                        "nome": {
                                            "type": "string",
                                            "maxLength": 150,
                                        },
                                        "email": {
                                            "type": "string",
                                            "format": "email",
                                        },
                                        "papel": {
                                            "type": "string",
                                            "enum": [
                                                "cliente",
                                                "profissional",
                                                "recepcionista",
                                            ],
                                            "default": "cliente",
                                        },
                                        "especialidade": {
                                            "type": "string",
                                            "maxLength": 150,
                                            "description": (
                                                "Obrigatória se papel=profissional."
                                            ),
                                        },
                                        "modalidade": {
                                            "type": "string",
                                            "enum": [
                                                "presencial",
                                                "online",
                                                "hibrido",
                                            ],
                                            "description": (
                                                "Obrigatória se papel=profissional."
                                            ),
                                        },
                                        "senha": {
                                            "type": "string",
                                            "format": "password",
                                        },
                                        "confirmar_senha": {
                                            "type": "string",
                                            "format": "password",
                                        },
                                    },
                                }
                            }
                        },
                    }
                elif route == "" and method == "post":
                    operation["summary"] = "Entrar na conta"
                    operation["description"] = (
                        "Autentica com e-mail e senha pelo formulário do sistema. "
                        "O campo do e-mail chama-se `username` no formulário Django. "
                        "Ao sucesso, cria a sessão e redireciona; não retorna JSON."
                    )
                    operation["security"] = [{"csrf": []}]
                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/x-www-form-urlencoded": {
                                "schema": {
                                    "type": "object",
                                    "required": ["username", "password"],
                                    "properties": {
                                        "username": {
                                            "type": "string",
                                            "format": "email",
                                            "description": "E-mail cadastrado.",
                                        },
                                        "password": {
                                            "type": "string",
                                            "format": "password",
                                        },
                                    },
                                }
                            }
                        },
                    }
                elif route == "perfil/" and method == "post":
                    operation["summary"] = "Atualizar perfil"
                    operation["description"] = (
                        "Atualiza o nome e telefone; para profissional também "
                        "especialidade e apresentação. Formulário HTML Django."
                    )
                    operation["requestBody"] = _form_request_body(
                        {
                            "nome": ("string", True),
                            "telefone": ("string", False),
                            "especialidade": ("string", False),
                            "apresentacao": ("string", False),
                        }
                    )
                elif route == "profissional/disponibilidade/" and method == "post":
                    operation["summary"] = "Cadastrar disponibilidade profissional"
                    operation["requestBody"] = _form_request_body(
                        {
                            "dia_semana": ("integer", True, list(range(7))),
                            "hora_inicio": ("string", True, "time"),
                            "hora_fim": ("string", True, "time"),
                        }
                    )
                elif route == "profissional/bloqueios/novo/" and method == "post":
                    operation["summary"] = "Criar bloqueio de horário"
                    operation["requestBody"] = _form_request_body(
                        {
                            "data": ("string", True, "date"),
                            "hora_inicio": ("string", True, "time"),
                            "hora_fim": ("string", True, "time"),
                            "motivo": ("string", True),
                            "confirmar": ("string", False, ["1"]),
                            "origem": ("string", False),
                        }
                    )
                elif route == "minha-agenda/<int:pk>/cancelar/" and method == "post":
                    operation["summary"] = "Cancelar atendimento"
                    operation["description"] = (
                        "Cancela uma ocorrência ou, com escopo=serie, as sessões "
                        "futuras ativas da recorrência. Formulário HTML Django."
                    )
                    operation["requestBody"] = _form_request_body(
                        {
                            "escopo": ("string", False, ["ocorrencia", "serie"]),
                            "origem": ("string", False),
                        }
                    )
                elif method == "post" and view_class is not None:
                    form_class = getattr(view_class, "form_class", None)
                    form_fields = getattr(form_class, "base_fields", None)
                    if form_fields:
                        operation["requestBody"] = _form_request_body(
                            {
                                field_name: _openapi_form_field(field)
                                for field_name, field in form_fields.items()
                            }
                        )
                if method == "post" and "requestBody" not in operation:
                    if route.startswith("admin/"):
                        operation["description"] += (
                            " O Django Admin processa formulários HTML próprios, "
                            "com campos variáveis; esta rota não é destinada ao "
                            "envio pelo Swagger."
                        )
                        operation["x-html-form-route"] = True
                    else:
                        operation["description"] += (
                            " Não requer campos adicionais no corpo da requisição; "
                            "os dados necessários estão no caminho ou são enviados "
                            "pelo token CSRF."
                        )
                        operation["x-no-request-body"] = True
                if requires_session:
                    operation.setdefault(
                        "security",
                        [
                            {
                                "sessao": [],
                                **({"csrf": []} if method != "get" else {}),
                            }
                        ],
                    )
                path_item[method] = operation

    add_routes(get_resolver().url_patterns)
    return paths


def _openapi_form_field(field):
    """Converte um campo Django Form em tipo e obrigatoriedade OpenAPI."""
    if isinstance(field, forms.ModelMultipleChoiceField):
        return ("array", field.required, None, "integer")
    if isinstance(field, forms.MultipleChoiceField):
        choices = [value for value, _label in field.choices if value != ""]
        return ("array", field.required, choices, "string")
    if isinstance(field, forms.ModelChoiceField):
        return ("integer", field.required)
    if isinstance(field, forms.BooleanField):
        return ("boolean", field.required)
    if isinstance(field, forms.DateTimeField):
        return ("string", field.required, "date-time")
    if isinstance(field, forms.DateField):
        return ("string", field.required, "date")
    if isinstance(field, forms.TimeField):
        return ("string", field.required, "time")
    if isinstance(field, forms.EmailField):
        return ("string", field.required, "email")
    if isinstance(field, forms.IntegerField):
        return ("integer", field.required)
    if isinstance(field, forms.DecimalField):
        return ("number", field.required)
    if isinstance(field, forms.ChoiceField):
        choices = [value for value, _label in field.choices if value != ""]
        return ("string", field.required, choices)
    if isinstance(field, forms.FileField):
        return ("string", field.required, "binary")
    if getattr(field.widget, "input_type", None) == "password":
        return ("string", field.required, "password")
    return ("string", field.required)


def _form_request_body(fields):
    properties = {}
    required = []
    for name, definition in fields.items():
        value_type, is_required, *details = definition
        if value_type == "array":
            item_type = details[1] if len(details) > 1 and details[1] else "string"
            property_schema = {
                "type": "array",
                "items": {"type": item_type},
            }
            if details and details[0]:
                property_schema["items"]["enum"] = details[0]
        else:
            property_schema = {"type": value_type}
            if details:
                if isinstance(details[0], list):
                    property_schema["enum"] = details[0]
                elif details[0]:
                    property_schema["format"] = details[0]
        properties[name] = property_schema
        if is_required:
            required.append(name)
    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {"schema": schema}
        },
    }


def _model_schemas():
    """Gera schemas OpenAPI para todos os modelos concretos do app."""
    type_mapping = {
        "AutoField": ("integer", "int32"),
        "BigAutoField": ("integer", "int64"),
        "SmallAutoField": ("integer", "int32"),
        "IntegerField": ("integer", "int32"),
        "BigIntegerField": ("integer", "int64"),
        "SmallIntegerField": ("integer", "int32"),
        "PositiveIntegerField": ("integer", "int32"),
        "PositiveBigIntegerField": ("integer", "int64"),
        "PositiveSmallIntegerField": ("integer", "int32"),
        "BooleanField": ("boolean", None),
        "NullBooleanField": ("boolean", None),
        "DateField": ("string", "date"),
        "DateTimeField": ("string", "date-time"),
        "TimeField": ("string", "time"),
        "DecimalField": ("number", "double"),
        "FloatField": ("number", "double"),
        "EmailField": ("string", "email"),
        "URLField": ("string", "uri"),
        "UUIDField": ("string", "uuid"),
        "JSONField": ("object", None),
        "TextField": ("string", None),
        "CharField": ("string", None),
        "SlugField": ("string", None),
        "DurationField": ("string", "duration"),
        "BinaryField": ("string", "byte"),
    }
    schemas = {}
    models = list(apps.get_app_config("agendamento").get_models())
    for model in models:
        properties = {}
        required = []
        for field in model._meta.get_fields():
            if not getattr(field, "concrete", False):
                continue
            field_type, field_format = type_mapping.get(
                field.get_internal_type(),
                ("string", None),
            )
            if field.many_to_many:
                property_schema = {
                    "type": "array",
                    "items": {"type": "integer"},
                }
            else:
                property_schema = {"type": field_type}
                if field_format:
                    property_schema["format"] = field_format
                if field.is_relation and field.related_model:
                    property_schema["description"] = (
                        f"ID relacionado a {field.related_model.__name__}."
                    )
            if field.primary_key:
                property_schema["readOnly"] = True
            if field.null:
                property_schema["nullable"] = True
            if field.choices:
                property_schema["enum"] = [
                    value for value, _label in field.flatchoices
                ]
            if field.name == "password":
                property_schema["writeOnly"] = True
            properties[field.name] = property_schema
            if (
                not field.primary_key
                and not field.blank
                and not field.null
                and not field.has_default()
                and not field.auto_created
            ):
                required.append(field.name)
        model_group = {
            "Profissional": "Profissionais",
            "Cliente": "Alunos (Clientes)",
            "Agendamento": "Alunos (Clientes)",
            "Recorrencia": "Alunos (Clientes)",
            "Usuario": "Alunos (Clientes)",
            "Perfil": "Alunos (Clientes)",
            "Recepcionista": "Recepção",
            "Administrador": "Administração",
            "Papel": "Administração",
            "Permissao": "Administração",
            "Servico": "Administração",
            "Disponibilidade": "Profissionais",
            "Bloqueio": "Profissionais",
            "Sala": "Administração",
            "Recurso": "Administração",
        }.get(model.__name__, "Administração")
        schemas[model.__name__] = {
            "type": "object",
            "description": (
                f"Modelo Django `{model._meta.label}`. Seção: `{model_group}`."
            ),
            "properties": properties,
        }
        if required:
            schemas[model.__name__]["required"] = required
    return schemas


def swagger_docs(request):
    """Serve a interface Swagger UI apontando para o schema OpenAPI local."""
    schema_url = reverse("api_schema")
    return HttpResponse(
        """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Swagger UI - API Equilibra</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function () {
      SwaggerUIBundle({
        url: "%s",
        dom_id: "#swagger-ui",
        presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
        layout: "StandaloneLayout",
        withCredentials: true
      });
    };
  </script>
</body>
</html>"""
        % schema_url
    )


def _acesso_negado(request):
    return render(request, "agendamento/acesso_negado.html", status=403)


def _url_tela_inicial(usuario):
    if usuario.perfil.papel == Perfil.Papel.ADMINISTRADOR:
        return reverse("administracao")
    return reverse("inicio")


def _cliente_para_usuario(usuario):
    cliente = Cliente.objects.filter(pk=usuario.pk).first()
    if cliente is not None:
        return cliente

    cliente = Cliente(
        usuario_ptr=usuario,
        password=usuario.password,
        last_login=usuario.last_login,
        is_superuser=usuario.is_superuser,
        first_name=usuario.first_name,
        last_name=usuario.last_name,
        is_staff=usuario.is_staff,
        is_active=usuario.is_active,
        date_joined=usuario.date_joined,
        email=usuario.email,
        nome=usuario.nome,
    )
    cliente.save()
    return cliente


def _proximos_horarios(profissional, servico, quantidade=5):
    """Próximos inícios livres do profissional para o serviço (RF09).

    Usa ``horarios_livres`` dia a dia, com passo de 30 minutos, descartando
    horários que já passaram.
    """
    agora = timezone.now()
    hoje = timezone.localdate()
    horarios = []
    for dias_a_frente in range(31):
        data = hoje + timedelta(days=dias_a_frente)
        for inicio in horarios_livres(
            profissional,
            data,
            duracao_minutos=servico.duracao_minutos,
            passo_minutos=30,
        ):
            if inicio >= agora:
                horarios.append(inicio)
                if len(horarios) >= quantidade:
                    return horarios
    return horarios


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email"}
        ),
    )
    password = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"autocomplete": "current-password"}
        ),
    )
    error_messages = {
        "invalid_login": _("E-mail ou senha inválidos. Verifique os dados e tente novamente."),
        "inactive": _("Esta conta está inativa."),
    }


class LoginView(DjangoLoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "agendamento/login.html"

    def get_success_url(self):
        return _url_tela_inicial(self.request.user)


class CadastroForm(forms.Form):
    nome = forms.CharField(label=_("Nome completo"), max_length=150)
    email = forms.EmailField(
        label=_("E-mail"),
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    papel = forms.ChoiceField(
        label=_("Tipo de usuário"),
        choices=(
            (Perfil.Papel.CLIENTE, _("Cliente")),
            (Perfil.Papel.PROFISSIONAL, _("Profissional")),
            (Perfil.Papel.RECEPCIONISTA, _("Recepcionista")),
        ),
        initial=Perfil.Papel.CLIENTE,
    )
    especialidade = forms.CharField(
        label=_("Especialidade"),
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "organization-title"}),
    )
    modalidade = forms.ChoiceField(
        label=_("Modalidade de atendimento"),
        choices=Profissional.Modalidade.choices,
        required=False,
        initial=Profissional.Modalidade.PRESENCIAL,
    )
    senha = forms.CharField(
        label=_("Senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    confirmar_senha = forms.CharField(
        label=_("Confirme a senha"),
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("Já existe uma conta com este e-mail."))
        return email

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("papel") == Perfil.Papel.PROFISSIONAL
            and not cleaned_data.get("especialidade", "").strip()
        ):
            self.add_error(
                "especialidade",
                _("Informe sua especialidade profissional."),
            )
        if (
            cleaned_data.get("papel") == Perfil.Papel.PROFISSIONAL
            and not cleaned_data.get("modalidade")
        ):
            self.add_error(
                "modalidade",
                _("Informe a modalidade de atendimento."),
            )
        senha = cleaned_data.get("senha")
        confirmar_senha = cleaned_data.get("confirmar_senha")
        if senha and confirmar_senha and senha != confirmar_senha:
            self.add_error("confirmar_senha", _("As senhas não coincidem."))
        if senha and cleaned_data.get("email") and cleaned_data.get("nome"):
            usuario = Usuario(
                email=cleaned_data["email"],
                nome=cleaned_data["nome"],
            )
            try:
                validate_password(senha, user=usuario)
            except ValidationError as error:
                self.add_error("senha", error)
        return cleaned_data

    @transaction.atomic
    def save(self):
        papel = self.cleaned_data["papel"]
        tipo_usuario = {
            Perfil.Papel.CLIENTE: Cliente,
            Perfil.Papel.PROFISSIONAL: Profissional,
            Perfil.Papel.RECEPCIONISTA: Recepcionista,
        }[papel]
        extra_fields = {}
        if papel == Perfil.Papel.PROFISSIONAL:
            extra_fields["especialidade"] = self.cleaned_data[
                "especialidade"
            ].strip()
            extra_fields["modalidade"] = self.cleaned_data["modalidade"]
        return tipo_usuario.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["senha"],
            nome=self.cleaned_data["nome"],
            papel=papel,
            **extra_fields,
        )


class CadastroView(FormView):
    form_class = CadastroForm
    template_name = "agendamento/cadastro.html"
    success_url = reverse_lazy("inicio")

    def form_valid(self, form):
        usuario = form.save()
        # Entra direto na conta recém-criada: pedir a senha de novo logo após
        # digitá-la duas vezes não acrescenta nada.
        login(
            self.request,
            usuario,
            backend="django.contrib.auth.backends.ModelBackend",
        )
        messages.success(
            self.request,
            _("Conta criada com sucesso. Bem-vindo(a) ao Equilibra!"),
        )
        return HttpResponseRedirect(_url_tela_inicial(usuario))


class InicioView(LoginRequiredMixin, TemplateView):
    template_name = "agendamento/inicio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        perfil = usuario.perfil
        agora = timezone.now()
        context.update(
            {
                "papel": perfil.get_papel_display(),
                "eh_cliente": perfil.papel == Perfil.Papel.CLIENTE,
                "eh_profissional": perfil.papel == Perfil.Papel.PROFISSIONAL,
                "eh_recepcionista": perfil.papel == Perfil.Papel.RECEPCIONISTA,
            }
        )

        if perfil.papel in (
            Perfil.Papel.CLIENTE,
            Perfil.Papel.PROFISSIONAL,
        ):
            campo = (
                "cliente_id"
                if perfil.papel == Perfil.Papel.CLIENTE
                else "profissional_id"
            )
            context["agendamentos"] = (
                Agendamento.objects.filter(**{campo: usuario.pk})
                .filter(data_hora_inicio__gte=agora)
                .exclude(status=Agendamento.Status.CANCELADO)
                .select_related("cliente", "profissional", "servico", "sala")
                .order_by("data_hora_inicio")[:10]
            )
        elif perfil.papel == Perfil.Papel.RECEPCIONISTA:
            hoje = timezone.localdate()
            context["agendamentos"] = (
                Agendamento.objects.filter(data_hora_inicio__date=hoje)
                .exclude(status=Agendamento.Status.CANCELADO)
                .select_related("cliente", "profissional", "servico", "sala")
                .order_by("data_hora_inicio")
            )
            context["hoje"] = hoje

        return context


class UsuarioPerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ("nome", "telefone")


class ProfissionalPerfilForm(forms.ModelForm):
    class Meta:
        model = Profissional
        fields = ("nome", "telefone", "especialidade", "apresentacao")
        labels = {"apresentacao": _("Apresentação")}


class PerfilEdicaoView(LoginRequiredMixin, View):
    template_name = "agendamento/perfil_edicao.html"

    def get_form(self, request, data=None):
        if request.user.perfil.papel == Perfil.Papel.PROFISSIONAL:
            profissional = get_object_or_404(Profissional, pk=request.user.pk)
            return ProfissionalPerfilForm(data=data, instance=profissional)
        return UsuarioPerfilForm(data=data, instance=request.user)

    def render_form(self, request, form):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "eh_profissional": (
                    request.user.perfil.papel == Perfil.Papel.PROFISSIONAL
                ),
            },
        )

    def get(self, request, *args, **kwargs):
        return self.render_form(request, self.get_form(request))

    def post(self, request, *args, **kwargs):
        form = self.get_form(request, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Perfil atualizado com sucesso."))
            return HttpResponseRedirect(_url_tela_inicial(request.user))
        return self.render_form(request, form)


class ProfissionalListView(ListView):
    model = Profissional
    context_object_name = "profissionais"
    template_name = "agendamento/profissional_list.html"

    def get_queryset(self):
        queryset = Profissional.objects.filter(is_active=True).prefetch_related(
            "servicos"
        )
        especialidade = self.request.GET.get("especialidade", "").strip()
        servico = self.request.GET.get("servico", "").strip()
        modalidade = self.request.GET.get("modalidade", "").strip()

        if especialidade:
            queryset = queryset.filter(especialidade__iexact=especialidade)
        if servico:
            queryset = queryset.filter(
                servicos__nome__iexact=servico
            ).distinct()
        if modalidade:
            queryset = queryset.filter(modalidade=modalidade)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profissionais_ativos = Profissional.objects.filter(is_active=True)
        context["especialidades"] = (
            profissionais_ativos.order_by("especialidade")
            .values_list("especialidade", flat=True)
            .distinct()
        )
        context["servicos_disponiveis"] = (
            Servico.objects.filter(profissional__is_active=True)
            .order_by("nome")
            .values_list("nome", flat=True)
            .distinct()
        )
        context["modalidades"] = Profissional.Modalidade.choices
        context["filtros"] = {
            "especialidade": self.request.GET.get("especialidade", "").strip(),
            "servico": self.request.GET.get("servico", "").strip(),
            "modalidade": self.request.GET.get("modalidade", "").strip(),
        }
        return context


class ProfissionalDetailView(DetailView):
    model = Profissional
    context_object_name = "profissional"
    template_name = "agendamento/profissional_detail.html"
    queryset = Profissional.objects.filter(is_active=True).prefetch_related(
        "servicos",
        "disponibilidades",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        servicos = context["profissional"].servicos.all()
        for servico in servicos:
            servico.proximos_horarios = _proximos_horarios(
                context["profissional"],
                servico,
            )
        context["servicos"] = servicos
        papel = (
            self.request.user.perfil.papel
            if self.request.user.is_authenticated
            else None
        )
        context["pode_agendar"] = papel == Perfil.Papel.CLIENTE
        context["eh_recepcionista"] = papel == Perfil.Papel.RECEPCIONISTA
        return context


class AgendamentoForm(forms.Form):
    horario = forms.ChoiceField(
        label=_("Próximo horário disponível"),
        choices=(),
        error_messages={
            "invalid_choice": _(
                "Este horário não está mais disponível. Atualize e escolha outro."
            ),
        },
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    sala = forms.ModelChoiceField(
        label=_("Local"),
        queryset=Sala.objects.all(),
        required=False,
        empty_label=_("Não preciso de sala"),
    )
    recursos = forms.ModelMultipleChoiceField(
        label=_("Equipamentos"),
        queryset=Recurso.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Marque apenas se o atendimento precisar de algum equipamento."),
    )
    repetir_semanal = forms.BooleanField(
        label=_("Repetir semanalmente"),
        required=False,
    )
    dias_semana = forms.TypedMultipleChoiceField(
        label=_("Dias da semana"),
        choices=DIAS_SEMANA,
        coerce=int,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Se nenhum dia for marcado, repete no mesmo dia da semana do primeiro horário."),
    )
    data_termino = forms.DateField(
        label=_("Repetir até"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def __init__(self, *args, horarios, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["horario"].choices = [
            (
                horario.isoformat(),
                timezone.localtime(horario).strftime("%d/%m/%Y às %H:%M"),
            )
            for horario in horarios
        ]
        if not Sala.objects.exists():
            del self.fields["sala"]
        if not Recurso.objects.exists():
            del self.fields["recursos"]

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("repetir_semanal") and not cleaned_data.get("data_termino"):
            self.add_error(
                "data_termino",
                _("Informe até quando o agendamento deve se repetir."),
            )
        return cleaned_data

    def montar_recorrencia(self, cliente, servico):
        """Recorrência descrita pelo formulário (ainda não salva)."""
        inicio = timezone.localtime(
            datetime.fromisoformat(self.cleaned_data["horario"])
        )
        return Recorrencia(
            padrao=Recorrencia.PADRAO_SEMANAL,
            cliente=cliente,
            profissional=servico.profissional,
            servico=servico,
            sala=self.cleaned_data.get("sala"),
            dias_semana=self.cleaned_data.get("dias_semana") or [inicio.weekday()],
            data_inicio=inicio.date(),
            data_termino=self.cleaned_data["data_termino"],
            hora_inicio=inicio.time(),
        )


class ClienteRoleRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not Perfil.objects.filter(
            usuario_id=request.user.pk,
            papel=Perfil.Papel.CLIENTE,
        ).exists():
            return _acesso_negado(request)
        self.cliente = _cliente_para_usuario(request.user)
        return super().dispatch(request, *args, **kwargs)


class _AgendamentoBaseView(LoginRequiredMixin, FormView):
    """Fluxo de agendamento de um serviço (UC5, RF10).

    Quando o horário não pode ser reservado, a tela informa o motivo e sugere
    outros horários livres (RF26), preferindo o mesmo dia.

    Serve tanto ao cliente agendando para si quanto à recepção agendando em
    nome de um cliente (RF25): o que muda é de onde vem o cliente.
    """

    form_class = AgendamentoForm
    template_name = "agendamento/novo_agendamento.html"
    success_url = reverse_lazy("profissionais")
    quantidade_horarios = 12
    quantidade_sugestoes = 6

    def dispatch(self, request, *args, **kwargs):
        self.servico = get_object_or_404(
            Servico.objects.select_related("profissional"),
            pk=kwargs["servico_id"],
            profissional__is_active=True,
        )
        self.conflito = []
        self.sugestoes = []
        return super().dispatch(request, *args, **kwargs)

    def get_horarios(self):
        if not hasattr(self, "_horarios"):
            self._horarios = _proximos_horarios(
                self.servico.profissional,
                self.servico,
                quantidade=self.quantidade_horarios,
            )
        return self._horarios

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["horarios"] = self.get_horarios()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["servico"] = self.servico
        context["profissional"] = self.servico.profissional
        context["conflito"] = self.conflito
        context["sugestoes"] = self.sugestoes
        return context

    def get_cliente(self, form):
        """Quem recebe o atendimento. O cliente agenda para si mesmo."""
        return self.cliente

    def get_recepcionista(self):
        """Quem operou o agendamento, quando não foi o próprio cliente."""
        return None

    def _novo_agendamento(self, cliente, inicio, sala):
        return Agendamento(
            cliente=cliente,
            profissional=self.servico.profissional,
            servico=self.servico,
            recepcionista=self.get_recepcionista(),
            sala=sala,
            data_hora_inicio=inicio,
            data_hora_fim=self.servico.calcular_horario_fim(inicio),
        )

    def _sugestoes(self, cliente, inicio, sala, recursos):
        """Outros horários da lista que passam em todas as regras, começando
        pelos do mesmo dia do horário recusado."""
        dia = timezone.localtime(inicio).date()
        candidatos = sorted(
            (h for h in self.get_horarios() if h != inicio),
            key=lambda h: (timezone.localtime(h).date() != dia, h),
        )
        sugestoes = []
        for candidato in candidatos:
            agendamento = self._novo_agendamento(cliente, candidato, sala)
            if not agendamento.motivos_conflito(recursos=recursos):
                sugestoes.append(candidato)
                if len(sugestoes) >= self.quantidade_sugestoes:
                    break
        return sugestoes

    def form_valid(self, form):
        inicio = datetime.fromisoformat(form.cleaned_data["horario"])
        sala = form.cleaned_data.get("sala")
        recursos = list(form.cleaned_data.get("recursos") or [])
        cliente = self.get_cliente(form)
        if form.cleaned_data.get("repetir_semanal"):
            return self._criar_recorrencia(form, cliente, recursos)

        with transaction.atomic():
            Profissional.objects.select_for_update().get(
                pk=self.servico.profissional_id
            )
            agendamento = self._novo_agendamento(cliente, inicio, sala)
            if inicio < timezone.now():
                motivos = [_("Este horário já passou.")]
            else:
                motivos = agendamento.motivos_conflito(recursos=recursos)
            if motivos:
                form.add_error(
                    "horario",
                    _("Este horário não está mais disponível. Escolha outro."),
                )
                self.conflito = motivos
                self.sugestoes = self._sugestoes(cliente, inicio, sala, recursos)
                return self.form_invalid(form)
            agendamento.save()
            agendamento.recursos.set(recursos)

        messages.success(self.request, _("Agendamento confirmado com sucesso."))
        return super().form_valid(form)

    def _criar_recorrencia(self, form, cliente, recursos):
        """Cria a série semanal (UC6): cada sessão é validada isoladamente
        (RN11) e as que têm conflito são descartadas (RN12)."""
        recorrencia = form.montar_recorrencia(cliente, self.servico)
        try:
            recorrencia.clean()
        except ValidationError as erro:
            for campo, mensagens in erro.message_dict.items():
                destino = campo if campo in form.fields else None
                for mensagem in mensagens:
                    form.add_error(destino, mensagem)
            return self.form_invalid(form)

        with transaction.atomic():
            Profissional.objects.select_for_update().get(
                pk=self.servico.profissional_id
            )
            validas, conflitos = recorrencia.avaliar_ocorrencias(recursos=recursos)
            if not validas:
                self.conflito = [
                    _("Todas as sessões do período apresentaram conflito: %(motivo)s")
                    % {"motivo": conflitos[0][1] if conflitos else ""}
                ]
                return self.form_invalid(form)
            recorrencia.save()
            recorrencia.recursos.set(recursos)
            validas, conflitos = recorrencia.gerar_ocorrencias(recursos=recursos)

        if conflitos:
            datas = ", ".join(
                timezone.localtime(agendamento.data_hora_inicio).strftime("%d/%m/%Y")
                for agendamento, _motivo in conflitos
            )
            messages.warning(
                self.request,
                _(
                    "Série criada com %(validas)s sessão(ões). %(conflitos)s "
                    "sessão(ões) com conflito foram descartadas (%(datas)s)."
                )
                % {"validas": len(validas), "conflitos": len(conflitos), "datas": datas},
            )
        else:
            messages.success(
                self.request,
                _("Série criada com sucesso: %(validas)s sessões agendadas.")
                % {"validas": len(validas)},
            )
        return HttpResponseRedirect(reverse("minha_agenda"))


class NovoAgendamentoView(ClienteRoleRequiredMixin, _AgendamentoBaseView):
    """Agendamento feito pelo próprio cliente."""


class RecepcionistaRoleRequiredMixin(LoginRequiredMixin):
    """Restringe a tela ao papel de recepcionista (RN14)."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not Perfil.objects.filter(
            usuario_id=request.user.pk,
            papel=Perfil.Papel.RECEPCIONISTA,
        ).exists():
            return _acesso_negado(request)
        self.recepcionista = Recepcionista.objects.get(pk=request.user.pk)
        return super().dispatch(request, *args, **kwargs)


class AgendamentoRecepcaoForm(AgendamentoForm):
    """Mesmo formulário do cliente, com a escolha de para quem é o atendimento."""

    cliente = forms.ModelChoiceField(
        label=_("Cliente"),
        queryset=Cliente.objects.filter(is_active=True).order_by("nome"),
        empty_label=_("Selecione o cliente"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # O cliente aparece antes dos demais campos na tela.
        self.order_fields(["cliente", *[c for c in self.fields if c != "cliente"]])


class RecepcaoAgendarView(RecepcionistaRoleRequiredMixin, _AgendamentoBaseView):
    """Agendamento criado pela recepção em nome de um cliente (RF25, RN14).

    Usa as mesmas regras de conflito do agendamento feito pelo cliente; o
    atendimento fica registrado com a recepcionista que o operou.
    """

    form_class = AgendamentoRecepcaoForm
    template_name = "agendamento/recepcao_agendar.html"
    success_url = reverse_lazy("recepcao_agenda")

    def get_cliente(self, form):
        return form.cleaned_data["cliente"]

    def get_recepcionista(self):
        return self.recepcionista


class RecepcaoAgendaView(RecepcionistaRoleRequiredMixin, ListView):
    """Agenda do dia para a recepção acompanhar a operação (RF25, RN14)."""

    model = Agendamento
    context_object_name = "agendamentos"
    template_name = "agendamento/recepcao_agenda.html"

    def dia(self):
        valor = self.request.GET.get("dia", "").strip()
        try:
            return date.fromisoformat(valor) if valor else timezone.localdate()
        except ValueError:
            return timezone.localdate()

    def get_queryset(self):
        dia = self.dia()
        inicio = timezone.make_aware(datetime.combine(dia, time.min))
        fim = inicio + timedelta(days=1)
        return (
            Agendamento.objects.filter(
                data_hora_inicio__gte=inicio,
                data_hora_inicio__lt=fim,
            )
            .select_related("cliente", "profissional", "servico", "sala")
            .prefetch_related("recursos")
            .order_by("data_hora_inicio")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dia = self.dia()
        context.update(
            {
                "dia": dia,
                "dia_anterior": dia - timedelta(days=1),
                "dia_seguinte": dia + timedelta(days=1),
                "hoje": timezone.localdate(),
                "profissionais": Profissional.objects.filter(
                    is_active=True
                ).order_by("nome"),
            }
        )
        return context


class PreviaRecorrenciaView(NovoAgendamentoView):
    """JSON com cada data da série e se ela está livre ou em conflito (RF16).

    Usa o mesmo formulário e as mesmas regras da criação, sem salvar nada.
    """

    http_method_names = ["post"]

    def form_invalid(self, form):
        mensagens = [
            str(mensagem)
            for erros in form.errors.values()
            for mensagem in erros
        ]
        return JsonResponse(
            {"valido": False, "erro": " ".join(mensagens)},
            status=400,
        )

    def form_valid(self, form):
        if not Perfil.objects.filter(
            usuario_id=self.request.user.pk,
            papel=Perfil.Papel.CLIENTE,
        ).exists():
            return JsonResponse(
                {"valido": False, "erro": str(_("Apenas clientes podem agendar."))},
                status=403,
            )
        if not form.cleaned_data.get("data_termino"):
            return JsonResponse(
                {"valido": False, "erro": str(_("Informe até quando o agendamento deve se repetir."))},
                status=400,
            )
        cliente = _cliente_para_usuario(self.request.user)
        recorrencia = form.montar_recorrencia(cliente, self.servico)
        try:
            recorrencia.clean()
        except ValidationError as erro:
            return JsonResponse(
                {"valido": False, "erro": " ".join(erro.messages)},
                status=400,
            )

        recursos = list(form.cleaned_data.get("recursos") or [])
        validas, conflitos = recorrencia.avaliar_ocorrencias(recursos=recursos)
        motivos = {
            timezone.localtime(agendamento.data_hora_inicio).date(): motivo
            for agendamento, motivo in conflitos
        }
        nomes = dict(DIAS_SEMANA)
        sessoes = []
        for agendamento in sorted(
            validas + [agendamento for agendamento, _motivo in conflitos],
            key=lambda item: item.data_hora_inicio,
        ):
            inicio = timezone.localtime(agendamento.data_hora_inicio)
            fim = timezone.localtime(agendamento.data_hora_fim)
            conflito = inicio.date() in motivos
            sessoes.append(
                {
                    "data": inicio.date().isoformat(),
                    "data_formatada": f"{inicio:%d/%m/%Y} ({nomes[inicio.weekday()]})",
                    "horario": f"{inicio:%H:%M} - {fim:%H:%M}",
                    "conflito": conflito,
                    "status": "Conflito" if conflito else "Disponível",
                    "motivo": motivos.get(inicio.date(), ""),
                }
            )
        return JsonResponse(
            {
                "valido": True,
                "total": len(sessoes),
                "total_validas": len(validas),
                "total_conflitos": len(conflitos),
                "sessoes": sessoes,
            }
        )


class AgendaClienteView(ClienteRoleRequiredMixin, ListView):
    """Agenda do cliente com filtro opcional por período (UC9, RF17)."""

    model = Agendamento
    context_object_name = "agendamentos"
    template_name = "agendamento/minha_agenda.html"

    def _data_do_filtro(self, nome):
        valor = self.request.GET.get(nome, "").strip()
        try:
            return valor, date.fromisoformat(valor) if valor else None
        except ValueError:
            return valor, None

    def get_queryset(self):
        queryset = (
            Agendamento.objects.filter(cliente=self.cliente)
            .select_related("servico", "profissional", "sala")
            .prefetch_related("recursos")
            .order_by("data_hora_inicio")
        )
        _, data_inicio = self._data_do_filtro("data_inicio")
        _, data_fim = self._data_do_filtro("data_fim")
        if data_inicio:
            queryset = queryset.filter(
                data_hora_inicio__gte=timezone.make_aware(
                    datetime.combine(data_inicio, time.min)
                )
            )
        if data_fim:
            queryset = queryset.filter(
                data_hora_inicio__lt=timezone.make_aware(
                    datetime.combine(data_fim + timedelta(days=1), time.min)
                )
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["now"] = timezone.now()
        context["data_inicio"] = self._data_do_filtro("data_inicio")[0]
        context["data_fim"] = self._data_do_filtro("data_fim")[0]
        context["filtrando"] = bool(context["data_inicio"] or context["data_fim"])
        return context


# ---------------------------------------------------------------------------
# Cancelamento e reagendamento (UC7, UC8, RF11, RF12, RN10).
# ---------------------------------------------------------------------------
def _pode_operar_agendamento(usuario, agendamento):
    """Cliente do atendimento, profissional responsável, recepção (RN14) ou
    administração podem cancelar e reagendar."""
    papel = (
        Perfil.objects.filter(usuario_id=usuario.pk)
        .values_list("papel", flat=True)
        .first()
    )
    if papel == Perfil.Papel.CLIENTE:
        return agendamento.cliente_id == usuario.pk
    if papel == Perfil.Papel.PROFISSIONAL:
        return agendamento.profissional_id == usuario.pk
    return papel in (Perfil.Papel.RECEPCIONISTA, Perfil.Papel.ADMINISTRADOR)


def _agendamento_operavel(request, pk):
    """Agendamento que o usuário pode operar; 404 para os demais, sem revelar
    que o atendimento existe."""
    agendamento = get_object_or_404(
        Agendamento.objects.select_related("servico", "profissional", "cliente"),
        pk=pk,
    )
    if not _pode_operar_agendamento(request.user, agendamento):
        raise Http404
    return agendamento


def _pode_ser_alterado(agendamento):
    """Só atendimentos futuros e ativos podem ser cancelados ou reagendados."""
    return (
        agendamento.status
        in (Agendamento.Status.AGENDADO, Agendamento.Status.CONFIRMADO)
        and agendamento.data_hora_inicio > timezone.now()
    )


def _destino_apos_operacao(request):
    destino = request.POST.get("origem")
    if destino and url_has_allowed_host_and_scheme(
        destino,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return destino
    if Perfil.objects.filter(
        usuario_id=request.user.pk, papel=Perfil.Papel.CLIENTE
    ).exists():
        return reverse("minha_agenda")
    return reverse("inicio")


class CancelarAgendamentoView(LoginRequiredMixin, View):
    """Cancela uma sessão ou, em atendimentos recorrentes, toda a série."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        agendamento = _agendamento_operavel(request, kwargs["pk"])
        destino = _destino_apos_operacao(request)
        if not _pode_ser_alterado(agendamento):
            messages.error(
                request,
                _("Este agendamento não pode mais ser cancelado."),
            )
            return HttpResponseRedirect(destino)

        if request.POST.get("escopo") == "serie" and agendamento.recorrencia_id:
            total = agendamento.recorrencia.cancelar()
            messages.success(
                request,
                _(
                    "Série cancelada: %(total)s sessão(ões) futura(s) cancelada(s). "
                    "Os horários, a sala e os equipamentos foram liberados."
                )
                % {"total": total},
            )
        else:
            agendamento.status = Agendamento.Status.CANCELADO
            agendamento.save(update_fields=["status"])
            messages.success(request, _("Agendamento cancelado."))
        return HttpResponseRedirect(destino)


class HorariosReagendamentoView(LoginRequiredMixin, View):
    """JSON com os horários livres para remarcar um atendimento numa data.

    O próprio atendimento não conta como ocupado, e só entram horários que
    passam em todas as regras de conflito com a sala e os equipamentos já
    reservados.
    """

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        agendamento = _agendamento_operavel(request, kwargs["pk"])
        if not _pode_ser_alterado(agendamento):
            return JsonResponse(
                {"erro": _("Este agendamento não pode mais ser reagendado.")},
                status=400,
            )
        valor = request.GET.get("data", "").strip()
        if not valor:
            return JsonResponse({"erro": _("Informe a data.")}, status=400)
        try:
            data = date.fromisoformat(valor)
        except ValueError:
            return JsonResponse(
                {"erro": _("Formato de data inválido. Use AAAA-MM-DD.")},
                status=400,
            )

        agora = timezone.now()
        duracao = agendamento.servico.duracao_minutos
        recursos = list(agendamento.recursos.all())
        horarios = []
        for inicio in horarios_livres(
            agendamento.profissional,
            data,
            duracao_minutos=duracao,
            passo_minutos=30,
            ignorar=agendamento,
        ):
            if inicio <= agora:
                continue
            candidato = Agendamento(
                pk=agendamento.pk,
                cliente_id=agendamento.cliente_id,
                profissional_id=agendamento.profissional_id,
                servico_id=agendamento.servico_id,
                sala_id=agendamento.sala_id,
                data_hora_inicio=inicio,
                data_hora_fim=agendamento.servico.calcular_horario_fim(inicio),
            )
            if not candidato.motivos_conflito(recursos=recursos):
                horarios.append(timezone.localtime(inicio).strftime("%H:%M"))

        return JsonResponse(
            {"horarios": horarios, "data": valor, "duracao_minutos": duracao}
        )


class ReagendarAgendamentoView(LoginRequiredMixin, View):
    """Remarca um atendimento (UC7). A troca é atômica: o horário antigo só é
    liberado quando o novo passa em todas as regras."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        agendamento = _agendamento_operavel(request, kwargs["pk"])
        if not _pode_ser_alterado(agendamento):
            return JsonResponse(
                {"erro": _("Este agendamento não pode mais ser reagendado.")},
                status=400,
            )
        nova_data = request.POST.get("data", "").strip()
        nova_hora = request.POST.get("hora_inicio", "").strip()
        if not nova_data or not nova_hora:
            return JsonResponse(
                {"erro": _("Informe a nova data e o novo horário.")},
                status=400,
            )
        try:
            inicio = timezone.make_aware(
                datetime.combine(
                    date.fromisoformat(nova_data),
                    time.fromisoformat(nova_hora),
                )
            )
        except ValueError:
            return JsonResponse(
                {"erro": _("Data ou horário em formato inválido.")},
                status=400,
            )
        if inicio == agendamento.data_hora_inicio:
            return JsonResponse(
                {"erro": _("O novo horário é igual ao atual.")},
                status=400,
            )
        if inicio <= timezone.now():
            return JsonResponse(
                {"erro": _("Escolha um horário que ainda não passou.")},
                status=400,
            )

        with transaction.atomic():
            Profissional.objects.select_for_update().get(
                pk=agendamento.profissional_id
            )
            agendamento.data_hora_inicio = inicio
            agendamento.data_hora_fim = agendamento.servico.calcular_horario_fim(
                inicio
            )
            motivos = agendamento.motivos_conflito()
            if motivos:
                return JsonResponse({"erro": " ".join(motivos)}, status=400)
            agendamento.save(update_fields=["data_hora_inicio", "data_hora_fim"])

        local_inicio = timezone.localtime(agendamento.data_hora_inicio)
        local_fim = timezone.localtime(agendamento.data_hora_fim)
        messages.success(
            request,
            _("Atendimento remarcado para %(data)s às %(hora)s.")
            % {
                "data": local_inicio.strftime("%d/%m/%Y"),
                "hora": local_inicio.strftime("%H:%M"),
            },
        )
        return JsonResponse(
            {
                "ok": True,
                "data": local_inicio.strftime("%d/%m/%Y"),
                "hora_inicio": local_inicio.strftime("%H:%M"),
                "hora_fim": local_fim.strftime("%H:%M"),
            }
        )
