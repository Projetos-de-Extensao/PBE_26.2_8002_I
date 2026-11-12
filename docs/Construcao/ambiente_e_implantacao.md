---
id: ambiente_e_implantacao
title: Ambiente e Implantação
---

## Introdução

<p align = "justify">
Esta página reúne o que precisa ser configurado para rodar o Equilibra, em
desenvolvimento e em um servidor de verdade. A regra geral: o projeto roda na
máquina de qualquer pessoa sem nenhuma configuração, e tudo que muda em
produção vem de variáveis de ambiente.
</p>

## Rodando na própria máquina

```bash
python iniciar.py
```

O script cria o ambiente virtual, instala o Django, aplica as migrações,
carrega os dados de exemplo, cria o acesso de demonstração e sobe o servidor.
O passo a passo manual está no `README.md` do repositório.

## Documentação das rotas

Com o servidor local ligado, a interface Swagger fica em
`http://127.0.0.1:8000/docs/` e o schema OpenAPI em
`http://127.0.0.1:8000/api/schema/`. A interface carrega os arquivos do Swagger
UI de um CDN, portanto precisa de acesso à internet para exibir a documentação.

O schema enumera as rotas Django registradas e inclui os modelos do app como
schemas de referência. Muitas rotas são páginas HTML ou formulários do sistema,
não endpoints de uma API REST; a inclusão de um modelo no schema também não
significa que exista CRUD REST para ele. As operações JSON existentes estão
indicadas nas descrições da documentação.

## Variáveis de ambiente

O arquivo `.env.example` lista todas, com os valores usados em desenvolvimento.
Copie para `.env` e ajuste conforme o ambiente.

| Variável | Para que serve | Padrão local |
|---|---|---|
| `DJANGO_SECRET_KEY` | Assina sessões e tokens | Chave de desenvolvimento, insegura |
| `DJANGO_DEBUG` | Liga as páginas de erro detalhadas | `1` |
| `DJANGO_ALLOWED_HOSTS` | Domínios que podem servir a aplicação | `localhost,127.0.0.1,[::1]` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Endereços confiáveis para formulários | `http://localhost:8000` |
| `DJANGO_EMAIL_BACKEND` | Como as mensagens são enviadas | Terminal |

Em produção, gere a chave com:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## O que muda quando `DJANGO_DEBUG=0`

<p align = "justify">
As proteções de produção ligam sozinhas: cookies de sessão e CSRF só por
HTTPS, redirecionamento de HTTP para HTTPS, HSTS por trinta dias e a política
de referenciador restrita à mesma origem. Com a chave e os domínios definidos,
o comando de verificação do Django passa sem nenhum aviso:
</p>

```bash
python manage.py check --deploy
```

## Envio de e-mail

<p align = "justify">
Em desenvolvimento, o backend é o de console: a mensagem de recuperação de
senha aparece no terminal onde o servidor está rodando, com o link de
redefinição. Nenhum e-mail sai da máquina, o que é proposital — ninguém
precisa de uma conta de envio para testar o fluxo.
</p>

<p align = "justify">
Em produção, defina <code>DJANGO_EMAIL_BACKEND</code> como
<code>django.core.mail.backends.smtp.EmailBackend</code> e configure o servidor
de envio. Enquanto isso não for feito, a recuperação de senha funciona, mas a
mensagem não chega ao usuário.
</p>

## Banco de dados

<p align = "justify">
O projeto usa SQLite, em um arquivo <code>db.sqlite3</code> que não é
versionado. Para começar do zero, basta apagar o arquivo e rodar o
<code>iniciar.py</code> de novo: as migrações e os dados de exemplo são
recriados.
</p>

## Testes

```bash
python manage.py test agendamento
```

## Referências

> [Rastreabilidade](./rastreabilidade.md)

> [GitHub Projects](./github_projects.md)

> [Django — Deployment checklist](https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/)
