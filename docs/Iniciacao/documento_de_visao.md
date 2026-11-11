---
id: documento_de_visao
title: Documento de Visão
---

## Introdução

<p align = "justify">
Este documento apresenta a visão geral do Equilibra, plataforma web de
agendamento multidisciplinar desenvolvida na disciplina Projeto Back-End
(IBM8936), turma PBE 26.2 — 8002 I. Ele descreve o problema atacado, os
usuários atendidos, as funcionalidades principais e os limites do produto.
</p>

## Descrição do Problema

### Problema

<p align = "justify">
Em academias, clínicas e estúdios, cada profissional costuma manter a própria
agenda em ferramentas separadas: mensagens de WhatsApp, planilhas e cadernos.
Quando um mesmo cliente é acompanhado por mais de um profissional — personal
trainer, nutricionista e fisioterapeuta, por exemplo — ninguém enxerga a rotina
completa dele, e as salas e os equipamentos compartilhados não têm controle
nenhum.
</p>

### Impactados

Clientes, profissionais de treinamento, saúde e bem-estar, recepcionistas e
administradores do estabelecimento.

### Consequência

<p align = "justify">
O resultado é choque de horário, retrabalho para remarcar, sala ou equipamento
reservado em duplicidade e dependência de troca de mensagens para qualquer
alteração. O cliente não tem uma visão única dos seus atendimentos e o
estabelecimento não sabe qual é a ocupação real dos seus espaços.
</p>

### Solução

<p align = "justify">
Uma plataforma web única em que o cliente pesquisa profissionais, consulta
horários livres e agenda, reagenda ou cancela atendimentos; o profissional
configura sua disponibilidade e bloqueios; a recepção opera a agenda em nome do
cliente; e o administrador mantém profissionais, serviços, salas, equipamentos
e permissões. Antes de confirmar qualquer atendimento, o sistema verifica se
cliente, profissional e, quando necessário, sala e equipamento estão livres no
mesmo intervalo.
</p>

## Objetivos

<p align = "justify">
Centralizar em uma única agenda os atendimentos de diferentes especialidades,
eliminar conflitos de horário e de recursos antes que aconteçam, e reduzir o
trabalho manual de coordenação entre cliente, profissionais e recepção.
</p>

## Descrição do Usuário

| Perfil | Quem é | O que faz na plataforma |
|---|---|---|
| Cliente | Pessoa atendida pelo estabelecimento | Pesquisa profissionais, agenda, reagenda, cancela e acompanha a própria agenda |
| Profissional | Personal trainer, nutricionista, fisioterapeuta e afins | Configura disponibilidade, bloqueia horários e acompanha os atendimentos do dia |
| Recepcionista | Quem atende no balcão | Cria atendimentos em nome do cliente e acompanha a agenda do dia |
| Administrador | Responsável pelo estabelecimento | Gerencia profissionais, serviços, salas, equipamentos, usuários e papéis |

## Recursos do produto

### Conta e acesso

<p align = "justify">
O usuário cria a conta informando nome, e-mail e senha, escolhe o perfil de
cliente, profissional ou recepcionista e pode recuperar a senha por e-mail. O
papel de administrador não é concedido pelo cadastro.
</p>

### Profissionais e serviços

<p align = "justify">
Cada profissional tem especialidade, modalidade de atendimento e apresentação,
além dos serviços que oferece, cada um com a duração que define o horário de
término do atendimento.
</p>

### Agendamento

<p align = "justify">
O cliente escolhe o serviço e um dos horários livres, podendo indicar sala e
equipamentos. É possível repetir o atendimento semanalmente, e cada data da
série é conferida separadamente. Quando o horário não pode ser reservado, a
tela explica o motivo e sugere outros horários.
</p>

### Agenda

<p align = "justify">
Cliente, profissional e recepção têm visões próprias da agenda, com data,
horário, serviço, pessoas envolvidas, local e status do atendimento.
</p>

### Espaços e recursos

<p align = "justify">
Salas e equipamentos são cadastrados pelo administrador. Equipamentos marcados
como exclusivos não podem ser reservados por dois atendimentos no mesmo
intervalo.
</p>

## Restrições

<p align = "justify">
A aplicação não substitui prontuário clínico, não realiza telemedicina, não
emite diagnóstico nem prescrição, não processa convênios ou pagamentos e não
possui aplicativo nativo. Lembretes automáticos e lista de espera foram
classificados como evolução e não fazem parte desta entrega.
</p>

## Referências Bibliográficas

> [Pesquisa do tema](./pesquisa.md)

> [Brainstorm](./Brainstorm.md)

> [Regras de Negócio](../Elaboracao/regras-de-negocio.md)

> BARBOSA, S. D. J.; DA SILVA, B. S. Interação Humano-Computador. Rio de Janeiro: Elsevier, 2010.

## Versionamento

| Data | Versão | Descrição | Autor(es) |
| -- | -- | -- | -- |
| 11/11/2026 | 1.0 | Documento de visão escrito a partir da pesquisa, do brainstorm e do produto implementado | Equipe do projeto |
