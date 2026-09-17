---
id: diagrama_de_casos de uso
title: Diagrama de Casos de Uso
---

## Casos de Uso

### Descrição:

- Contas
	- Criação
	- Entrada
	- Alteração
	- Recuperar Senha
	- Exclusão Lógica
	- Visualização

- Perfis
	- Cliente
	- Profissional
	- Recepcionista
	- Administrador

- Profissionais
	- Cadastro
	- Edição
	- Pesquisa
	- Visualização
	- Inativação

- Serviços
	- Cadastro
	- Duração
	- Modalidade (presencial/online)
	- Vínculo com profissional

- Disponibilidade
	- Configuração de horários
	- Bloqueio de horários
	- Consulta de horários livres

- Agendamentos
	- Criação
	- Recorrência
	- Reagendamento
	- Cancelamento
	- Visualização
	- Validação de conflitos

- Agenda
	- Agenda do Cliente
	- Agenda do Profissional

- Espaços e Recursos
	- Salas
	- Equipamentos
	- Ocupação

- Permissões
	- Papéis
	- Privilégios

### Criação de uma conta no sistema

- Atores:
	- Cliente
	- Sistema

- Pré-Condições:
	- Nenhuma

- Fluxo Básico:
	1. Cliente fornece nome, e-mail, senha e confirmação
	2. Dados do Cliente são validados pelo Sistema
	3. Senha do Cliente é encriptada pelo Sistema
	4. Dados do Cliente são persistidos pelo Sistema
	5. Sistema atribui o perfil de Cliente ao novo usuário
	6. Sistema confirma que o Cadastro foi realizado com sucesso
	7. Sistema redireciona o Cliente para a página de Entrada

- Fluxos Alternativos:
	- 2a. E-mail do Cliente é inválido
		- 2a1. Sistema exibe mensagem de erro
	- 2b. E-mail do Cliente já está cadastrado
		- 2b1. Sistema exibe mensagem de erro e sugere a recuperação de senha
	- 2c. Senha do Cliente não respeita regras de segurança
		- 2c1. Sistema exibe mensagem de erro com os critérios exigidos

### Entrada do usuário no sistema

- Atores:
	- Usuário (Cliente, Profissional, Recepcionista ou Administrador)
	- Sistema

- Pré-Condições:
	- Usuário deve estar cadastrado

- Fluxo Básico:
	1. Usuário fornece e-mail e senha
	2. Sistema autentica o Usuário
	3. Sistema identifica o perfil do Usuário
	4. Sistema libera as funcionalidades permitidas ao perfil
	5. Sistema redireciona o Usuário para a página inicial

- Fluxos Alternativos:
	- 2a. Dados do Usuário inválidos
		- 2a1. Sistema exibe mensagem de erro
	- 2b. Usuário esqueceu a senha
		- 2b1. Sistema envia link de redefinição para o e-mail cadastrado

### Pesquisa de profissionais e serviços

- Atores:
	- Cliente
	- Sistema

- Pré-Condições:
	- Cliente deve estar autenticado

- Fluxo Básico:
	1. Cliente informa filtros de especialidade, serviço ou modalidade
	2. Sistema consulta os profissionais cadastrados
	3. Sistema exibe a lista de profissionais encontrados
	4. Cliente seleciona um profissional
	5. Sistema exibe o perfil com especialidade, formação, serviços e duração

- Fluxos Alternativos:
	- 3a. Nenhum profissional encontrado
		- 3a1. Sistema informa que não há resultados e sugere remover filtros

### Consulta de disponibilidade

- Atores:
	- Cliente
	- Recepcionista
	- Sistema

- Pré-Condições:
	- Profissional deve ter disponibilidade configurada

- Fluxo Básico:
	1. Ator seleciona profissional, serviço e data
	2. Sistema calcula a duração do serviço
	3. Sistema desconsidera os horários ocupados e bloqueados
	4. Sistema exibe os horários livres da data

- Fluxos Alternativos:
	- 4a. Não há horários livres na data
		- 4a1. Sistema sugere as próximas datas com disponibilidade

### Criação de um agendamento

- Atores:
	- Cliente
	- Sistema

- Pré-Condições:
	- Cliente deve estar autenticado
	- Profissional deve possuir horário disponível

- Fluxo Básico:
	1. Cliente escolhe o serviço e o profissional
	2. Cliente escolhe o local, a data e o horário
	3. Sistema calcula o horário de término a partir da duração do serviço
	4. Sistema verifica se o serviço exige sala ou recurso
	5. Sistema valida os conflitos de Cliente, Profissional, sala e recurso
	6. Dados do agendamento são persistidos pelo Sistema
	7. Sistema confirma o agendamento e atualiza as agendas envolvidas

- Fluxos Alternativos:
	- 5a. Profissional já possui atendimento no intervalo
		- 5a1. Sistema exibe mensagem de conflito e oferece outros horários
	- 5b. Cliente já possui atendimento no intervalo
		- 5b1. Sistema exibe mensagem de conflito e solicita outro horário
	- 5c. Sala ou recurso indisponível no intervalo
		- 5c1. Sistema informa a indisponibilidade e sugere outro horário ou local

### Criação de agendamentos recorrentes

- Atores:
	- Cliente
	- Sistema

- Pré-Condições:
	- Cliente deve estar autenticado

- Fluxo Básico:
	1. Cliente escolhe o serviço, o profissional, os dias da semana e o horário
	2. Cliente informa o período de repetição
	3. Sistema gera as ocorrências do período
	4. Sistema valida cada ocorrência individualmente
	5. Sistema exibe o resumo das ocorrências válidas e das que possuem conflito
	6. Cliente confirma a criação
	7. Sistema persiste as sessões confirmadas

- Fluxos Alternativos:
	- 5a. Parte das ocorrências apresenta conflito
		- 5a1. Cliente opta por agendar somente as ocorrências válidas
		- 5a2. Cliente opta por alterar o horário da série

### Reagendamento de um atendimento

- Atores:
	- Cliente
	- Recepcionista
	- Sistema

- Pré-Condições:
	- Deve existir atendimento futuro confirmado

- Fluxo Básico:
	1. Ator seleciona o atendimento e solicita o reagendamento
	2. Sistema exibe os horários disponíveis
	3. Ator escolhe o novo horário
	4. Sistema valida os conflitos do novo horário
	5. Sistema atualiza o atendimento
	6. Sistema libera o horário anterior

- Fluxos Alternativos:
	- 4a. Novo horário em conflito
		- 4a1. Sistema exibe mensagem de erro e mantém o agendamento original

### Cancelamento de um atendimento

- Atores:
	- Cliente
	- Recepcionista
	- Sistema

- Pré-Condições:
	- Deve existir atendimento futuro confirmado

- Fluxo Básico:
	1. Ator seleciona o atendimento e solicita o cancelamento
	2. Sistema solicita a confirmação da operação
	3. Ator confirma o cancelamento
	4. Sistema altera o status do atendimento para cancelado
	5. Sistema libera o horário, a sala e o recurso reservados

- Fluxos Alternativos:
	- 2a. Atendimento pertence a uma recorrência
		- 2a1. Sistema pergunta se o cancelamento vale para a ocorrência ou para toda a série

### Visualização da agenda

- Atores:
	- Cliente
	- Profissional
	- Sistema

- Pré-Condições:
	- Usuário deve estar autenticado

- Fluxo Básico:
	1. Usuário acessa a sua agenda
	2. Sistema consulta os atendimentos do período
	3. Sistema exibe data, horário, serviço, local e status de cada atendimento
	4. Usuário filtra os atendimentos por período ou status

- Fluxos Alternativos:
	- 3a. Não há atendimentos no período
		- 3a1. Sistema exibe a agenda vazia e o atalho para novo agendamento

### Configuração da disponibilidade do profissional

- Atores:
	- Profissional
	- Sistema

- Pré-Condições:
	- Profissional deve estar autenticado

- Fluxo Básico:
	1. Profissional informa os dias e as faixas de horário de atendimento
	2. Profissional vincula os serviços que oferece
	3. Sistema valida as faixas informadas
	4. Sistema persiste a disponibilidade
	5. Sistema passa a exibir os horários na consulta dos Clientes

- Fluxos Alternativos:
	- 3a. Faixas de horário sobrepostas
		- 3a1. Sistema exibe mensagem de erro e solicita correção
	- 4a. Redução de disponibilidade com atendimentos já marcados
		- 4a1. Sistema lista os atendimentos afetados antes de salvar

### Bloqueio de horários pelo profissional

- Atores:
	- Profissional
	- Sistema

- Pré-Condições:
	- Profissional deve estar autenticado

- Fluxo Básico:
	1. Profissional seleciona o período a ser bloqueado
	2. Profissional informa o motivo do bloqueio
	3. Sistema verifica se há atendimentos no período
	4. Sistema registra o bloqueio
	5. Sistema retira os horários da consulta de disponibilidade

- Fluxos Alternativos:
	- 3a. Existem atendimentos marcados no período
		- 3a1. Sistema exibe a lista e solicita reagendamento ou cancelamento antes do bloqueio

### Operação da agenda pela recepção

- Atores:
	- Recepcionista
	- Sistema

- Pré-Condições:
	- Recepcionista deve estar autenticado

- Fluxo Básico:
	1. Recepcionista cadastra o Cliente com os dados básicos
	2. Recepcionista consulta a disponibilidade dos profissionais
	3. Recepcionista cria, reagenda ou cancela atendimentos em nome do Cliente
	4. Sistema aplica as mesmas validações de conflito do agendamento

- Fluxos Alternativos:
	- 1a. Cliente já possui cadastro
		- 1a1. Sistema exibe o cadastro existente
	- 3a. Recepcionista tenta acessar função administrativa
		- 3a1. Sistema nega o acesso por falta de privilégio

### Gerenciamento de profissionais e serviços

- Atores:
	- Administrador
	- Sistema

- Pré-Condições:
	- Administrador deve estar autenticado

- Fluxo Básico:
	1. Administrador cadastra o Profissional com especialidade, formação e modalidade
	2. Administrador cadastra os serviços com a respectiva duração
	3. Administrador vincula os serviços aos profissionais
	4. Sistema valida e persiste os dados

- Fluxos Alternativos:
	- 1a. Profissional já cadastrado
		- 1a1. Sistema exibe mensagem de duplicidade
	- 2a. Exclusão de serviço com atendimentos futuros
		- 2a1. Sistema impede a exclusão e sugere a inativação

### Gerenciamento de espaços e recursos

- Atores:
	- Administrador
	- Sistema

- Pré-Condições:
	- Administrador deve estar autenticado

- Fluxo Básico:
	1. Administrador cadastra salas, consultórios, estúdios e equipamentos
	2. Administrador indica os recursos de uso exclusivo
	3. Administrador vincula os recursos aos serviços que os exigem
	4. Sistema persiste os dados
	5. Administrador consulta a ocupação dos recursos ao longo do dia

- Fluxos Alternativos:
	- 2a. Recurso em uso no período da inativação
		- 2a1. Sistema lista os atendimentos afetados

### Gerenciamento de usuários e permissões

- Atores:
	- Administrador
	- Sistema

- Pré-Condições:
	- Administrador deve estar autenticado

- Fluxo Básico:
	1. Administrador consulta os usuários cadastrados
	2. Administrador atribui ou altera o perfil do usuário
	3. Sistema aplica os privilégios correspondentes ao perfil
	4. Administrador realiza a exclusão lógica do usuário quando necessário

- Fluxos Alternativos:
	- 2a. Administrador tenta remover o próprio privilégio
		- 2a1. Sistema impede a operação
