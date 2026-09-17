---
id: brainstorm
title: Brainstorm
---

## Introdução

<p align = "justify">
O brainstorm é uma técnica de elicitação e ideação utilizada para gerar possibilidades antes de priorizá-las. Neste projeto, a técnica foi estruturada a partir dos problemas, usuários e limites identificados na pesquisa do tema.
</p>

## Metodologia

<p align = "justify">
A equipe se reuniu para debater ideias gerais sobre o projeto via chamada de vídeo, começou pela apresentação do problema de negócio (organização de agendamentos entre clientes e múltiplos profissionais de treinamento, saúde e bem-estar) e terminou com a consolidação dos requisitos elicitados, onde Miguel Esteves foi o moderador, direcionando a equipe com questões pré-elaboradas e transcrevendo as respostas para o documento.

Após a geração das ideias, as respostas foram sintetizadas em listas, agrupadas por tema e priorizadas para o MVP, separando o que fica para evoluções futuras.
</p>

## Brainstorm

## Versão 1.0

## Perguntas

### 1. Qual o objetivo principal da aplicação?

<p align = "justify">
<b>Miguel Figueira</b> - Deve ser uma plataforma onde qualquer pessoa possa organizar, agendar e acompanhar seus atendimentos com profissionais de treinamento, saúde e bem-estar em um único ambiente.

<b>Miguel Esteves</b> - A plataforma deve fornecer um espaço centralizado para que clientes marquem sessões com personal trainers, nutricionistas, fisioterapeutas e outros profissionais, sem precisar controlar várias agendas separadas.

<b>Kauê Fernandes</b> - O objetivo da aplicação é reduzir conflitos de horário e facilitar o trabalho de profissionais e recepcionistas, automatizando o que hoje é feito por planilhas ou mensagens.
</p>

Ideias relacionadas:

- agenda única do cliente;
- agenda por profissional;
- busca por especialidade;
- serviços com duração definida;
- visualização de horários livres;
- experiência web responsiva.

---

### 2. Como será o processo para cadastrar um novo cliente?

<p align = "justify">
<b>Miguel Figueira</b> - O cliente deverá se cadastrar informando e-mail e senha, com opção de recuperação de senha em caso de esquecimento.

<b>Miguel Esteves</b> - Após o cadastro, o cliente poderá completar o perfil com preferências de horário e histórico de atendimentos, se já tiver algum.

<b>Kauê Fernandes</b> - O administrador ou a recepção também poderá cadastrar clientes manualmente, para os casos em que o próprio cliente não tem acesso direto ao sistema.
</p>

Fluxo inicial:

1. criar conta;
2. informar e-mail e senha;
3. confirmar dados básicos;
4. selecionar perfil de cliente;
5. acessar a página inicial;
6. pesquisar profissionais e serviços.

A aplicação deverá coletar apenas os dados necessários para o funcionamento do serviço.

---

### 3. Como será a forma de organizar os serviços e os profissionais?

<p align = "justify">
<b>Miguel Figueira</b> - O administrador deve cadastrar os profissionais, informando especialidade, formação e se o atendimento é presencial ou online.

<b>Miguel Esteves</b> - Cada serviço oferecido por um profissional deve ter uma duração definida, para que a agenda calcule automaticamente o horário de término.

<b>Kauê Fernandes</b> - O profissional deve configurar sua própria disponibilidade, indicando os dias e horários em que pode atender.
</p>

---

### 4. Outras perguntas pertinentes ao contexto

<p align = "justify">
<b>Miguel Figueira</b> - Com a localização e o tipo de atendimento (presencial ou online), o sistema deve saber se é necessário reservar uma sala ou recurso físico.

<b>Miguel Esteves</b> - O sistema deve impedir que a mesma sala, recurso ou profissional seja reservado duas vezes no mesmo intervalo de tempo.

<b>Kauê Fernandes</b> - O administrador precisa conseguir cadastrar salas e equipamentos e acompanhar a ocupação desses recursos ao longo do dia.
</p>

Regras sugeridas para evitar conflitos:

- impedir dois atendimentos do mesmo profissional no mesmo intervalo;
- impedir dois atendimentos do mesmo cliente no mesmo intervalo;
- impedir dupla reserva de sala;
- impedir dupla reserva de recurso exclusivo;
- validar cada ocorrência de uma recorrência;
- informar ao usuário quando houver conflito.

---

### 5. Como seria a forma do cliente realizar um agendamento?

<p align = "justify">
<b>Miguel Figueira</b> - O cliente pesquisa o profissional desejado, visualiza os horários disponíveis e escolhe o que melhor se encaixa na sua agenda.

<b>Miguel Esteves</b> - O cliente também deve conseguir cancelar ou reagendar um atendimento já marcado, com a disponibilidade sendo atualizada imediatamente.

<b>Kauê Fernandes</b> - Para sessões recorrentes, o cliente define a frequência (por exemplo, semanal) e o sistema valida cada ocorrência individualmente contra possíveis conflitos.
</p>

Possibilidades levantadas:

- calendário de horários;
- duração automática de acordo com o serviço;
- recorrência semanal;
- confirmação;
- reagendamento;
- cancelamento;
- status do atendimento.

---

### 6. Quais informações seriam interessante para o cliente?

<p align = "justify">
<b>Miguel Figueira</b> - Informações sobre os próximos atendimentos agendados, com lembretes automáticos antes do horário marcado.

<b>Miguel Esteves</b> - O cliente usuário poderá acessar informações sobre o profissional, como especialidade, avaliações de outros clientes e disponibilidade.

<b>Kauê Fernandes</b> - O cliente poderá ver seu histórico de atendimentos, favoritar profissionais e entrar em uma lista de espera quando não houver horário disponível.
</p>

Informações levantadas:

- nome do profissional;
- especialidade;
- serviços;
- modalidade (presencial ou online);
- local;
- duração;
- disponibilidade;
- valor, caso essa informação faça parte da versão do produto;
- próximos atendimentos;
- histórico de agendamentos.

---

### 7. Como funcionará o controle de privilégios?

<p align = "justify">
O sistema terá papéis distintos para evitar que todos os usuários possuam as mesmas permissões.
</p>

- **Cliente:** gerencia seus próprios agendamentos.
- **Profissional:** gerencia disponibilidade, bloqueia horários e consulta sua agenda.
- **Recepcionista:** realiza as operações de agenda e cadastro permitidas, sem acesso administrativo completo.
- **Administrador:** gerencia usuários, profissionais, serviços, espaços, recursos e permissões.

---

### 8. Quais automações podem reduzir trabalho manual?

- lembrete de atendimento;
- confirmação automática;
- recorrência;
- bloqueio de conflitos;
- liberação de horário após cancelamento;
- lista de espera;
- aviso de nova vaga;
- integração futura com calendário externo.

---

### 9. O que deve ficar fora do MVP?

- prontuário clínico completo;
- telemedicina;
- diagnóstico;
- prescrição por IA;
- convênios;
- pagamentos avançados;
- aplicativo mobile nativo;
- integrações complexas.

---

### Requisitos elicitados

|ID|Descrição|
|----|-------------|
|BS01| O cliente deve se cadastrar com e-mail e senha, com opção de recuperação de senha.|
|BS02| O cliente deve pesquisar profissionais por especialidade e disponibilidade.|
|BS03| O cliente deve visualizar horários disponíveis antes de agendar.|
|BS04| O cliente deve conseguir cancelar ou reagendar um atendimento.|
|BS05| O cliente deve poder agendar sessões recorrentes.|
|BS06| O cliente deve receber lembretes automáticos antes do atendimento.|
|BS07| O cliente deve poder favoritar profissionais e consultar histórico de atendimentos.|
|BS08| O cliente deve poder entrar em uma lista de espera quando não houver horário disponível.|
|BS09| O cliente deve visualizar avaliações e informações do perfil do profissional.|
|BS10| O profissional deve configurar sua própria disponibilidade de horários.|
|BS11| O profissional deve ter cadastro de especialidade, formação e tipo de atendimento (presencial ou online).|
|BS12| O administrador deve cadastrar profissionais, serviços, salas e recursos.|
|BS13| O sistema deve impedir conflito de horário entre cliente, profissional, sala ou recurso.|
|BS14| O sistema deve calcular automaticamente o horário de término com base na duração do serviço.|
|BS15| O administrador deve acompanhar a ocupação de salas e recursos ao longo do dia.|
|BS16| O sistema deve aplicar permissões de acordo com o papel do usuário (cliente, profissional, recepcionista e administrador).|
|BS17| O profissional deve poder bloquear horários na sua agenda.|
|BS18| O cliente e o profissional devem possuir uma visão de agenda com seus atendimentos.|
|BS19| A recepção deve poder cadastrar clientes e operar agendamentos sem acesso administrativo completo.|

> **Priorização:** os requisitos de lembretes (BS06), favoritos (BS07), lista de espera (BS08) e avaliações (BS09) são tratados como evolução do MVP. O núcleo do produto é o fluxo de agendamento com prevenção de conflitos.

## Conclusão

<p align = "justify">
Através da aplicação da técnica, foi possível elicitar os primeiros requisitos do projeto, cobrindo o fluxo de cadastro, a organização de profissionais e serviços, o processo de agendamento e as necessidades de informação do cliente. A síntese das ideias permitiu ainda definir o controle de privilégios, as automações desejadas e os limites do MVP, priorizando o fluxo de agendamento e a prevenção de conflitos como núcleo do produto.
</p>

## Referências Bibliográficas

> BARBOSA, S. D. J.; DA SILVA, B. S. Interação Humano-Computador. Elsevier, 2010.

> [Pesquisa do tema](./pesquisa.md)

## Autor(es)

| Data | Versão | Descrição | Autor(es) |
| -- | -- | -- | -- |
| 08/09/2026 | 1.0 | Criação do documento | Miguel Figueira, Miguel Esteves e Kauê Fernandes |
| 16/09/2026 | 1.1 | Junção das falas da equipe com a síntese das ideias; inclusão das perguntas 7 a 9 e dos requisitos BS16 a BS19 | Miguel Figueira, Miguel Esteves e Kauê Fernandes |
