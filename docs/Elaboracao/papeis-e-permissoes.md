---
title: Papéis e Permissões
---

# Papéis e permissões

O acesso é definido pelo papel associado ao perfil de cada usuário (RN08). As
permissões são verificadas no servidor, não apenas pela presença ou ausência de
links na interface.

| Papel | Pode fazer | Limites |
|---|---|---|
| Cliente | Pesquisar profissionais, consultar perfis, agendar, consultar e cancelar os próprios atendimentos, e editar o próprio nome e telefone. | Não acessa a agenda de outras pessoas nem o painel administrativo. |
| Profissional | Ter o perfil público consultado e editar o próprio nome, telefone, especialidade e apresentação. | Não acessa a agenda de clientes nem gerencia cadastros administrativos. |
| Recepcionista | Editar o próprio nome e telefone. | Não acessa o painel administrativo. As operações de agenda em nome de clientes previstas em RF25 ainda não estão disponíveis na aplicação. |
| Administrador | Gerenciar usuários, papéis, profissionais, serviços, salas e equipamentos pelo painel administrativo. | O painel exige uma conta ativa, com acesso de equipe e papel de administrador (RN09). |

As páginas de busca e de perfil público dos profissionais podem ser consultadas
sem autenticação. Para ações protegidas, usuários sem o papel exigido recebem
uma resposta de acesso negado; no painel administrativo, o controle também
verifica se a conta está ativa e autorizada.

O painel de gestão em `/administracao/` permite cadastrar e editar profissionais,
serviços, salas e equipamentos. Também resume os agendamentos do dia e a ocupação
de salas e equipamentos. A gestão de contas e a atribuição de papéis estão
disponíveis nos respectivos links do painel.

Para criar contas locais de demonstração dos quatro papéis, execute
`python manage.py criar_usuarios_demo`. O comando gera senhas aleatórias e
mostra cada senha uma única vez no terminal; guarde-as com segurança. Ele cria
as contas `cliente@gmail.com`, `profissional@gmail.com`,
`recepcionista@gmail.com` e `admin@gmail.com`, não altera contas existentes e
não deve ser usado para criar credenciais de produção.

## Referências

- [Regras de Negócio](./regras-de-negocio.md): RN08, RN09 e RN14.
- [Levantamento de Requisitos](./levreq.md): RF19 e RF25.
