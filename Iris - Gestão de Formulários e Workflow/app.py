from __future__ import annotations
"""
app.py — Iris · API Flask
Porta: 5070  |  Auth: Atlas IAM (localhost:5010)
"""
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

import auth
import database as db
import atlas_client as ac

ac.SISTEMA_FOLDER = "Iris - Gestão de Formulários e Workflow"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("iris.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE    = os.path.join(BASE_DIR, "iris.key")
AI_CFG_FILE = os.path.join(BASE_DIR, "ai_config.json")

if os.path.exists(KEY_FILE):
    _key = open(KEY_FILE, "rb").read()[:32]
else:
    _key = os.urandom(32)
    with open(KEY_FILE, "wb") as f:
        f.write(_key)

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
app.secret_key = _key
app.permanent_session_lifetime = timedelta(hours=12)
CORS(app, supports_credentials=True)


def _err(msg, code=400):
    return jsonify({"error": msg}), code


# ── AI Config ─────────────────────────────────────────────────────────────────

_AI_DEFAULTS = {
    "provider": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model": "gpt-4o-mini",
}


def _load_ai_cfg() -> dict:
    if os.path.exists(AI_CFG_FILE):
        try:
            with open(AI_CFG_FILE, "r", encoding="utf-8") as f:
                return {**_AI_DEFAULTS, **json.load(f)}
        except Exception:
            pass
    return dict(_AI_DEFAULTS)


def _save_ai_cfg(cfg: dict):
    with open(AI_CFG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


_AI_SYSTEM = (
    "Você é um assistente especializado em criação de formulários e workflows corporativos.\n"
    "Dado o nome e descrição de um processo, gere campos de formulário e etapas de workflow.\n\n"
    "Responda SOMENTE com JSON válido (sem markdown, sem bloco de código) neste formato exato:\n"
    '{\n'
    '  "campos": [\n'
    '    {"id":"snake_case_unico","label":"Rótulo","tipo":"text","obrigatorio":true,"opcoes":[]}\n'
    '  ],\n'
    '  "etapas": [\n'
    '    {"nome":"Nome da Etapa","responsavel":""}\n'
    '  ]\n'
    '}\n\n'
    "Tipos disponíveis: text, textarea, number, date, select, checkbox\n"
    "Preencha \"opcoes\" apenas quando tipo == \"select\".\n"
    "Crie 3–8 campos e 2–6 etapas. A última etapa deve representar conclusão."
)


def _normalize_base_url(base_url: str) -> str:
    """Remove endpoint paths que o usuário possa ter incluído na base URL."""
    b = base_url.rstrip("/")
    for suffix in ("/responses", "/chat/completions", "/messages", "/completions"):
        if b.endswith(suffix):
            b = b[: -len(suffix)]
    return b


def _call_openai_compat(base_url: str, api_key: str, model: str,
                         system: str, user_msg: str) -> str:
    url  = _normalize_base_url(base_url) + "/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user",   "content": user_msg}],
        "max_tokens": 2048,
        "temperature": 0.5,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def _call_anthropic(api_key: str, model: str, system: str, user_msg: str) -> str:
    url  = "https://api.anthropic.com/v1/messages"
    body = json.dumps({
        "model": model,
        "max_tokens": 2048,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", api_key)
    req.add_header("anthropic-version", "2023-06-01")
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["content"][0]["text"]


def _call_gemini_native(api_key: str, model: str, system: str, user_msg: str) -> str:
    url  = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = json.dumps({
        "system_instruction": {"parts": [{"text": system}]},
        "contents":           [{"parts": [{"text": user_msg}]}],
        "generationConfig":   {"temperature": 0.5, "maxOutputTokens": 2048},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("X-goog-api-key", api_key)
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _ai_http_error_msg(code: int) -> str:
    return {
        401: "Chave de API inválida ou sem permissão (401).",
        403: "Acesso negado pela API (403). Verifique a chave.",
        404: "Modelo não encontrado (404). Verifique o nome do modelo.",
        429: "Limite de requisições atingido (429). Aguarde alguns segundos e tente novamente.",
        500: "Erro interno do servidor da API (500). Tente novamente em breve.",
        503: "Serviço da API indisponível (503). Tente novamente em breve.",
    }.get(code, f"Erro HTTP {code} da API de IA.")


def _call_ai(cfg: dict, system: str, user_msg: str) -> str:
    provider = cfg.get("provider", "openai")
    api_key  = cfg.get("api_key", "")
    model    = cfg.get("model", "gpt-4o-mini")
    base_url = cfg.get("base_url", "https://api.openai.com/v1")
    if provider == "anthropic":
        return _call_anthropic(api_key, model, system, user_msg)
    if provider == "gemini":
        return _call_gemini_native(api_key, model, system, user_msg)
    return _call_openai_compat(base_url, api_key, model, system, user_msg)


# ── Permissões ────────────────────────────────────────────────────────────────

def _funcoes(user: dict) -> list:
    """Retorna as funções do usuário; 'admin' tem acesso irrestrito."""
    return list(user.get("funcoes") or [])


def _can_access_form(user: dict, formulario: dict) -> bool:
    """Verifica se o usuário pode ver/criar OS deste template."""
    grupos = json.loads(formulario.get("grupos_acesso") or "[]")
    if not grupos:
        return True   # sem restrição — todos os autenticados
    funcoes = _funcoes(user)
    return "admin" in funcoes or bool(set(grupos) & set(funcoes))


def _can_act_step(user: dict, etapa: dict) -> bool:
    """Verifica se o usuário pode agir na etapa (avançar / rejeitar)."""
    resp = (etapa or {}).get("responsavel", "").strip()
    if not resp:
        return True   # etapa aberta a todos
    funcoes = _funcoes(user)
    return "admin" in funcoes or resp in funcoes


def _ok(data=None, **kw):
    p = {"ok": True}
    if data is not None:
        p["data"] = data
    p.update(kw)
    return jsonify(p)


# ── SSO ───────────────────────────────────────────────────────────────────────

def _sso_login(token: str):
    ac.sso_login_from_token(token)


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    token = request.args.get("atlas_token", "").strip()
    if token and not ac.is_atlas_authenticated():
        _sso_login(token)
    resp = send_from_directory(BASE_DIR, "iris.html")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


@app.route("/api/ping")
def ping():
    return _ok(message="pong")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.json or {}
    email    = data.get("email", data.get("username", "")).strip().lower()
    password = data.get("password", "")
    atlas_user = ac.login_with_credentials(email, password)
    if atlas_user:
        return _ok({"nome": atlas_user.get("nome"), "email": atlas_user.get("email"),
                    "role_atlas": ac.get_atlas_role(), "escopo": ac.get_atlas_escopo()},
                   message="Login realizado com sucesso.")
    return _err("E-mail ou senha inválidos, ou acesso ao Iris não autorizado.", 401)


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    auth.logout_user()
    return _ok(message="Sessão encerrada.")


@app.route("/api/auth/status")
def auth_status():
    return _ok({
        "authenticated": ac.is_atlas_authenticated(),
        "user": ac.get_atlas_user(),
        "role_atlas": ac.get_atlas_role(),
        "escopo": ac.get_atlas_escopo(),
    })


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
@auth.require_auth
def stats():
    return _ok(db.get_stats())


# ── Formulários ───────────────────────────────────────────────────────────────

@app.route("/api/formularios")
@auth.require_auth
def list_formularios():
    ativo  = request.args.get("ativo")
    user   = auth.get_current_user() or {}
    forms  = db.list_formularios(ativo=None if ativo is None else (ativo == "1"))
    # cada template carrega apenas para quem tem acesso
    return _ok([f for f in forms if _can_access_form(user, f)])


@app.route("/api/formularios/<int:fid>")
@auth.require_auth
def get_formulario(fid):
    f = db.get_formulario(fid)
    if not f:
        return _err("Template não encontrado.", 404)
    return _ok(f)


@app.route("/api/formularios", methods=["POST"])
@auth.require_auth
def add_formulario():
    d    = request.json or {}
    nome = d.get("nome", "").strip()
    if not nome:
        return _err("Nome é obrigatório.")
    fid = db.add_formulario(
        nome          = nome,
        descricao     = d.get("descricao", ""),
        categoria     = d.get("categoria", "generico"),
        campos        = d.get("campos", []),
        etapas        = d.get("etapas", []),
        grupos_acesso = d.get("grupos_acesso", []),
    )
    return _ok({"id": fid}, message="Template criado.")


@app.route("/api/formularios/<int:fid>", methods=["PUT"])
@auth.require_auth
def update_formulario(fid):
    d, kw = request.json or {}, {}
    for k in ("nome", "descricao", "categoria"):
        if k in d: kw[k] = d[k]
    if "campos"        in d: kw["campos"]        = json.dumps(d["campos"],        ensure_ascii=False)
    if "etapas"        in d: kw["etapas"]        = json.dumps(d["etapas"],        ensure_ascii=False)
    if "grupos_acesso" in d: kw["grupos_acesso"] = json.dumps(d["grupos_acesso"], ensure_ascii=False)
    if "ativo"         in d: kw["ativo"]         = int(bool(d["ativo"]))
    if kw:
        db.update_formulario(fid, **kw)
    return _ok(message="Template atualizado.")


@app.route("/api/formularios/<int:fid>", methods=["DELETE"])
@auth.require_auth
def delete_formulario(fid):
    db.delete_formulario(fid)
    return _ok(message="Template removido.")


# ── Ordens ────────────────────────────────────────────────────────────────────

@app.route("/api/ordens")
@auth.require_auth
def list_ordens():
    status     = request.args.get("status", "")
    prioridade = request.args.get("prioridade", "")
    q          = request.args.get("q", "")
    limit      = min(int(request.args.get("limit", 100)), 500)
    offset     = int(request.args.get("offset", 0))
    ordens = db.list_ordens(status=status, prioridade=prioridade, q=q,
                            limit=limit, offset=offset)
    # filtra pelo acesso ao template correspondente
    user   = auth.get_current_user() or {}
    forms  = {f["id"]: f for f in db.list_formularios()}
    return _ok([o for o in ordens if _can_access_form(user, forms.get(o["formulario_id"], {}))])


@app.route("/api/ordens/<int:oid>")
@auth.require_auth
def get_ordem(oid):
    o = db.get_ordem(oid)
    if not o:
        return _err("OS não encontrada.", 404)
    o["historico"] = db.list_historico(oid)
    return _ok(o)


@app.route("/api/ordens", methods=["POST"])
@auth.require_auth
def add_ordem():
    d      = request.json or {}
    fid    = d.get("formulario_id")
    titulo = d.get("titulo", "").strip()
    if not fid or not titulo:
        return _err("formulario_id e titulo são obrigatórios.")
    f = db.get_formulario(fid)
    if not f:
        return _err("Template não encontrado.", 404)

    user  = auth.get_current_user() or {}
    if not _can_access_form(user, f):
        return _err("Acesso negado a este tipo de formulário.", 403)

    uname = user.get("nome") or user.get("email") or "Sistema"
    etapas = json.loads(f.get("etapas", "[]") or "[]")
    etapa_nome = etapas[0]["nome"] if etapas else "Solicitação"

    oid, numero = db.add_ordem(
        formulario_id   = fid,
        titulo          = titulo,
        dados           = d.get("dados", {}),
        criado_por_nome = uname,
        atribuido_a     = d.get("atribuido_a", ""),
        prioridade      = d.get("prioridade", "normal"),
        observacao      = d.get("observacao", ""),
        nome_contato    = d.get("nome_contato", ""),
        email_contato   = d.get("email_contato", ""),
    )
    db.add_historico(oid, acao="Criação",
                     etapa_de="", etapa_para=etapa_nome,
                     comentario=d.get("observacao", ""),
                     usuario_nome=uname)
    logger.info(f"OS {numero} criada por {uname}")
    return _ok({"id": oid, "numero": numero}, message=f"OS {numero} criada.")


@app.route("/api/ordens/<int:oid>/avancar", methods=["POST"])
@auth.require_auth
def avancar_ordem(oid):
    o = db.get_ordem(oid)
    if not o:
        return _err("OS não encontrada.", 404)
    if o["status"] in ("concluida", "cancelada"):
        return _err("OS já está encerrada.")

    d          = request.json or {}
    acao       = d.get("acao", "avancar")   # avancar | rejeitar | cancelar
    comentario = d.get("comentario", "")
    user       = auth.get_current_user() or {}
    uname      = user.get("nome") or user.get("email") or "Sistema"

    f      = db.get_formulario(o["formulario_id"])
    etapas = json.loads(f.get("etapas", "[]") or "[]") if f else []
    n      = len(etapas)
    atual  = o["etapa_atual"]
    nome_de = etapas[atual]["nome"] if atual < n else f"Etapa {atual}"

    # cancelar pode ser feito por qualquer um com acesso ao template
    # avançar/rejeitar exige ser o responsável da etapa atual
    if acao in ("avancar", "rejeitar"):
        etapa_obj = etapas[atual] if atual < n else {}
        if not _can_act_step(user, etapa_obj):
            resp = etapa_obj.get("responsavel", "?")
            return _err(f"Ação restrita ao grupo '{resp}' nesta etapa.", 403)

    if acao == "cancelar":
        db.update_ordem(oid, status="cancelada")
        db.add_historico(oid, "Cancelamento",
                         etapa_de=nome_de, etapa_para="Cancelada",
                         comentario=comentario, usuario_nome=uname)
        return _ok(message="OS cancelada.")

    if acao == "rejeitar":
        nova = max(0, atual - 1)
        nome_para = etapas[nova]["nome"] if nova < n else f"Etapa {nova}"
        db.update_ordem(oid, status="aberta", etapa_atual=nova)
        db.add_historico(oid, "Rejeição",
                         etapa_de=nome_de, etapa_para=nome_para,
                         comentario=comentario, usuario_nome=uname)
        return _ok(message="OS rejeitada — retornou à etapa anterior.")

    # avancar
    proxima = atual + 1
    if proxima >= n:
        # já estava na última — conclui
        db.update_ordem(oid, status="concluida",
                        concluida_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        db.add_historico(oid, "Conclusão",
                         etapa_de=nome_de, etapa_para="Concluída",
                         comentario=comentario, usuario_nome=uname)
        return _ok(message="OS concluída.")

    nome_para = etapas[proxima]["nome"]
    # Se a próxima etapa for a última, marca concluída diretamente
    if proxima == n - 1:
        db.update_ordem(oid, status="concluida", etapa_atual=proxima,
                        concluida_em=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        db.add_historico(oid, "Conclusão",
                         etapa_de=nome_de, etapa_para=nome_para,
                         comentario=comentario, usuario_nome=uname)
        return _ok(message=f"OS concluída em: {nome_para}.")

    # Etapa intermediária
    novo_status = "em_andamento" if proxima > 0 else "aberta"
    db.update_ordem(oid, status=novo_status, etapa_atual=proxima)
    db.add_historico(oid, "Avanço",
                     etapa_de=nome_de, etapa_para=nome_para,
                     comentario=comentario, usuario_nome=uname)
    return _ok(message=f"OS avançada para: {nome_para}.")


@app.route("/api/ordens/<int:oid>", methods=["DELETE"])
@auth.require_auth
def delete_ordem(oid):
    if not db.get_ordem(oid):
        return _err("OS não encontrada.", 404)
    db.delete_ordem(oid)
    return _ok(message="OS removida.")


# ── IA ────────────────────────────────────────────────────────────────────────

@app.route("/api/ai/config")
@auth.require_auth
def get_ai_config():
    cfg  = _load_ai_cfg()
    safe = {**cfg, "api_key": "***" if cfg.get("api_key") else ""}
    return _ok(safe)


@app.route("/api/ai/config", methods=["POST"])
@auth.require_auth
def save_ai_config():
    d   = request.json or {}
    cfg = _load_ai_cfg()
    for k in ("provider", "base_url", "model"):
        if k in d:
            cfg[k] = d[k]
    if d.get("api_key") and d["api_key"] != "***":
        cfg["api_key"] = d["api_key"]
    _save_ai_cfg(cfg)
    return _ok(message="Configurações de IA salvas.")


@app.route("/api/ai/test", methods=["POST"])
@auth.require_auth
def test_ai_connection():
    d       = request.json or {}
    saved   = _load_ai_cfg()
    test_cfg = {
        "provider": d.get("provider") or saved.get("provider", "openai"),
        "base_url": d.get("base_url") or saved.get("base_url", ""),
        "model":    d.get("model")    or saved.get("model", ""),
        "api_key":  saved.get("api_key", ""),
    }
    if d.get("api_key") and d["api_key"] != "***":
        test_cfg["api_key"] = d["api_key"]
    if not test_cfg.get("api_key"):
        return _err("Chave de API não configurada.")
    if not test_cfg.get("model"):
        return _err("Modelo não informado.")
    try:
        resp = _call_ai(test_cfg, "Você é um assistente.", "Responda apenas com a palavra: OK")
        return _ok({"resposta": resp.strip()[:120]}, message="Conexão bem-sucedida!")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        logger.error(f"AI test HTTP {e.code}: {body}")
        return _err(_ai_http_error_msg(e.code))
    except Exception as e:
        logger.error(f"AI test error: {e}")
        return _err(f"Falha na conexão: {e}")


@app.route("/api/ai/gerar", methods=["POST"])
@auth.require_auth
def ai_gerar():
    d         = request.json or {}
    nome      = d.get("nome", "").strip()
    descricao = d.get("descricao", "").strip()
    if not nome and not descricao:
        return _err("Informe o nome ou descrição do template.")
    cfg = _load_ai_cfg()
    if not cfg.get("api_key"):
        return _err("Chave de API não configurada. Acesse Configurações de IA.")
    user_msg = f"Nome: {nome or '(não informado)'}\nDescrição: {descricao or '(não informada)'}\n\nGere os campos e etapas."
    try:
        raw  = _call_ai(cfg, _AI_SYSTEM, user_msg)
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text  = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(text)
        if "campos" not in result or "etapas" not in result:
            raise ValueError("campos/etapas ausentes")
        return _ok(result)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        logger.error(f"AI HTTP {e.code}: {body}")
        return _err(_ai_http_error_msg(e.code))
    except json.JSONDecodeError as e:
        logger.error(f"AI JSON inválido: {e}")
        return _err("A IA retornou um formato inválido. Tente novamente.")
    except Exception as e:
        logger.error(f"AI error: {e}")
        return _err(f"Erro ao chamar a IA: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("Iris iniciado na porta 5070")
    app.run(host="127.0.0.1", port=5070, debug=False, use_reloader=False)
