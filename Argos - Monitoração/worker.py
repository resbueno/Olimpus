from __future__ import annotations
"""
worker.py — Motor de execucao de jornadas via Playwright
"""

import os
import time
import logging
from datetime import datetime

from database import decrypt_password, get_monitor, save_history, SCREENSHOTS_DIR

logger = logging.getLogger(__name__)

TIMEOUT_MS          = 60_000
NAV_TIMEOUT         = 60_000
POST_LOGIN_WAIT_MS  = 3_000
SELECTOR_RETRIES    = 3
SELECTOR_RETRY_WAIT = 2


def _ts() -> int:
    return int(time.time() * 1000)


def _screenshot(page, prefix: str) -> str | None:
    try:
        fn = f"{prefix}.png"
        fp = os.path.join(SCREENSHOTS_DIR, fn)
        page.screenshot(path=fp, full_page=False)
        logger.info(f"Screenshot salvo: {fn}")
        return fn
    except Exception as e:
        logger.warning(f"Screenshot falhou: {e}")
        return None


def _log_inputs(page, monitor_id: int):
    """Loga todos os inputs visiveis na pagina para diagnostico."""
    try:
        inputs = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, textarea, select')).map(el => ({
                tag:         el.tagName,
                type:        el.type || '',
                name:        el.name || '',
                id:          el.id   || '',
                placeholder: el.placeholder || '',
                className:   el.className   || '',
                visible:     el.offsetParent !== null && el.offsetWidth > 0,
            }));
        }""")
        logger.info(f"[{monitor_id}] Inputs encontrados na pagina ({len(inputs)}):")
        for inp in inputs:
            logger.info(
                f"[{monitor_id}]   tag={inp['tag']} type={inp['type']!r} "
                f"name={inp['name']!r} id={inp['id']!r} "
                f"placeholder={inp['placeholder']!r} visible={inp['visible']}"
            )
    except Exception as e:
        logger.warning(f"[{monitor_id}] Falha ao listar inputs: {e}")


def _log_iframes(page, monitor_id: int):
    """Loga iframes presentes — login pode estar dentro de um deles."""
    try:
        frames = page.frames
        if len(frames) > 1:
            logger.info(f"[{monitor_id}] {len(frames)} frames detectados:")
            for i, f in enumerate(frames):
                logger.info(f"[{monitor_id}]   frame[{i}] url={f.url!r}")
    except Exception:
        pass


def run_journey(monitor_id: int) -> dict:
    monitor = get_monitor(monitor_id)
    if not monitor:
        return {"error": f"Monitor {monitor_id} nao encontrado."}

    result = {
        "monitor_id":       monitor_id,
        "status":           "FAIL",
        "initial_load_ms":  None,
        "login_ms":         None,
        "service_load_ms":  None,
        "total_journey_ms": None,
        "error_message":    None,
        "screenshot_path":  None,
        "executed_at":      datetime.now().isoformat(),
    }

    journey_start = _ts()
    page = None
    browser = None

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                viewport={"width": 1440, "height": 900},
                ignore_https_errors=True,
            )
            ctx.clear_cookies()
            page = ctx.new_page()
            page.set_default_timeout(TIMEOUT_MS)
            page.set_default_navigation_timeout(NAV_TIMEOUT)

            # ── PASSO 1: Carga inicial ─────────────────────────────────────
            t0 = _ts()
            logger.info(f"[{monitor_id}] Abrindo URL: {monitor['url']}")
            try:
                page.goto(monitor["url"], wait_until="networkidle")
            except PWTimeout:
                page.goto(monitor["url"], wait_until="domcontentloaded")
                _wait_stable(page)
            result["initial_load_ms"] = _ts() - t0
            logger.info(f"[{monitor_id}] Pagina carregada em {result['initial_load_ms']}ms — URL: {page.url} — Titulo: {page.title()!r}")
            _log_inputs(page, monitor_id)
            _log_iframes(page, monitor_id)

            # ── PASSO 2: Login ─────────────────────────────────────────────
            t1 = _ts()
            plain_pwd = decrypt_password(monitor["password_enc"])
            two_step = bool(monitor.get("two_step_login", 0))
            _perform_login(page, monitor["username"], plain_pwd, monitor_id, two_step=two_step)
            result["login_ms"] = _ts() - t1
            logger.info(f"[{monitor_id}] Login em {result['login_ms']}ms — URL apos login: {page.url}")

            # ── PASSO 3: Menu alvo ─────────────────────────────────────────
            t2 = _ts()
            selector = monitor["target_menu_selector"]
            logger.info(f"[{monitor_id}] Navegando ao seletor: {selector!r}")
            _navigate_to_menu(page, selector, monitor_id)
            result["service_load_ms"] = _ts() - t2
            logger.info(f"[{monitor_id}] Seletor encontrado em {result['service_load_ms']}ms — URL final: {page.url}")

            result["total_journey_ms"] = (
                (result["initial_load_ms"]  or 0) +
                (result["login_ms"]         or 0) +
                (result["service_load_ms"]  or 0)
            )
            result["status"] = "SUCCESS"
            result["screenshot_path"] = _screenshot(page, str(monitor_id))

            ctx.close()
            browser.close()

    except Exception as exc:
        result["error_message"]    = _classify_error(exc)
        result["total_journey_ms"] = _ts() - journey_start
        logger.error(f"[{monitor_id}] Jornada falhou: {result['error_message']}")
        if page is not None:
            result["screenshot_path"] = _screenshot(page, f"{monitor_id}_FAIL")
            try:
                page.context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    history_id   = save_history(result)
    result["id"] = history_id

    if monitor.get("notify_emails", "").strip():
        try:
            import notifier
            import auth as _auth
            cfg = _auth.load_config()
            notifier.check_and_send_alert(
                monitor, result,
                gmail_user=cfg.get("gmail_user", ""),
                gmail_app_password=cfg.get("gmail_app_password", ""),
            )
        except Exception as exc:
            logger.error(f"[{monitor_id}] Erro ao enviar notificação: {exc}")

    return result


# ── Login ─────────────────────────────────────────────────────────────────────

def _perform_login(page, username: str, password: str, monitor_id: int, two_step: bool = False):
    from playwright.sync_api import TimeoutError as PWTimeout

    # Aguarda qualquer input aparecer na pagina antes de procurar
    try:
        page.wait_for_selector("input", timeout=10_000, state="visible")
    except PWTimeout:
        logger.warning(f"[{monitor_id}] Nenhum <input> visivel apos 10s. Continuando mesmo assim.")

    if two_step:
        _perform_login_two_step(page, username, password, monitor_id)
    else:
        _perform_login_single(page, username, password, monitor_id)


def _perform_login_single(page, username: str, password: str, monitor_id: int):
    """Preenche usuario e senha na mesma tela e envia."""
    user_el = _find_user_field(page, monitor_id)
    if user_el:
        user_el.click()
        user_el.fill("")
        user_el.type(username, delay=30)
        logger.info(f"[{monitor_id}] Campo usuario preenchido.")
    else:
        logger.warning(f"[{monitor_id}] Campo de usuario nao encontrado. Verifique o log de inputs acima.")

    pass_el = _find_password_field(page, monitor_id)
    if pass_el:
        pass_el.click()
        pass_el.fill("")
        pass_el.type(password, delay=30)
        logger.info(f"[{monitor_id}] Campo senha preenchido.")
    else:
        logger.warning(f"[{monitor_id}] Campo de senha nao encontrado.")

    submit_el = _find_submit(page)
    if submit_el:
        submit_el.click()
        logger.info(f"[{monitor_id}] Botao submit clicado.")
    elif pass_el:
        pass_el.press("Enter")
        logger.info(f"[{monitor_id}] Enter pressionado no campo senha.")

    _wait_stable(page, min_wait_ms=POST_LOGIN_WAIT_MS)


def _perform_login_two_step(page, username: str, password: str, monitor_id: int):
    """
    Login em 2 etapas: usuario na primeira tela, aguarda a tela de senha
    aparecer, preenche e confirma.
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    # ── Etapa 1: usuario ──────────────────────────────────────────────────────
    PASS_SEL = 'input[type="password"], input[name*="senha" i], input[name*="pass" i]'

    user_el = _find_user_field(page, monitor_id)
    if user_el:
        user_el.click()
        user_el.fill("")
        user_el.type(username, delay=30)
        logger.info(f"[{monitor_id}] [2-step] Campo usuario preenchido.")

        # Tenta Enter no proprio campo primeiro — mais confiavel que achar o botao certo
        user_el.press("Enter")
        logger.info(f"[{monitor_id}] [2-step] Enter pressionado no campo usuario.")

        # Se o campo de senha nao aparecer em 3s, procura e clica no botao de submit
        pass_appeared = False
        try:
            page.wait_for_selector(PASS_SEL, state="visible", timeout=3_000)
            pass_appeared = True
            logger.info(f"[{monitor_id}] [2-step] Campo senha apareceu apos Enter.")
        except PWTimeout:
            pass

        if not pass_appeared:
            submit_el = _find_submit_near(page, user_el, monitor_id)
            if submit_el:
                submit_el.click()
                logger.info(f"[{monitor_id}] [2-step] Botao continuar clicado apos usuario.")
            else:
                logger.warning(f"[{monitor_id}] [2-step] Nenhum botao de continuar encontrado.")
    else:
        logger.warning(f"[{monitor_id}] [2-step] Campo de usuario nao encontrado.")

    # Aguarda o campo de senha aparecer (ate 10s)
    try:
        page.wait_for_selector(PASS_SEL, state="visible", timeout=10_000)
        logger.info(f"[{monitor_id}] [2-step] Campo senha detectado.")
    except PWTimeout:
        logger.warning(f"[{monitor_id}] [2-step] Campo senha nao apareceu em 10s; tentando mesmo assim.")

    logger.info(f"[{monitor_id}] [2-step] URL apos etapa 1: {page.url}")
    _log_inputs(page, monitor_id)

    # ── Etapa 2: senha ────────────────────────────────────────────────────────
    pass_el = _find_password_field(page, monitor_id)
    if pass_el:
        pass_el.click()
        pass_el.fill("")
        pass_el.type(password, delay=30)
        logger.info(f"[{monitor_id}] [2-step] Campo senha preenchido.")
    else:
        logger.warning(f"[{monitor_id}] [2-step] Campo de senha nao encontrado apos etapa 1.")

    submit_el = _find_submit(page)
    if submit_el:
        submit_el.click()
        logger.info(f"[{monitor_id}] [2-step] Botao submit clicado apos senha.")
    elif pass_el:
        pass_el.press("Enter")
        logger.info(f"[{monitor_id}] [2-step] Enter pressionado no campo senha.")

    _wait_stable(page, min_wait_ms=POST_LOGIN_WAIT_MS)


def _find_user_field(page, monitor_id: int):
    """
    Procura o campo de usuario em multiplas estrategias, incluindo iframes.
    Seletores mais especificos vem primeiro para evitar capturar campos de busca.
    """
    SELS = [
        # Campos de CPF / documento (portais brasileiros)
        'input[name="cpf"]', 'input[name="CPF"]',
        'input[name*="cpf" i]', 'input[id*="cpf" i]',
        'input[placeholder*="cpf" i]',
        # E-mail
        'input[type="email"]',
        # Campos com atributos semanticos claros
        'input[autocomplete="username"]',
        'input[autocomplete="email"]',
        'input[name="username"]', 'input[name="user"]',
        'input[name="login"]',   'input[name="j_username"]',
        'input[name="UserName"]','input[name="Email"]',
        'input[name="email"]',   'input[name="uid"]',
        # Campos por name/id/placeholder contendo termos de login
        'input[type="text"][name*="user" i]',
        'input[type="text"][name*="login" i]',
        'input[type="text"][name*="email" i]',
        'input[type="text"][id*="user" i]',
        'input[type="text"][id*="login" i]',
        'input[type="text"][id*="email" i]',
        'input[placeholder*="usuario" i]',
        'input[placeholder*="user" i]',
        'input[placeholder*="email" i]',
        'input[placeholder*="login" i]',
    ]

    # tenta na pagina principal
    for sel in SELS:
        el = _find_first_visible(page, sel)
        if el:
            logger.info(f"[{monitor_id}] Usuario encontrado com seletor: {sel!r}")
            return el

    # tenta dentro de iframes
    for frame in page.frames[1:]:
        for sel in SELS:
            el = _find_first_visible(frame, sel)
            if el:
                logger.info(f"[{monitor_id}] Usuario encontrado em iframe ({frame.url!r}) com: {sel!r}")
                return el

    # ultimo recurso: primeiro input text visivel que nao seja busca nem senha
    logger.info(f"[{monitor_id}] Seletores especificos nao encontraram campo; usando fallback com filtro anti-busca.")
    fallback_sel = (
        'input[type="text"]:not([type="password"]):not([type="hidden"]),'
        'input:not([type="password"]):not([type="hidden"]):not([type="submit"])'
        ':not([type="checkbox"]):not([type="radio"]):not([type="file"]):not([type="search"])'
    )
    for context in [page] + list(page.frames[1:]):
        try:
            candidates = context.query_selector_all(fallback_sel)
        except Exception:
            continue
        for el in candidates:
            if not el.is_visible():
                continue
            if _looks_like_search_field(el):
                continue
            logger.info(f"[{monitor_id}] Usuario encontrado via fallback.")
            return el

    return None


def _looks_like_search_field(el) -> bool:
    """Retorna True se o elemento parece ser um campo de busca, nao de login."""
    SEARCH_HINTS = ("buscar", "busca", "search", "pesquisa", "pesquisar", "query", "filtro", "filter")
    try:
        attrs = {
            "placeholder": (el.get_attribute("placeholder") or "").lower(),
            "name":        (el.get_attribute("name")        or "").lower(),
            "id":          (el.get_attribute("id")          or "").lower(),
            "aria_label":  (el.get_attribute("aria-label")  or "").lower(),
            "type":        (el.get_attribute("type")        or "").lower(),
        }
        if attrs["type"] == "search":
            return True
        return any(hint in v for hint in SEARCH_HINTS for v in attrs.values())
    except Exception:
        return False


def _find_password_field(page, monitor_id: int):
    SELS = [
        'input[type="password"]',
        'input[name="password"]', 'input[name="senha"]',
        'input[name="j_password"]', 'input[name="Password"]',
        'input[id*="pass" i]', 'input[id*="senha" i]',
    ]
    for sel in SELS:
        el = _find_first_visible(page, sel)
        if el:
            logger.info(f"[{monitor_id}] Senha encontrada com seletor: {sel!r}")
            return el
    for frame in page.frames[1:]:
        for sel in SELS:
            el = _find_first_visible(frame, sel)
            if el:
                logger.info(f"[{monitor_id}] Senha encontrada em iframe ({frame.url!r}) com: {sel!r}")
                return el
    return None


def _find_submit_near(page, field_el, monitor_id: int):
    """
    Procura o botao de submit mais proximo do campo informado:
    primeiro dentro do mesmo <form>, depois no mesmo pai imediato,
    por fim recorre ao _find_submit global mas excluindo elementos
    que parecem links de navegacao do site (header/nav/topbar).
    """
    SUBMIT_SELS = [
        'button[type="submit"]', 'input[type="submit"]',
        'button[type="button"]',  # alguns SPAs usam type=button
    ]
    TEXT_HINTS = ("entrar", "login", "acessar", "continuar", "next", "sign in", "ok", "confirmar")

    try:
        # 1) dentro do <form> que contém o campo
        form_el = page.evaluate("el => el.closest('form')", field_el)
        if form_el:
            for sel in SUBMIT_SELS:
                candidates = page.evaluate(
                    f"([form, sel]) => Array.from(form.querySelectorAll(sel))"
                    f".filter(b => b.offsetWidth > 0)"
                    f".map(b => ({{ text: b.innerText.trim().toLowerCase(), id: b.id, el: b }}))",
                    [form_el, sel],
                )
                for c in candidates:
                    if any(h in c["text"] for h in TEXT_HINTS) or c["id"]:
                        logger.info(f"[{monitor_id}] Submit (form) id={c['id']!r} text={c['text']!r}")
                        # retorna via handle direto
                        return page.evaluate_handle(
                            f"([form, sel]) => Array.from(form.querySelectorAll(sel))"
                            f".filter(b => b.offsetWidth > 0)[0]",
                            [form_el, sel],
                        )

        # 2) sobe até encontrar um contêiner de login e busca lá dentro
        container_el = page.evaluate(
            "el => el.closest('[class*=\"login\"], [class*=\"Login\"], [id*=\"login\"], [id*=\"Login\"], "
            "[class*=\"form\"], [id*=\"form\"]') || el.parentElement?.parentElement",
            field_el,
        )
        if container_el:
            for sel in SUBMIT_SELS:
                handle = page.evaluate_handle(
                    f"([c, sel]) => Array.from(c.querySelectorAll(sel))"
                    f".filter(b => b.offsetWidth > 0)[0]",
                    [container_el, sel],
                )
                # evaluate_handle returns JSHandle — check if not undefined
                tp = page.evaluate("h => h ? h.tagName : null", handle)
                if tp:
                    logger.info(f"[{monitor_id}] Submit (container) sel={sel!r}")
                    return handle

    except Exception as e:
        logger.debug(f"[{monitor_id}] _find_submit_near erro: {e}")

    # 3) fallback global, excluindo nav/header
    return _find_submit(page, exclude_nav=True)


def _find_submit(page, exclude_nav: bool = False):
    SELS = [
        'button[type="submit"]', 'input[type="submit"]',
        'button:has-text("Entrar")', 'button:has-text("Login")',
        'button:has-text("Sign in")', 'button:has-text("Acessar")',
        'button:has-text("Conectar")', 'button:has-text("Continuar")',
        'button:has-text("OK")',
        '[data-testid*="login"]', '[data-testid*="submit"]',
    ]
    for sel in SELS:
        el = _find_first_visible(page, sel)
        if el:
            if exclude_nav and _is_inside_nav(page, el):
                continue
            return el
    for frame in page.frames[1:]:
        for sel in SELS:
            el = _find_first_visible(frame, sel)
            if el:
                return el
    return None


def _is_inside_nav(page, el) -> bool:
    """Retorna True se o elemento esta dentro de nav, header ou topbar — provavel link de navegacao."""
    try:
        return page.evaluate(
            "el => !!el.closest('nav, header, [class*=\"topbar\"], [class*=\"navbar\"], [role=\"navigation\"]')",
            el,
        )
    except Exception:
        return False


# ── Navegacao ao menu ──────────────────────────────────────────────────────────

def _navigate_to_menu(page, selector: str, monitor_id: int):
    from playwright.sync_api import TimeoutError as PWTimeout

    if selector.strip().lower().startswith("url:"):
        target = selector.strip()[4:].strip()
        logger.info(f"[{monitor_id}] Navegando diretamente para: {target}")
        try:
            page.goto(target, wait_until="networkidle")
        except PWTimeout:
            page.goto(target, wait_until="domcontentloaded")
            _wait_stable(page)
        return

    for attempt in range(1, SELECTOR_RETRIES + 1):
        logger.info(f"[{monitor_id}] Tentativa {attempt}/{SELECTOR_RETRIES} CSS: {selector!r} | URL: {page.url}")
        try:
            el = page.wait_for_selector(selector, timeout=8_000, state="visible")
            if el:
                page.evaluate("el => el.scrollIntoView({block:'center'})", el)
                el.click()
                _wait_after_menu_click(page, monitor_id)
                return
        except PWTimeout:
            logger.warning(f"[{monitor_id}] CSS timeout tentativa {attempt}.")
        except Exception as e:
            logger.warning(f"[{monitor_id}] CSS erro tentativa {attempt}: {e}")
        if attempt < SELECTOR_RETRIES:
            time.sleep(SELECTOR_RETRY_WAIT)
            _wait_stable(page)

    for attempt in range(1, SELECTOR_RETRIES + 1):
        for exact in (True, False):
            try:
                el = page.get_by_text(selector, exact=exact).first
                el.wait_for(state="visible", timeout=5_000)
                page.evaluate("el => el.scrollIntoView({block:'center'})", el)
                el.click()
                _wait_after_menu_click(page, monitor_id)
                logger.info(f"[{monitor_id}] Encontrado por texto (exact={exact}).")
                return
            except Exception:
                continue
        if attempt < SELECTOR_RETRIES:
            time.sleep(SELECTOR_RETRY_WAIT)

    for role in ("link", "button", "menuitem"):
        try:
            el = page.get_by_role(role, name=selector).first
            el.wait_for(state="visible", timeout=4_000)
            el.click()
            _wait_after_menu_click(page, monitor_id)
            logger.info(f"[{monitor_id}] Encontrado por role={role}.")
            return
        except Exception:
            continue

    raise RuntimeError(
        f"SELECTOR_NOT_FOUND: seletor={selector!r} | "
        f"URL atual={page.url!r} | titulo={page.title()!r} | "
        f"Dica: use F12, inspecione o elemento e copie o seletor CSS, "
        f"ou use 'url:https://...' para navegar diretamente apos o login."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wait_stable(page, min_wait_ms: int = 0):
    from playwright.sync_api import TimeoutError as PWTimeout
    if min_wait_ms > 0:
        time.sleep(min_wait_ms / 1000)
    try:
        page.wait_for_load_state("networkidle", timeout=12_000)
    except PWTimeout:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=6_000)
        except PWTimeout:
            pass


def _wait_after_menu_click(page, monitor_id: int):
    """Aguarda a página carregar completamente após clicar no menu alvo.
    Levanta RuntimeError se o carregamento não for concluído — garante que
    o sucesso só seja registrado quando a página de fato abriu."""
    from playwright.sync_api import TimeoutError as PWTimeout
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
        logger.info(f"[{monitor_id}] Página carregou completamente (networkidle) após clique no menu.")
    except PWTimeout:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=8_000)
            logger.info(f"[{monitor_id}] Página carregou (domcontentloaded) após clique no menu.")
        except PWTimeout:
            raise RuntimeError(
                f"PAGE_LOAD_TIMEOUT: Página não carregou após clicar no menu alvo. "
                f"URL atual: {page.url!r}"
            )


def _find_first_visible(frame_or_page, selector: str):
    try:
        el = frame_or_page.query_selector(selector)
        if el and el.is_visible():
            return el
    except Exception:
        pass
    return None


def _classify_error(exc: Exception) -> str:
    msg = str(exc)
    low = msg.lower()
    if "selector_not_found" in low or "seletor" in low:
        return msg
    if "timeout" in low:
        return f"TIMEOUT: {msg}"
    if "net::" in low or "connection" in low or "refused" in low:
        return f"CONNECTION_ERROR: {msg}"
    if "auth" in low or "senha" in low or "credencial" in low:
        return f"AUTH_ERROR: {msg}"
    return msg
