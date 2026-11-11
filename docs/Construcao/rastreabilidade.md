---
id: rastreabilidade
title: Rastreabilidade
---

## Introdução

<p align = "justify">
Esta página liga o que foi documentado ao que está implementado: cada requisito
funcional aponta a tela ou o comportamento que o atende no sistema, e cada regra
de negócio aponta onde é verificada no código. Serve para conferir a entrega e
para encontrar rapidamente o ponto certo ao corrigir algo.
</p>

Base: app `agendamento`, com o fluxo em `agendamento/views.py`, a área do
profissional em `agendamento/agenda_profissional.py`, a administração em
`agendamento/administracao.py` e as regras em `agendamento/models.py`.

## Requisitos funcionais

| ID | Requisito | Onde está | Situação |
|---|---|---|---|
| RF01 | Cadastro de usuários | Tela `/cadastrar/` | Implementado |
| RF02 | Autenticação por e-mail e senha | Tela `/` | Implementado |
| RF03 | Recuperação de senha | `/senha/redefinir/` | Implementado (e-mail no terminal em desenvolvimento) |
| RF04 | Administrador gerencia profissionais | `/administracao/profissionais/` | Implementado |
| RF05 | Administrador gerencia serviços | `/administracao/servicos/` | Implementado |
| RF06 | Administrador cadastra salas e equipamentos | `/administracao/salas/`, `/administracao/recursos/` | Implementado |
| RF07 | Profissional configura disponibilidade | `/profissional/disponibilidade/` | Implementado |
| RF08 | Cliente pesquisa profissionais | `/profissionais/` | Implementado |
| RF09 | Cliente visualiza horários disponíveis | Perfil do profissional e tela de agendar | Implementado |
| RF10 | Cliente realiza agendamento | `/agendar/<servico>/` | Implementado |
| RF11 | Cliente cancela atendimento | `/minha-agenda/<id>/cancelar/` | Implementado |
| RF12 | Cliente reagenda atendimento | `/agendamentos/<id>/reagendar/` | Implementado |
| RF13 | Impedir conflito do profissional | `Agendamento.motivos_conflito` | Implementado |
| RF14 | Impedir conflito do cliente | `Agendamento.motivos_conflito` | Implementado |
| RF15 | Impedir conflito de sala ou equipamento | `Agendamento.motivos_conflito` e `conflitos_de_recursos` | Implementado |
| RF16 | Agendamentos recorrentes | Bloco de repetição na tela de agendar | Implementado |
| RF17 | Agenda do cliente | `/minha-agenda/` | Implementado |
| RF18 | Agenda do profissional | `/profissional/agenda/` | Implementado |
| RF19 | Permissões conforme o papel | Mixins de papel nas views | Implementado |
| RF20 | Profissional bloqueia horários | `/profissional/disponibilidade/` | Implementado |
| RF21 | Lembretes de atendimento | — | Fora do MVP |
| RF22 | Lista de espera | — | Fora do MVP |
| RF23 | Informações operacionais do administrador | Painel `/administracao/` | Implementado |
| RF24 | Registro do status do atendimento | Campo `status` em `Agendamento` | Implementado |
| RF25 | Recepção cria, reagenda ou cancela agendamentos | `/recepcao/agendar/<servico>/` e `/recepcao/agenda/` | Parcial: a recepção cria atendimentos e acompanha a agenda do dia; reagendar e cancelar continuam com o cliente |
| RF26 | Informar o motivo do conflito e permitir nova escolha | Tela de agendar, com sugestões de horário | Implementado |

## Regras de negócio

| ID | Regra | Onde é verificada |
|---|---|---|
| RN01 | Conflito do profissional | `Agendamento.motivos_conflito` |
| RN02 | Conflito do cliente | `Agendamento.motivos_conflito` |
| RN03 | Conflito de sala | `Agendamento.motivos_conflito` |
| RN04 | Equipamento exclusivo | `Agendamento.conflitos_de_recursos`, também ao vincular o equipamento (sinal `m2m_changed`) |
| RN05 | Horário dentro da disponibilidade | `Agendamento._dentro_da_disponibilidade` |
| RN06 | Confirmação só com tudo livre | `Agendamento.clean`, chamado no `save` |
| RN07 | Término calculado pela duração | `Servico.calcular_horario_fim` |
| RN08 | Todo usuário tem um papel | `Perfil` e o sinal que o cria |
| RN09 | Administrador gerencia os cadastros | Mixin de administração em `administracao.py` |
| RN10 | Cancelamento libera o horário | Fluxo de cancelamento em `views.py` |
| RN11 | Cada ocorrência da série é validada | `Recorrencia.avaliar_ocorrencias` |
| RN12 | Ocorrência em conflito não sobrescreve | `Recorrencia.gerar_ocorrencias` |
| RN13 | Bloqueio torna o intervalo indisponível | `Agendamento.motivos_conflito` e `Bloqueio.agendamentos_afetados` |
| RN14 | Recepção sem acesso administrativo | `RecepcionistaRoleRequiredMixin` |
| RN15 | Status do atendimento | `Agendamento.Status` |

## O que ficou fora do MVP

<p align = "justify">
Lembretes automáticos (RF21) e lista de espera (RF22) foram classificados como
evolução desde o brainstorm e não entraram nesta entrega. No RF25, a recepção
cria atendimentos e acompanha a agenda do dia; reagendar e cancelar em nome do
cliente ficaram para a próxima iteração. Prontuário clínico, telemedicina,
convênios, pagamentos e aplicativo nativo seguem fora do escopo, como registrado
na pesquisa do tema.
</p>

## Testes

<p align = "justify">
A suíte automatizada cobre os fluxos acima e roda com
<code>python manage.py test agendamento</code>.
</p>

## Referências

> [Levantamento de Requisitos e Casos de Uso](../Elaboracao/levreq.md)

> [Regras de Negócio](../Elaboracao/regras-de-negocio.md)

> [Papéis e Permissões](../Elaboracao/papeis-e-permissoes.md)
