# Projeto Back-End 

**Código da Disciplina**: IBM8936<br>

## Sobre 
Descreva o seu projeto em linhas gerais. 

## Instalação 
**Linguagens**: Python, Django<br>
**Tecnologias**: Github, Visual Studio Code<br>
 os pré-requisitos para rodar o seu projeto são UX, Engenharia de Dados, POO.


## Como rodar (jeito rápido)

Com o Python instalado, na pasta do projeto:

```bash
python iniciar.py
```

O script cria o ambiente virtual, instala o Django, prepara o banco, carrega os dados de
exemplo, cria o acesso de demonstração (usuário `admin`, senha `admin`), sobe o servidor e
abre o navegador. Funciona em Windows, macOS e Linux. Para parar, `Ctrl+C`.

> O acesso `admin`/`admin` existe só para demonstração local e não deve ir para produção.

## Como rodar (passo a passo)

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install Django==6.1.2
python src/manage.py migrate
python src/manage.py runserver
```

A aplicação sobe em `http://127.0.0.1:8000`. O painel administrativo fica em `/admin/`
(crie o acesso com `python src/manage.py createsuperuser`) e a tela de novo agendamento
em `/agenda/agendamentos/novo/`.

### Dados de exemplo

Para demonstrar o sistema sem cadastrar tudo na mão:

```bash
python src/manage.py loaddata exemplo
```

São carregados 3 salas, 3 equipamentos, 3 profissionais (personal, nutricionista e
fisioterapeuta), 4 serviços, as disponibilidades da semana, um bloqueio de almoço e 5
agendamentos de novembro de 2026, incluindo um cancelado. Os usuários de exemplo entram
apenas pelo admin, pois não têm senha definida.

### Testes

```bash
python src/manage.py test agenda
```
