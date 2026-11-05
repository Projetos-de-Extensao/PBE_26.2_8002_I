---
title: Papéis e Permissões
---

# Papéis e permissões

Este documento define os papéis previstos para o sistema e as regras de acesso associadas a cada perfil. A ideia central é garantir que cada ação do sistema seja executada apenas por usuários com autorização adequada, conforme as regras de negócio RN08 e RN09.

## Objetivo

Estabelecer uma política clara de autorização para o sistema, separando responsabilidades entre cliente, profissional, recepcionista e administrador. As verificações de permissão devem ocorrer no backend, e não apenas na interface, para evitar acesso indevido por manipulação da tela.

## Regras gerais

- A autenticação é obrigatória para ações sensíveis.
- As funções de administração exigem conta ativa e papel específico.
- Usuários sem autorização adequada recebem resposta de acesso negado.
- A navegação pública pode existir para informações abertas, mas qualquer ação de alteração ou gestão exige permissão explícita.

## Matriz de papéis e permissões

| Papel | Permissões principais | Limitações |
|---|---|---|
| Cliente | Pesquisar profissionais, consultar perfis, visualizar o próprio histórico de atendimentos, solicitar e cancelar agendamentos próprios, editar os próprios dados básicos. | Não acessa agenda de terceiros, não gerencia profissionais, serviços, salas ou equipamentos, e não entra no painel administrativo. |
| Profissional | Consultar o próprio perfil público, atualizar dados profissionais e de contato, responder a consultas, manter sua disponibilidade e agenda. | Não acessa dados de clientes em contexto administrativo nem realiza gestão de usuários e configuração do sistema. |
| Recepcionista | Atualizar dados próprios, auxiliar no atendimento e acompanhar a agenda operacional. | Não acessa o painel administrativo completo. As operações de agenda em nome de clientes previstas em RF25 dependem de evolução da aplicação. |
| Administrador | Gerenciar usuários, papéis, profissionais, serviços, salas, equipamentos e configurações do sistema pelo painel administrativo. | Requer conta ativa e autorização de equipe; o acesso administrativo não é concedido por simples cadastro no sistema. |

## Permissões por contexto

### Acesso público

As páginas de busca e perfil público dos profissionais podem ser consultadas sem autenticação. Essa abertura serve para descoberta do serviço, mas não permite edição ou gerenciamento de dados privados.

### Acesso autenticado

Ações como agendamento, consulta de histórico, edição de perfil e organização de agenda exigem que o usuário esteja autenticado e tenha o papel adequado para a operação.

### Acesso administrativo

O painel de gestão em `/administracao/` permite:

- cadastrar e editar profissionais;
- cadastrar serviços, salas e equipamentos;
- monitorar agendamentos do dia;
- verificar ocupação dos recursos;
- gerenciar contas e atribuição de papéis.

A validação do admnistrador deve verificar, além do papel, a ativação da conta e a autorização de acesso à equipe.

## Conta de demonstração

Para criar contas locais de demonstração dos quatro papéis, execute:

```bash
python manage.py criar_usuarios_demo
```

Esse comando gera senhas aleatórias e as exibe uma única vez no terminal. As contas criadas são:

- `cliente@gmail.com`
- `profissional@gmail.com`
- `recepcionista@gmail.com`
- `admin@gmail.com`

O comando não altera contas existentes e não deve ser usado em ambiente de produção.

## Referências

- [Regras de Negócio](./regras-de-negocio.md): RN08, RN09 e RN14.
- [Levantamento de Requisitos](./levreq.md): RF19 e RF25.
