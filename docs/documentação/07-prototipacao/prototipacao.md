# Prototipação

## Objetivo
Definir as telas essenciais antes da implementação.

## Tela 1 — Login
Campos:
- e-mail;
- senha;
- entrar;
- criar conta;
- recuperar senha.

## Tela 2 — Home do cliente
Componentes:
- próximos atendimentos;
- botão “Agendar”;
- profissionais favoritos;
- calendário resumido;
- notificações.

## Tela 3 — Buscar profissionais
Filtros:
- especialidade;
- modalidade;
- local;
- faixa de preço;
- disponibilidade.

Cada card:
- nome;
- profissão;
- especialidade;
- avaliação;
- próximo horário;
- botão “Ver perfil”.

## Tela 4 — Perfil do profissional
- foto;
- nome;
- especialidade;
- formação;
- descrição;
- serviços;
- valores;
- disponibilidade;
- avaliações;
- botão “Agendar horário”.

## Tela 5 — Novo agendamento
Fluxo:
1. serviço;
2. profissional;
3. local;
4. data;
5. horário;
6. recorrência opcional;
7. confirmação.

## Tela 6 — Minha agenda
- calendário;
- filtros;
- status do atendimento;
- reagendar;
- cancelar.

## Tela 7 — Painel do profissional
- agenda do dia;
- próximos clientes;
- bloqueio de horário;
- disponibilidade;
- histórico básico de atendimentos.

## Tela 8 — Administração
- usuários;
- profissionais;
- serviços;
- espaços;
- recursos;
- permissões;
- relatórios.

## Wireframe textual — Home do cliente

```text
+------------------------------------------------------+
| FitConnect                         Perfil | Sair      |
+------------------------------------------------------+
| Olá, usuário!                                        |
|                                                      |
| [ + Agendar atendimento ]                            |
|                                                      |
| Próximos atendimentos                                |
| ---------------------------------------------------  |
| Seg 16:00  Personal Carlos        [Ver] [Reagendar]  |
| Ter 14:00  Nutricionista Ana     [Ver] [Reagendar]  |
|                                                      |
| Minha semana                                         |
| [ SEG ][ TER ][ QUA ][ QUI ][ SEX ][ SAB ][ DOM ]   |
+------------------------------------------------------+
```

## Wireframe textual — Agendamento

```text
+----------------------------------------------+
| Novo agendamento                            |
+----------------------------------------------+
| Serviço:       [ Personal Trainer       v ] |
| Profissional:  [ Carlos Silva           v ] |
| Local:         [ Unidade Centro         v ] |
| Data:          [ 10/09/2026              ] |
| Horário:       [ 16:00                   ] |
|                                              |
| [ ] Repetir semanalmente                     |
|                                              |
|          [ Confirmar agendamento ]           |
+----------------------------------------------+
```

## Próximo passo de prototipação
Criar essas telas no Figma e validar o fluxo com usuários antes da implementação.
