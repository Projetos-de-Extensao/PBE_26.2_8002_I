---
id: casos_de_uso
title: LEVANTAMENTO DE REQUISITOS E CASO DE USO
---

## Introdução

<p align = "justify">
Este documento aplica ao projeto real — a Plataforma Web de Agendamento Multidisciplinar — o roteiro de elicitação e representação de casos de uso. Ele organiza os stakeholders, os requisitos funcionais e não funcionais já levantados, detalha os fluxos de uso mais relevantes, apresenta o diagrama de casos de uso em UML/PlantUML, referencia o protótipo de baixa fidelidade e define critérios de validação.
</p>

## Metodologia

<p align = "justify">
O conteúdo foi derivado da <a href="../Iniciacao/pesquisa.md">pesquisa do tema</a>, do <a href="../Iniciacao/documento_de_visao.md">documento de visão</a>, dos <a href="#2-requisitos-funcionais">requisitos funcionais</a>, dos <a href="#3-requisitos-nao-funcionais">requisitos não funcionais</a>, das <a href="./regras-de-negocio.md">regras de negócio</a> e do <a href="./prototipos_baixa_fidelidade_md/index.md">protótipo de baixa fidelidade</a>, seguindo a estrutura de roteiro: stakeholders, requisitos, caso de uso detalhado, diagrama, protótipo e validação.
</p>

## 1. Identificação dos Stakeholders

- **Clientes:** pessoas que buscam agendar atendimentos com personal trainers, nutricionistas, fisioterapeutas e outros profissionais de saúde, treinamento e bem-estar.
- **Profissionais:** personal trainers, nutricionistas, fisioterapeutas e demais profissionais autorizados, que oferecem serviços, configuram disponibilidade e atendem clientes.
- **Recepcionistas:** usuários responsáveis pela operação da agenda em nome de clientes e profissionais dentro de academias, clínicas e estúdios.
- **Administradores:** gerenciam cadastros de profissionais, serviços, salas, recursos e permissões da organização.
- **Sistema (ator de apoio):** valida conflitos de horário, sala e recurso antes de confirmar qualquer operação de agenda.

## 2. Requisitos Funcionais

| ID | Descrição | Prioridade |
|---|---|---|
| RF01 | O sistema deve permitir cadastro de usuários. | Alta |
| RF02 | O sistema deve permitir autenticação por e-mail e senha. | Alta |
| RF03 | O sistema deve permitir recuperação de senha. | Alta |
| RF04 | O administrador deve cadastrar e gerenciar profissionais. | Alta |
| RF05 | O administrador deve cadastrar e gerenciar serviços. | Alta |
| RF06 | O administrador deve cadastrar salas e recursos. | Média |
| RF07 | O profissional deve configurar sua disponibilidade. | Alta |
| RF08 | O cliente deve pesquisar profissionais. | Alta |
| RF09 | O cliente deve visualizar horários disponíveis. | Alta |
| RF10 | O cliente deve realizar agendamentos. | Alta |
| RF11 | O cliente deve cancelar seus agendamentos permitidos. | Média |
| RF12 | O cliente deve reagendar seus atendimentos permitidos. | Média |
| RF13 | O sistema deve impedir conflito de horário do profissional. | Alta |
| RF14 | O sistema deve impedir conflito de horário do cliente. | Alta |
| RF15 | O sistema deve impedir conflito de sala ou recurso exclusivo. | Alta |
| RF16 | O sistema deve permitir agendamentos recorrentes. | Média |
| RF17 | O sistema deve exibir a agenda do cliente. | Alta |
| RF18 | O sistema deve exibir a agenda do profissional. | Alta |
| RF19 | O sistema deve controlar permissões conforme o papel do usuário. | Alta |
| RF20 | O profissional deve poder bloquear horários. | Média |
| RF21 | O sistema poderá enviar lembretes de atendimento (evolução do MVP). | Baixa |
| RF22 | O sistema poderá oferecer lista de espera (evolução do MVP). | Baixa |
| RF23 | O administrador deve consultar informações operacionais básicas. | Baixa |
| RF24 | O sistema deve registrar o status do atendimento. | Média |
| RF25 | A recepção deve poder criar, reagendar ou cancelar agendamentos dentro de suas permissões. | Média |
| RF26 | O sistema deve informar o motivo de um conflito e permitir nova seleção de horário. | Alta |

> Prioridades alinhadas ao [backlog do projeto](../Construcao/github_projects.md).

## 3. Requisitos Não Funcionais

**Desempenho e Integridade:** o banco de dados deve manter integridade entre usuários, profissionais, horários e recursos (RNF05); conflitos devem ser validados antes de confirmar qualquer agendamento (RNF06); operações críticas de agenda devem ser validadas no back-end, não apenas na interface (RNF13); datas e horários devem ser registrados de forma consistente para evitar divergências (RNF14).

**Segurança e Privacidade:** senhas não devem ser armazenadas em texto puro (RNF03); todo acesso deve respeitar autenticação e autorização (RNF04); dados pessoais e sensíveis devem ter acesso restrito aos perfis autorizados (RNF10); o sistema deve coletar somente os dados necessários ao escopo (RNF11); credenciais e segredos de infraestrutura não devem ser versionados em repositório público (RNF12).

**Usabilidade:** a interface deve ser responsiva para desktop, tablet e celular (RNF01); as páginas principais devem ter navegação simples e consistente (RNF02); erros devem apresentar mensagens compreensíveis ao usuário (RNF09).

**Manutenibilidade:** código e documentação devem ser versionados com Git (RNF07); a aplicação deve possuir organização modular para facilitar manutenção (RNF08).

## 4. Casos de Uso

### UC01 - Autenticar-se / Criar Conta

**Atores:** Cliente, Profissional, Recepcionista, Administrador, Sistema.

**Pré-condição:** Usuário possui um e-mail válido; se já cadastrado, conhece sua senha.

**Fluxo Principal:**
1. Usuário informa e-mail e senha na tela de login.
2. Sistema valida as credenciais.
3. Sistema redireciona o usuário para a área correspondente ao seu papel.

**Fluxos Alternativos:**
- FA1: Usuário sem conta → usuário seleciona "Criar conta", informa nome, e-mail, senha e perfil; sistema cria a conta associada a um papel (RF01, RF19).
- FA2: Senha esquecida → usuário seleciona "Esqueci minha senha"; sistema inicia fluxo de recuperação (RF03).
- FA3: Credenciais inválidas → sistema informa o erro de forma compreensível e permite nova tentativa (RNF09).

**Pós-condição:** Usuário autenticado e com acesso às funcionalidades permitidas ao seu papel.

### UC02 - Realizar Agendamento

**Atores:** Cliente, Sistema.

**Pré-condição:** Cliente autenticado.

**Fluxo Principal:**
1. Cliente pesquisa profissionais por especialidade, modalidade e local (RF08).
2. Cliente seleciona um profissional e consulta os serviços oferecidos.
3. Cliente consulta horários disponíveis compatíveis com a disponibilidade do profissional (RF09).
4. Cliente escolhe serviço, data e horário e confirma o pedido de agendamento (RF10).
5. Sistema valida conflito de horário do cliente, do profissional e de sala/recurso exclusivo (RF13, RF14, RF15).
6. Sistema confirma o agendamento e atualiza a agenda do cliente e do profissional (RF17, RF18).

**Fluxos Alternativos:**
- FA1: Conflito detectado → sistema informa o motivo do conflito e sugere horários alternativos (RF26).
- FA2: Cliente marca a opção de repetição semanal → sistema trata o pedido como recorrência e valida cada ocorrência individualmente, sem sobrescrever reservas existentes (RF16, RN11, RN12).

**Pós-condição:** Agendamento (ou série de ocorrências) confirmado e refletido nas agendas do cliente e do profissional; status do atendimento registrado (RF24).

### UC03 - Configurar Disponibilidade e Bloquear Horários

**Atores:** Profissional.

**Pré-condição:** Profissional autenticado.

**Fluxo Principal:**
1. Profissional acessa o painel de disponibilidade.
2. Profissional informa os horários em que está disponível para atendimento (RF07).
3. Profissional pode bloquear um período específico, informando o motivo (RF20).
4. Sistema atualiza a disponibilidade exibida aos clientes na busca (RF08, RF09).

**Fluxos Alternativos:**
- FA1: Bloqueio conflita com um agendamento já confirmado → sistema alerta o profissional antes de aplicar o bloqueio (RN13).

**Pós-condição:** Disponibilidade e bloqueios atualizados e considerados nas próximas buscas e validações de conflito.

### UC04 - Reagendar ou Cancelar Atendimento

**Atores:** Cliente, Profissional responsável pelo atendimento, Recepcionista,
Administrador, Sistema.

**Ator principal:** Cliente dono do atendimento. O profissional associado, a
recepção ou o administrador também podem operar o atendimento conforme as
permissões implementadas.

**Pré-condição:** Ator autenticado e autorizado sobre o atendimento; existe um
atendimento futuro com status agendado ou confirmado.

**Fluxo Principal:**
1. Ator seleciona o atendimento na agenda ou informa seu identificador.
2. Ator escolhe reagendar ou cancelar.
3. Em caso de cancelamento, sistema cancela a sessão ou, quando solicitado,
   as sessões futuras ativas da recorrência (RN10).
4. Em caso de reagendamento, sistema consulta horários livres (UC06), recebe a
   nova data e o horário e repete a validação de conflitos (RF13, RF14, RF15).
5. Sistema atualiza o atendimento e libera o horário anterior somente depois
   que o novo horário passa pelas validações.

**Fluxos Alternativos:**
- FA1: Novo horário em conflito → sistema recusa a alteração e mantém o
  atendimento original; o ator pode consultar novamente os horários disponíveis (RF26).
- FA2: Atendimento cancelado, concluído ou passado → sistema impede a alteração.
- FA3: Ação fora das permissões do papel do ator → sistema bloqueia a operação (RF19, RN14).

**Pós-condição:** Atendimento cancelado ou reagendado; agendas do cliente e do profissional atualizadas; status do atendimento refletido (RF24).

**Observação de implementação:** A interface de cancelamento e reagendamento
está na agenda do cliente. As rotas protegidas também autorizam o profissional
do atendimento, a recepção e o administrador; a agenda da recepção ainda não
apresenta controles próprios para essas operações.

### UC05 - Gerenciar Cadastros e Permissões

**Atores:** Administrador.

**Pré-condição:** Administrador autenticado com permissão de gestão (RN09).

**Fluxo Principal:**
1. Administrador cadastra ou edita profissionais (RF04).
2. Administrador cadastra ou edita serviços, definindo nome, tipo e duração (RF05).
3. Administrador cadastra salas e recursos, incluindo recursos exclusivos (RF06).
4. Administrador define papéis e permissões de acesso dos usuários (RF19).
5. Administrador consulta informações operacionais básicas, como agendamentos do dia e ocupação de salas (RF23).

**Fluxos Alternativos:**
- FA1: Dados obrigatórios ausentes no cadastro → sistema impede o salvamento e indica os campos pendentes (RNF09).

**Pós-condição:** Cadastros de profissionais, serviços, salas, recursos e permissões atualizados e disponíveis para os demais casos de uso.

### UC06 - Consultar Horários para Reagendamento

**Atores:** Cliente, Profissional, Recepcionista, Administrador, Sistema.

**Ator principal:** Cliente dono do atendimento. O profissional
responsável pelo atendimento, a recepção ou o administrador também podem fazer a
consulta conforme suas permissões.

**Pré-condição:** Ator autenticado e autorizado a operar o atendimento; o
atendimento está ativo e ainda não ocorreu.

**Fluxo Principal:**
1. Ator seleciona um atendimento futuro que deseja reagendar (UC04).
2. Ator informa a nova data desejada.
3. Sistema verifica se o atendimento pode ser alterado e consulta os horários
   disponíveis para o profissional e o serviço.
4. Sistema desconsidera o próprio atendimento ao verificar conflitos e também
   verifica a disponibilidade da sala e dos recursos já vinculados.
5. Sistema retorna os horários livres para que o ator escolha um deles.

**Fluxos Alternativos:**
- FA1: Data ausente ou em formato inválido → sistema informa o erro e solicita
  uma data válida.
- FA2: Atendimento cancelado, concluído ou passado → sistema informa que não é
  possível reagendá-lo.
- FA3: Ator sem permissão sobre o atendimento → sistema não revela os dados do
  atendimento e bloqueia a consulta (RF19, RN14).
- FA4: Nenhum horário compatível → sistema retorna a lista vazia; o atendimento
  original permanece inalterado.

**Pós-condição:** Horários disponíveis apresentados; nenhum dado do atendimento
é alterado até a confirmação do reagendamento (UC04).

### Limite de escopo: responsável legal por aluno menor

O sistema atual não coleta data de nascimento, não verifica a idade do aluno e
não mantém cadastro ou vínculo de responsável legal. Portanto, não há fluxo de
autorização ou operação por responsável legal para menores de idade nesta
entrega. O administrador mencionado nos casos de uso é o administrador do
estabelecimento e não substitui um responsável legal.

> A documentação Swagger em `/docs/` lista as rotas do Django, incluindo páginas
> HTML, e apresenta os schemas dos modelos como referência. Isso não significa
> que todos os modelos tenham operações CRUD expostas por uma API REST.

## 5. Diagrama de Casos de Uso

Diagrama de Caso de Uso (UML) representando os fluxos acima, em PlantUML:

```plantuml
@startuml AgendamentoMultidisciplinar_CasosDeUso

left to right direction
skinparam actorStyle awesome

actor Cliente
actor Profissional
actor Recepcionista
actor Administrador
actor "Sistema" as Sistema

usecase (UC01: Autenticar-se / Criar Conta) as UC01

usecase (UC02: Realizar Agendamento) as UC02
usecase (Pesquisar Profissionais) as UC02_1
usecase (Consultar Horários) as UC02_2
usecase (Selecionar Serviço e Horário) as UC02_3
usecase (Confirmar Agendamento) as UC02_4
usecase (Validar Conflitos) as UC02_V
usecase (Sugerir Horários Alternativos) as FA_Conflito
usecase (Tratar Recorrência) as FA_Recorrencia

usecase (UC03: Configurar Disponibilidade) as UC03
usecase (Bloquear Horário) as UC03_1

usecase (UC04: Reagendar ou Cancelar Atendimento) as UC04

usecase (UC05: Gerenciar Cadastros e Permissões) as UC05
usecase (UC06: Consultar Horários para Reagendamento) as UC06

Cliente --> UC01
Profissional --> UC01
Recepcionista --> UC01
Administrador --> UC01

Cliente --> UC02
UC02 --> UC02_1
UC02 --> UC02_2
UC02 --> UC02_3
UC02 --> UC02_4
UC02_4 --> UC02_V : <<include>>
UC02_V --> Sistema
FA_Conflito .> UC02_V : <<extend>>
FA_Recorrencia .> UC02_4 : <<extend>>

Profissional --> UC03
UC03 --> UC03_1

Cliente --> UC04
Profissional --> UC04
Recepcionista --> UC04
Administrador --> UC04
UC06 .> UC04 : <<extend>>
UC06 --> UC02_V : <<include>>
UC02_V .> UC04 : <<extend>>

Administrador --> UC05

Cliente --> UC06
Profissional --> UC06
Recepcionista --> UC06
Administrador --> UC06
UC06 --> Sistema

note right of UC02
  **Pré-condição**: Cliente autenticado.
  **Pós-condição**: Agendamento confirmado
  e agendas atualizadas.
end note

@enduml
```

**Explicação:**

- **Atores:** Cliente interage com busca, agendamento e sua própria agenda; Profissional configura disponibilidade e bloqueios e pode operar os próprios atendimentos; Recepcionista opera agendamentos em nome de terceiros; Administrador gerencia cadastros e pode operar atendimentos; Sistema executa a validação de conflitos.
- **Relacionamentos `<<include>>`:** confirmar um agendamento inclui validação de conflitos (UC02); consultar horários também verifica os conflitos para oferecer somente horários livres (UC06).
- **Relacionamentos `<<extend>>`:** consulta de horários (UC06) e validação final de conflitos estendem o UC04 somente quando o ator escolhe reagendar, não quando escolhe cancelar.
- Os fluxos alternativos de conflito e recorrência estendem o fluxo principal apenas quando aplicáveis.

## 6. Protótipo

<p align = "justify">
As telas mínimas para os fluxos acima já estão descritas no <a href="./prototipos_baixa_fidelidade_md/index.md">protótipo de baixa fidelidade</a> (Login, Cadastro, Home do Cliente, Buscar Profissionais, Perfil do Profissional, Novo Agendamento, Conflito de Agendamento, Minha Agenda, Painel do Profissional e Administração). Abaixo, um wireframe complementar em notação Salt (PlantUML) para a tela de Novo Agendamento, ponto central do UC02:
</p>

```plantuml
@startsalt
{
  Novo Agendamento
  ..
  Serviço      | "^Avaliação Física^"
  Profissional | "^Ana Silva^"
  Local        | "^Sala 2^"
  Data         | "10/10/2026"
  Horário      | "16:00"
  [ ] Repetir semanalmente
  Até          | "10/12/2026"
  ..
  [ Verificar e Confirmar ]
}
@endsalt
```

## 7. Validação

- **Revisão com stakeholders:** confirmar com profissionais e administradores se o fluxo de recorrência (UC02, FA2) atende à rotina real de clientes fixos.
- **Teste de fluxo com o protótipo:** validar com clientes reais se a sequência buscar → selecionar horário → confirmar é compreensível e se as mensagens de conflito (RF26) são claras.
- **Teste A/B de priorização de resultados na busca:** comparar duas ordenações de profissionais (por proximidade e por avaliação) quando essa funcionalidade for implementada.

## Conclusão

<p align = "justify">
Este documento traduz a pesquisa e os requisitos do projeto em casos de uso concretos, um diagrama de casos de uso e um wireframe complementar, cobrindo os quatro perfis de usuário e o fluxo central de agendamento com prevenção de conflitos. Ele serve de base direta para o diagrama de classes e para a implementação incremental descrita na metodologia e no backlog.
</p>

## Referências

> [Pesquisa do tema](../Iniciacao/pesquisa.md)

> [Documento de visão](../Iniciacao/documento_de_visao.md)

> [Requisitos funcionais](#2-requisitos-funcionais)

> [Requisitos não funcionais](#3-requisitos-nao-funcionais)

> [Regras de negócio](./regras-de-negocio.md)

> [Protótipo de baixa fidelidade](./prototipos_baixa_fidelidade_md/index.md)

> [Backlog no GitHub Projects](../Construcao/github_projects.md)

## Autor(es)

| Data | Versão | Descrição | Autor(es) |
|---|---|---|---|
| 17/09/2026 | 1.0 | Criação dos casos de uso, diagrama de casos de uso e protótipo complementar a partir do roteiro | Equipe do projeto |
| 12/11/2026 | 1.1 | Alinhamento dos casos de uso de reagendamento e consulta de horários às permissões implementadas; registro dos limites de escopo | Equipe do projeto |