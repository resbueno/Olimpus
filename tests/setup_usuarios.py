from __future__ import annotations
"""
setup_usuarios.py — Cria usuários de teste no Atlas para o plano de testes Olimpus.

Execução: python tests/setup_usuarios.py
Pré-requisito: Atlas rodando em http://localhost:5010

Usuários criados (senha: Teste@2024):
  gestor.<app>@olimpus.local   — nível gestor/rh/financeiro por app
  operador.<app>@olimpus.local — nível colaborador/membro/leitura por app
"""

import json
import sys
import urllib.error
import urllib.request

ATLAS_URL    = "http://localhost:5010"
ADMIN_EMAIL  = "admin@olimpus.local"
ADMIN_SENHA  = "Atlas@2024"
TESTE_SENHA  = "Teste@2024"

# Mapeamento: app → (sistema_folder, role_gestor, role_operador)
APPS = {
    "hera": (
        "Hera - Gestão de Pessoas",
        "rh",
        "colaborador",
    ),
    "ploutos": (
        "Ploutos - Gestão Financeira",
        "financeiro",
        "colaborador",
    ),
    "cronos": (
        "Cronos - Ponto Eletrônico",
        "rh",
        "colaborador",
    ),
    "hercules": (
        "Hércules - Gestão de Tarefas",
        "gestor",
        "membro",
    ),
    "hermes": (
        "Hermes - Gestão de Ativos",
        "gestor",
        "colaborador",
    ),
    "hestia": (
        "Héstia - Intranet Corporativa",
        "admin",
        "leitura",
    ),
    "iris": (
        "Iris - Gestão de Formulários e Workflow",
        "admin",
        "leitura",
    ),
    "oraculo": (
        "Oráculo - Hub de Notícias",
        "editor",
        "leitura",
    ),
    "tiresias": (
        "Tiresias – OCR",
        "admin",
        "leitura",
    ),
    "temis": (
        "Têmis – Gestão de Contratos",
        "admin",
        "leitura",
    ),
    "argos": (
        "Argos - Monitoração",
        "admin",
        "leitura",
    ),
}

# Apps cujo "gestor" precisa de funcao='admin' no Atlas para acessar endpoints protegidos
# (Padrão B — não têm tabela local de users, usam funcoes do Atlas)
REQUER_FUNCAO_ADMIN = {"hestia", "iris", "tiresias", "temis", "argos"}


def _req(session_cookie, method, path, body=None):
    url = ATLAS_URL + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if session_cookie:
        headers["Cookie"] = session_cookie
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as ex:
        return 0, {"error": str(ex)}


def login_admin():
    code, resp = _req(None, "POST", "/api/auth/login",
                      {"email": ADMIN_EMAIL, "senha": ADMIN_SENHA})
    if code != 200 or not resp.get("ok"):
        print(f"  [ERRO] Login admin falhou: {resp}")
        return None, None
    # Obtém cookie de sessão (simplificado — urllib não lida com cookies diretamente)
    # Usaremos requests se disponível
    return resp.get("data", {}), None


def setup():
    try:
        import requests
    except ImportError:
        print("[ERRO] Instale 'requests': pip install requests")
        sys.exit(1)

    base = ATLAS_URL
    s = requests.Session()

    # Login admin
    r = s.post(f"{base}/api/auth/login",
               json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA}, timeout=10)
    if r.status_code != 200 or not r.json().get("ok"):
        print(f"[ERRO] Não foi possível fazer login no Atlas: {r.text}")
        sys.exit(1)
    print("[OK] Login admin no Atlas.")

    # Obtém lista de sistemas cadastrados
    r = s.get(f"{base}/api/sistemas", timeout=10)
    sistemas_existentes = {x["folder"] for x in r.json().get("data", [])}

    # Obtém funcoes cadastradas
    r = s.get(f"{base}/api/funcoes", timeout=10)
    funcoes_existentes = {x["nome"]: x["id"] for x in r.json().get("data", [])}

    # Garante que funcao 'admin' existe
    if "admin" not in funcoes_existentes:
        r = s.post(f"{base}/api/funcoes",
                   json={"nome": "admin", "descricao": "Administrador do sistema"}, timeout=10)
        if r.json().get("ok"):
            funcoes_existentes["admin"] = r.json()["data"]["id"]
            print("  [OK] Funcao 'admin' criada.")

    criados = 0
    erros = 0

    for app_key, (folder, role_g, role_o) in APPS.items():
        print(f"\n--- {app_key.upper()} ({folder}) ---")

        # Garante que o sistema está cadastrado no Atlas
        if folder not in sistemas_existentes:
            r = s.post(f"{base}/api/sistemas",
                       json={"folder": folder, "nome": folder.split(" - ")[-1] if " - " in folder else folder},
                       timeout=10)
            if r.json().get("ok"):
                sistemas_existentes.add(folder)
                print(f"  [OK] Sistema '{folder}' cadastrado no Atlas.")
            else:
                print(f"  [AVISO] Não foi possível cadastrar sistema '{folder}': {r.json()}")

        for nivel, role, email_prefix in [
            ("gestor",   role_g, f"gestor.{app_key}"),
            ("operador", role_o, f"operador.{app_key}"),
        ]:
            email = f"{email_prefix}@olimpus.local"
            nome  = f"Teste {nivel.capitalize()} {app_key.capitalize()}"

            # Verifica se pessoa já existe
            r = s.get(f"{base}/api/pessoas", timeout=10)
            pessoas = r.json().get("data", [])
            existente = next((p for p in pessoas if p["email"] == email), None)

            if existente:
                pid = existente["id"]
                print(f"  [JÁ EXISTE] {email} (id={pid})")
            else:
                # Cria pessoa
                payload = {
                    "nome":   nome,
                    "email":  email,
                    "senha":  TESTE_SENHA,
                    "cargo":  nivel.capitalize(),
                    "funcoes": [],
                    "ativo":  1,
                }
                r = s.post(f"{base}/api/pessoas", json=payload, timeout=10)
                if r.json().get("ok"):
                    pid = r.json()["data"]["id"]
                    print(f"  [CRIADO] {email} (id={pid})")
                    criados += 1
                else:
                    print(f"  [ERRO] Criação falhou para {email}: {r.json()}")
                    erros += 1
                    continue

            # Atribui funcao 'admin' para gestor de apps Padrão B
            if nivel == "gestor" and app_key in REQUER_FUNCAO_ADMIN:
                r = s.get(f"{base}/api/pessoas/{pid}", timeout=10)
                pdata = r.json().get("data", {})
                funcoes_atuais = [f["nome"] for f in (pdata.get("funcoes") or [])]
                if "admin" not in funcoes_atuais:
                    admin_id = funcoes_existentes.get("admin")
                    if admin_id:
                        r = s.post(f"{base}/api/pessoas/{pid}/funcoes",
                                   json={"funcao_id": admin_id}, timeout=10)
                        if r.json().get("ok"):
                            print(f"    [OK] Funcao 'admin' atribuída a {email}")
                        else:
                            # Tenta via PUT pessoa com funcoes
                            r = s.put(f"{base}/api/pessoas/{pid}",
                                      json={"funcoes": ["admin"]}, timeout=10)
                            if r.json().get("ok"):
                                print(f"    [OK] Funcao 'admin' atribuída (via PUT) a {email}")
                            else:
                                print(f"    [AVISO] Não atribuiu funcao admin: {r.json()}")

            # Cria/atualiza acesso ao sistema com role
            acesso_payload = {
                "sistema_folder": folder,
                "pessoa_id":      pid,
                "permitido":      1,
                "role_sistema":   role,
            }
            r = s.post(f"{base}/api/acessos", json=acesso_payload, timeout=10)
            if r.json().get("ok") or r.status_code in [200, 201]:
                print(f"    [OK] Acesso '{role}' em '{folder}' configurado")
            else:
                # Tenta PATCH/PUT se já existe
                print(f"    [AVISO] Acesso: {r.json()}")

    print(f"\n{'='*60}")
    print(f"Setup concluído: {criados} usuários criados, {erros} erros.")
    print(f"{'='*60}")
    print("\nCredenciais dos usuários de teste:")
    print(f"  Senha padrão: {TESTE_SENHA}")
    for app_key in APPS:
        print(f"  gestor.{app_key}@olimpus.local")
        print(f"  operador.{app_key}@olimpus.local")


if __name__ == "__main__":
    print("="*60)
    print("Olimpus — Setup de Usuários de Teste")
    print("="*60)
    print(f"Atlas: {ATLAS_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print()
    setup()
