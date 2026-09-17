---
id: pesquisa
title: Pesquisa
---

# Pesquisa
### **1. Capa**

- Tema: Plataforma web de agendamento multidisciplinar para treinamento, saúde e bem-estar, em uma academia
- Data: 2026.2
- Stakeholder: Pro-Reitoria Acadêmica

---

### **2. Pesquisa**

**Problema**
Profissionais como personal trainers, nutricionistas, fisioterapeutas e psicologos frequentemente utilizam ferramentas separadas para agenda, comunicação, clientes, pagamentos e controle de espaços. Isso pode gerar conflitos de horário, retrabalho, falta de visibilidade e dificuldade de coordenação quando um mesmo cliente é acompanhado por mais de um profissional.

**Solução proposta**
Criar uma plataforma única em que o cliente possa:

pesquisar profissionais;
consultar disponibilidade;
agendar, reagendar ou cancelar atendimentos;
visualizar uma agenda integrada;
receber lembretes;
acompanhar seus próximos atendimentos.
Para a organização, o sistema também controla:

profissionais;
serviços;
salas e espaços;
recursos/equipamentos;
horários;
recorrências;
permissões;
lista de espera.

**Gestão de ativos e espaços**
O sistema deve permitir cadastrar e controlar recursos físicos necessários a determinados atendimentos.

Exemplos:

sala de avaliação;
consultório;
estúdio de pilates;
sala de fisioterapia;
espaço funcional;
equipamentos específicos.
Regra central
Um agendamento só pode ser confirmado quando cliente, profissional e recurso necessário estiverem disponíveis no mesmo intervalo.

**Agendamento multidisciplinar**
Um cliente poderá ter atendimentos de diferentes especialidades em uma única agenda.

Exemplo:

Dia	Horário	Atendimento
Segunda	16:00	Personal trainer
Terça	14:00	Nutricionista
Quarta	16:00	Personal trainer
Quinta	10:00	Fisioterapeuta
Sexta	16:00	Personal trainer

**Controle de privilégios**
*Cliente*
Pode pesquisar profissionais, agendar, reagendar, cancelar e consultar seus próprios atendimentos.

*Profissional*
Pode configurar disponibilidade, visualizar sua agenda, confirmar atendimentos, bloquear horários e acompanhar seus próprios clientes.

*Recepcionista*
Pode apoiar o cadastro e a operação da agenda, sem acesso administrativo completo.

*Administrador*
Pode gerenciar usuários, profissionais, serviços, espaços, permissões e relatórios.

**Automação e recorrência**
O sistema deve permitir criar sessões recorrentes, por exemplo:

segunda, quarta e sexta;
16:00 às 17:00;
por 12 semanas.
Também pode automatizar:

lembretes;
liberação de horários cancelados;
avisos de vaga;
lista de espera;
detecção de conflitos.

**Público-alvo**
academias;
clínicas;
studios;
personal trainers;
nutricionistas;
fisioterapeutas;
clientes.

**Diferencial**
A proposta não é apenas um “site para marcar personal”. O diferencial é integrar atendimento multidisciplinar, agenda, espaços físicos, recorrência e permissões em uma única plataforma.

**Escopo do MVP**
cadastro e login;
perfis de usuário;
cadastro de profissionais;
cadastro de serviços;
disponibilidade;
agendamento;
reagendamento;
cancelamento;
agenda do cliente;
agenda do profissional;
validação de conflitos;
cadastro básico de espaços.

---
### **3. Aplicativos similares**

Foram analisadas soluções já existentes que atendem parte do problema, com base nas funcionalidades divulgadas publicamente por cada produto. O objetivo é identificar o que já é bem resolvido pelo mercado e quais lacunas justificam a proposta.

**Calendly**
Ferramenta de agendamento online genérica. O profissional compartilha um link e o cliente escolhe um horário livre, com integração a calendários como Google Agenda e Outlook.

- Pontos fortes: simplicidade, sincronização com calendários externos, lembretes automáticos.
- Limitações para o tema: não é voltada a academias ou clínicas, não controla salas e equipamentos compartilhados e não oferece ao cliente uma agenda única com vários profissionais de especialidades diferentes.

**Doctoralia**
Marketplace de profissionais de saúde em que o paciente pesquisa por especialidade e localização, consulta avaliações e agenda consultas.

- Pontos fortes: busca por especialidade, perfil do profissional com avaliações, lembretes de consulta.
- Limitações para o tema: foco em consultas de saúde, sem contemplar personal trainers e rotinas de treino; não gerencia espaços físicos compartilhados de um estabelecimento.

**Tecnofit**
Sistema brasileiro de gestão para academias e boxes, com controle de alunos, planos, financeiro, check-in e reserva de aulas.

- Pontos fortes: voltado ao contexto de academia, gestão administrativa e financeira, aplicativo para o aluno.
- Limitações para o tema: foco na gestão do negócio e em aulas/turmas; o agendamento individual entre cliente e diferentes profissionais (nutricionista, fisioterapeuta, personal) não é o centro da solução.

**Trainerize**
Aplicativo para personal trainers acompanharem clientes, com prescrição de treinos, acompanhamento de progresso, mensagens e agendamento de sessões.

- Pontos fortes: acompanhamento do cliente pelo profissional, recorrência de sessões, aplicativo mobile.
- Limitações para o tema: centrado no treinamento físico; não integra outras especialidades nem controla salas e recursos compartilhados.

**Mindbody**
Plataforma de gestão para estúdios, academias e centros de bem-estar, com agendamento de aulas e serviços, gestão de equipe e pagamentos.

- Pontos fortes: solução mais próxima do tema, cobrindo serviços, profissionais e agendamento em estabelecimentos.
- Limitações para o tema: produto pago e voltado principalmente ao mercado internacional, com grande quantidade de funcionalidades administrativas que aumentam a complexidade para estabelecimentos menores.

**Práticas manuais (WhatsApp, planilhas e agendas de papel)**
Ainda são muito usadas por profissionais autônomos e pequenos estabelecimentos.

- Pontos fortes: custo zero e familiaridade.
- Limitações para o tema: não detectam conflitos, geram retrabalho, dependem de troca de mensagens para reagendar e não oferecem visão consolidada da agenda.

**Comparativo**

| Funcionalidade | Calendly | Doctoralia | Tecnofit | Trainerize | Mindbody | Proposta |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| Agendamento online pelo cliente | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Busca por especialidade | ❌ | ✅ | ❌ | ❌ | Parcial | ✅ |
| Agenda única com várias especialidades | ❌ | ❌ | ❌ | ❌ | Parcial | ✅ |
| Controle de salas e equipamentos | ❌ | ❌ | Parcial | ❌ | Parcial | ✅ |
| Sessões recorrentes | Parcial | ❌ | ✅ | ✅ | ✅ | ✅ |
| Permissões por papel (cliente, profissional, recepção, admin) | Parcial | Parcial | ✅ | Parcial | ✅ | ✅ |
| Foco em academia + saúde + bem-estar | ❌ | ❌ | Parcial | Parcial | ✅ | ✅ |

> Observação: o comparativo reflete a análise da equipe a partir das informações públicas dos produtos e deve ser revisado caso as ferramentas sejam testadas diretamente.

**Conclusão da análise**
Cada solução resolve bem uma parte do problema: agendamento genérico (Calendly), busca de profissionais de saúde (Doctoralia), gestão de academia (Tecnofit), acompanhamento de treino (Trainerize) ou gestão completa de estúdios (Mindbody). Nenhuma delas, porém, combina de forma simples a agenda multidisciplinar do cliente com a validação de conflitos entre profissional, sala e recurso dentro de uma academia. Essa lacuna confirma o diferencial da proposta e reforça as prioridades do MVP.

---
