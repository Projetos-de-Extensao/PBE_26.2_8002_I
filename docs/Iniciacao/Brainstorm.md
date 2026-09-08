---
id: brainstorm
title: Brainstorm
---

## Introdução
<p align = "justify">
O brainstorm é uma técnica de elicitação de requisitos que consiste em reunir a equipe e discutir sobre diversos tópicos gerais do projeto apresentados no documento problema de negócio. No brainstorm o diálogo é incentivado e críticas são evitadas para permitir que todos colaborem com suas próprias ideias.
</p>

## Metodologia
<p align = "justify">
A equipe se reuniu para debater ideias gerais sobre o projeto via chamada de vídeo, começou pela apresentação do problema de negócio (organização de agendamentos entre clientes e múltiplos profissionais de treinamento, saúde e bem-estar) e terminou com a consolidação dos requisitos elicitados, onde Miguel Esteves foi o moderador, direcionando a equipe com questões pré-elaboradas e transcrevendo as respostas para o documento.
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

---

### 2. Como será o processo para cadastrar um novo cliente?

<p align = "justify">
<b>Miguel Figueira</b> - O cliente deverá se cadastrar informando e-mail e senha, com opção de recuperação de senha em caso de esquecimento.

<b>Miguel Esteves</b> - Após o cadastro, o cliente poderá completar o perfil com preferências de horário e histórico de atendimentos, se já tiver algum.

<b>Kauê Fernandes</b> - O administrador ou a recepção também poderá cadastrar clientes manualmente, para os casos em que o próprio cliente não tem acesso direto ao sistema.
</p>

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

---

### 5. Como seria a forma do cliente realizar um agendamento?

<p align = "justify">
<b>Miguel Figueira</b> - O cliente pesquisa o profissional desejado, visualiza os horários disponíveis e escolhe o que melhor se encaixa na sua agenda.

<b>Miguel Esteves</b> - O cliente também deve conseguir cancelar ou reagendar um atendimento já marcado, com a disponibilidade sendo atualizada imediatamente.

<b>Kauê Fernandes</b> - Para sessões recorrentes, o cliente define a frequência (por exemplo, semanal) e o sistema valida cada ocorrência individualmente contra possíveis conflitos.
</p>

### 6. Quais informações seriam interessante para o cliente?

<p align = "justify">
<b>Miguel Figueira</b> - Informações sobre os próximos atendimentos agendados, com lembretes automáticos antes do horário marcado.

<b>Miguel Esteves</b> - O cliente usuário poderá acessar informações sobre o profissional, como especialidade, avaliações de outros clientes e disponibilidade.

<b>Kauê Fernandes</b> - O cliente poderá ver seu histórico de atendimentos, favoritar profissionais e entrar em uma lista de espera quando não houver horário disponível.
</p>

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

## Conclusão
<p align = "justify">
Através da aplicação da técnica, foi possível elicitar os primeiros requisitos do projeto, cobrindo o fluxo de cadastro, a organização de profissionais e serviços, o processo de agendamento e as necessidades de informação do cliente.
</p>

## Referências Bibliográficas

> BARBOSA, S. D. J; DA SILVA, B. S. Interação humano-computador. Elsevier, 2010.


## Autor(es)
| Data | Versão | Descrição | Autor(es) |
| -- | -- | -- | -- |
| 08/09/2026 | 1.0 | Criação do documento | Miguel Figueira, Miguel Esteves e Kauê Fernandes |
