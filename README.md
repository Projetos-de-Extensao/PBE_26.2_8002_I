# Equilibra — Plataforma de Agendamento Multidisciplinar

**Disciplina**: Projeto Back-End (IBM8936) · **Turma**: PBE 26.2 — 8002 I

## Sobre

Plataforma web de agendamento para academias, clínicas e estúdios, onde um mesmo
cliente é atendido por profissionais de áreas diferentes — personal trainer,
nutricionista, fisioterapeuta — em uma agenda só.

A regra central do sistema: um atendimento só é confirmado quando cliente,
profissional e, quando necessário, sala e equipamento estiverem livres no mesmo
intervalo de tempo.

**Perfis de usuário**: cliente, profissional, recepcionista e administrador.

Documentação completa em
[projetos-de-extensao.github.io/PBE_26.2_8002_I](https://projetos-de-extensao.github.io/PBE_26.2_8002_I/).

## Como rodar

Pré-requisito: Python 3.11 ou mais novo.

```bash
python iniciar.py
```

O script cria o ambiente virtual, instala o Django, prepara o banco, carrega os
dados de exemplo, cria o acesso de demonstração, sobe o servidor e abre o
navegador. Funciona em Windows, macOS e Linux. Para parar, `Ctrl+C`.

Para não abrir o navegador automaticamente: `python iniciar.py --sem-navegador`.

Com o servidor ligado, abra `http://127.0.0.1:8000/docs/` para explorar as rotas
do sistema no Swagger UI. O schema OpenAPI inclui as rotas registradas e os
schemas de todos os modelos do app. Ele fica disponível em
`http://127.0.0.1:8000/api/schema/`.

### Passo a passo, se preferir

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows; no macOS e Linux: source .venv/bin/activate
pip install Django==6.1.2
python manage.py migrate
python manage.py criar_dados_exemplo
python manage.py runserver
```

## Acessos de demonstração

| Perfil | E-mail | Senha |
| --- | --- | --- |
| Administrador | `admin@demo.local` | `admin` |
| Cliente | `ana.souza@exemplo.local` | `exemplo123` |
| Cliente | `bruno.lima@exemplo.local` | `exemplo123` |
| Profissional | `carla.dias@exemplo.local` | `exemplo123` |
| Recepcionista | `fernanda.recepcao@exemplo.local` | `exemplo123` |

O login é feito por e-mail. Essas contas existem apenas para demonstração local:
o servidor de desenvolvimento escuta somente em `127.0.0.1`.

Para criar contas com senhas aleatórias, use `python manage.py criar_usuarios_demo`.

## O que dá para testar

- **Cliente**: buscar profissional por especialidade, ver serviços e horários
  livres, agendar, repetir semanalmente, acompanhar a agenda, reagendar e cancelar.
- **Profissional**: configurar as faixas de disponibilidade, bloquear horários e
  acompanhar os próprios atendimentos.
- **Administrador**: gerenciar profissionais, serviços, salas, equipamentos,
  usuários e papéis.
- **Prevenção de conflitos**: tente marcar dois atendimentos no mesmo horário
  para o mesmo profissional, cliente, sala ou equipamento exclusivo.

## Testes

```bash
python manage.py test agendamento
```

## Configuração por ambiente

O projeto roda sem configurar nada. Em produção, defina `DJANGO_SECRET_KEY`,
`DJANGO_DEBUG=0` e `DJANGO_ALLOWED_HOSTS`: as proteções de HTTPS e de cookies
ligam sozinhas. O arquivo `.env.example` lista todas as variáveis e a página
[Ambiente e Implantação](docs/Construcao/ambiente_e_implantacao.md) explica
cada uma.

Em desenvolvimento, o e-mail de recuperação de senha aparece no terminal do
servidor, não na caixa de entrada.

## Estrutura

```
agendamento/     aplicação principal (modelos, telas, regras de negócio e testes)
project/         configurações do Django
docs/            documentação do projeto, publicada com MkDocs
iniciar.py       prepara o ambiente e sobe o sistema
manage.py        utilitário padrão do Django
```

## Tecnologias

Python, Django 6.1, SQLite, HTML e CSS. Documentação em MkDocs com tema Material.
Versionamento no GitHub, com issues e quadro de projeto.
