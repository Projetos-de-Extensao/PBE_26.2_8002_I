"""Prepara e sobe o projeto com um comando só.

Uso:

    python iniciar.py

Use "python iniciar.py --sem-navegador" para não abrir o navegador sozinho.

O script cria o ambiente virtual, instala o Django, aplica as migrações,
carrega os dados de exemplo, cria um acesso de demonstração, sobe o servidor
e abre o navegador. Funciona em Windows, macOS e Linux.
"""

import os
import platform
import socket
import subprocess
import sys
import time
import venv
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VENV = RAIZ / ".venv"
MANAGE = RAIZ / "src" / "manage.py"
DJANGO = "Django==6.1.2"
HOST = "127.0.0.1"
PORTA = 8000
PAGINA = "/agenda/agendamentos/novo/"

# Acesso só para demonstração local. O servidor roda apenas nesta máquina.
USUARIO_DEMO = "admin"
SENHA_DEMO = "admin"


def aviso(texto):
    print("\n==> " + texto, flush=True)


def python_do_venv():
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def rodar(comando, **kwargs):
    """Executa um comando e interrompe o script se ele falhar."""
    resultado = subprocess.run(comando, cwd=str(RAIZ), **kwargs)
    if resultado.returncode != 0:
        print("\nO comando falhou: " + " ".join(str(parte) for parte in comando), flush=True)
        sys.exit(resultado.returncode)
    return resultado


def criar_venv():
    python = python_do_venv()
    if python.exists():
        return python
    aviso("Criando o ambiente virtual em .venv (só na primeira vez)")
    venv.EnvBuilder(with_pip=True, clear=False).create(str(VENV))
    python = python_do_venv()
    if not python.exists():
        print("Não consegui criar o ambiente virtual.", flush=True)
        sys.exit(1)
    return python


def instalar_django(python):
    tem_django = subprocess.run(
        [str(python), "-c", "import django"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if tem_django.returncode == 0:
        return
    aviso("Instalando o Django")
    rodar([str(python), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    rodar([str(python), "-m", "pip", "install", "--quiet", DJANGO])


def preparar_banco(python):
    aviso("Preparando o banco de dados")
    rodar([str(python), str(MANAGE), "migrate", "--noinput"])


def carregar_exemplo(python):
    """Carrega a fixture de demonstração se o banco ainda estiver vazio."""
    script = (
        "import django, os;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings');"
        "django.setup();"
        "from agenda.models import Agendamento;"
        "print(Agendamento.objects.count())"
    )
    resultado = subprocess.run(
        [str(python), "-c", script],
        cwd=str(RAIZ / "src"),
        capture_output=True,
        text=True,
    )
    if resultado.returncode != 0 or resultado.stdout.strip() != "0":
        return
    aviso("Carregando os dados de exemplo")
    rodar([str(python), str(MANAGE), "loaddata", "exemplo"])


def criar_acesso_demo(python):
    """Cria o acesso de demonstração e liga ele a um perfil de profissional."""
    script = (
        "import django, os;"
        "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings');"
        "django.setup();"
        "from django.contrib.auth import get_user_model;"
        "from agenda.models import Profissional;"
        "U = get_user_model();"
        "existe = U.objects.filter(username='{usuario}').exists();"
        "u = U.objects.get(username='{usuario}') if existe"
        " else U.objects.create_superuser('{usuario}', '', '{senha}');"
        # O admin também vira profissional para que o painel e a tela de
        # disponibilidade funcionem na demonstração.
        "Profissional.objects.get_or_create("
        "usuario=u, defaults={{'especialidade': 'PERSONAL',"
        " 'descricao': 'Perfil de demonstração.'}});"
        "print('criado' if not existe else 'ja_existe')"
    ).format(usuario=USUARIO_DEMO, senha=SENHA_DEMO)
    resultado = subprocess.run(
        [str(python), "-c", script],
        cwd=str(RAIZ / "src"),
        capture_output=True,
        text=True,
    )
    if "criado" in resultado.stdout:
        aviso(
            "Acesso de demonstração criado: usuário '{0}' e senha '{1}'".format(
                USUARIO_DEMO, SENHA_DEMO
            )
        )


def porta_ocupada():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as teste:
        teste.settimeout(0.5)
        return teste.connect_ex((HOST, PORTA)) == 0


def esperar_servidor(limite=40):
    for _ in range(limite):
        if porta_ocupada():
            return True
        time.sleep(0.5)
    return False


def main():
    abrir_navegador = "--sem-navegador" not in sys.argv

    if not MANAGE.exists():
        print("Rode este script na pasta do projeto (onde está a pasta src).", flush=True)
        sys.exit(1)

    if porta_ocupada():
        print("Já existe algo rodando em http://{0}:{1}".format(HOST, PORTA), flush=True)
        print("Feche o outro servidor e rode de novo.", flush=True)
        sys.exit(1)

    python = criar_venv()
    instalar_django(python)
    preparar_banco(python)
    carregar_exemplo(python)
    criar_acesso_demo(python)

    endereco = "http://{0}:{1}".format(HOST, PORTA)
    aviso("Subindo o servidor em " + endereco)
    ambiente = dict(os.environ, PYTHONUNBUFFERED="1")
    servidor = subprocess.Popen(
        [str(python), str(MANAGE), "runserver", "{0}:{1}".format(HOST, PORTA)],
        cwd=str(RAIZ),
        env=ambiente,
    )

    try:
        if esperar_servidor():
            if abrir_navegador:
                webbrowser.open(endereco + PAGINA)
            else:
                print("\nAbra no navegador: " + endereco + PAGINA, flush=True)
            print("\nPronto. Entre com usuário '{0}' e senha '{1}'.".format(
                USUARIO_DEMO, SENHA_DEMO
            ))
            print("Painel administrativo: " + endereco + "/admin/", flush=True)
            print("Para parar o servidor, aperte Ctrl+C.\n", flush=True)
        else:
            print("O servidor demorou a responder. Veja as mensagens acima.", flush=True)
        servidor.wait()
    except KeyboardInterrupt:
        print("\nParando o servidor...", flush=True)
    finally:
        servidor.terminate()
        try:
            servidor.wait(timeout=10)
        except subprocess.TimeoutExpired:
            servidor.kill()


if __name__ == "__main__":
    main()
