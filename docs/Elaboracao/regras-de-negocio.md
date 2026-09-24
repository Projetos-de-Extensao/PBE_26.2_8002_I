---
id: regras_de_negocio
title: Regras de Negócio
---

## Introdução

<p align = "justify">
Este documento reúne as regras de negócio da Plataforma Web de Agendamento Multidisciplinar. Elas são as restrições que o sistema precisa garantir independentemente da tela ou do fluxo em que a operação é feita, e são referenciadas pelos <a href="./levreq.md">casos de uso</a> e pelo <a href="./diagrama_de_classes.md">diagrama de classes</a>.
</p>

## Regras

| ID | Regra | Requisitos relacionados |
|---|---|---|
| RN01 | Um profissional não pode possuir dois atendimentos no mesmo intervalo de tempo. | RF13 |
| RN02 | Um cliente não pode possuir dois atendimentos no mesmo intervalo de tempo. | RF14 |
| RN03 | Uma sala não pode ser reservada por dois atendimentos no mesmo intervalo de tempo. | RF15 |
| RN04 | Um recurso de uso exclusivo não pode ser reservado por dois atendimentos no mesmo intervalo de tempo. | RF15 |
| RN05 | Só podem ser selecionados horários compatíveis com a disponibilidade configurada pelo profissional. | RF07, RF09 |
| RN06 | Um agendamento só é confirmado quando cliente, profissional e, quando aplicável, sala e recurso estiverem livres no mesmo intervalo. | RF10, RF13, RF14, RF15 |
| RN07 | O horário de término do atendimento é calculado a partir do horário de início somado à duração do serviço. | RF05, RF10 |
| RN08 | Todo usuário possui um papel (cliente, profissional, recepcionista ou administrador), e o papel determina o que ele pode visualizar e alterar. | RF19 |
| RN09 | Apenas o administrador pode gerenciar usuários, profissionais, serviços, espaços, recursos e permissões. | RF04, RF05, RF06, RF19 |
| RN10 | O cancelamento de um atendimento libera imediatamente o horário, a sala e o recurso reservados. | RF11, RF12 |
| RN11 | Em um agendamento recorrente, cada ocorrência é validada individualmente contra as regras RN01 a RN06. | RF16 |
| RN12 | Uma ocorrência de recorrência em conflito não pode sobrescrever uma reserva existente; ela é descartada ou reagendada. | RF16, RF26 |
| RN13 | Um bloqueio torna o intervalo indisponível para novos agendamentos; se houver atendimento confirmado no período, o profissional deve ser alertado antes da aplicação. | RF20 |
| RN14 | A recepção executa apenas as operações permitidas ao seu papel, sem acesso administrativo completo. | RF19, RF25 |
| RN15 | Todo atendimento possui um status (agendado, confirmado, cancelado ou realizado), e a mudança de status é registrada pelo sistema. | RF24 |

## Observações

<p align = "justify">
As regras RN01 a RN06 formam o núcleo do produto: a prevenção de conflitos entre cliente, profissional, sala e recurso. As regras RN08, RN09 e RN14 sustentam o controle de privilégios por papel. As demais apoiam o cálculo de horários, a recorrência, os bloqueios e o ciclo de vida do atendimento.
</p>

## Referências

> [Levantamento de Requisitos e Casos de Uso](./levreq.md)

> [Diagrama de Classes](./diagrama_de_classes.md)

> [Brainstorm](../Iniciacao/Brainstorm.md)

## Autor(es)

| Data | Versão | Descrição | Autor(es) |
|---|---|---|---|
| 23/09/2026 | 1.0 | Consolidação das regras de negócio citadas nos casos de uso e no diagrama de classes | Equipe do projeto |
