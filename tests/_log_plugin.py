from __future__ import annotations
"""
_log_plugin.py — Plugin pytest compartilhado para geração de relatório de testes.
Importado por cada conftest.py de app para gerar log estruturado.

Uso no conftest.py do app:
    from tests._log_plugin import gerar_relatorio_final
    ...
    def pytest_terminal_summary(terminalreporter, exitstatus):
        gerar_relatorio_final(terminalreporter, exitstatus, APP_NOME, LOG_PATH)
"""

import os
from datetime import datetime
from pathlib import Path


def gerar_relatorio_final(terminalreporter, exitstatus, app_nome: str, log_path: str):
    """Gera arquivo de log estruturado com resultado dos testes."""
    stats   = terminalreporter.stats
    passed  = stats.get("passed",  [])
    failed  = stats.get("failed",  [])
    error   = stats.get("error",   [])
    skipped = stats.get("skipped", [])

    total   = len(passed) + len(failed) + len(error)
    agora   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    linhas = [
        "=" * 70,
        f"  OLIMPUS — PLANO DE TESTES: {app_nome.upper()}",
        f"  Data/Hora: {agora}",
        "=" * 70,
        "",
    ]

    # Seção PASSARAM
    if passed:
        linhas.append(f"  PASSOU ({len(passed)})")
        linhas.append("-" * 70)
        for rep in passed:
            nome = _nome_teste(rep)
            linhas.append(f"  [PASSOU]  {nome}")
        linhas.append("")

    # Seção FALHARAM
    if failed or error:
        all_fail = failed + error
        linhas.append(f"  FALHOU ({len(all_fail)})")
        linhas.append("-" * 70)
        for rep in all_fail:
            nome = _nome_teste(rep)
            linhas.append(f"  [FALHOU]  {nome}")
            # Captura mensagem de erro resumida
            if hasattr(rep, "longrepr") and rep.longrepr:
                msg = str(rep.longrepr)
                # Pega só a última linha útil
                linhas_err = [l.strip() for l in msg.splitlines() if l.strip()]
                if linhas_err:
                    linhas.append(f"            {linhas_err[-1][:120]}")
        linhas.append("")

    # Seção IGNORADOS
    if skipped:
        linhas.append(f"  IGNORADOS ({len(skipped)})")
        linhas.append("-" * 70)
        for rep in skipped:
            nome = _nome_teste(rep)
            razao = rep.longrepr[-1] if isinstance(rep.longrepr, tuple) else str(rep.longrepr)
            linhas.append(f"  [IGNORADO] {nome}  →  {razao[:80]}")
        linhas.append("")

    # Resumo final
    linhas.append("=" * 70)
    status_geral = "APROVADO" if (not failed and not error) else "REPROVADO"
    linhas.append(f"  RESULTADO GERAL: {status_geral}")
    linhas.append(f"  Total: {total}  |  Passou: {len(passed)}  |  Falhou: {len(failed) + len(error)}  |  Ignorados: {len(skipped)}")
    linhas.append("=" * 70)

    conteudo = "\n".join(linhas) + "\n"

    # Escreve no arquivo
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(conteudo)

    # Exibe no terminal também
    print("\n" + conteudo)
    print(f"\n  Log salvo em: {log_path}\n")


def _nome_teste(rep) -> str:
    """Extrai nome legível do relatório de teste."""
    nodeid = getattr(rep, "nodeid", str(rep))
    # Remove caminho do arquivo, mantém classe::metodo
    partes = nodeid.split("::")
    if len(partes) >= 3:
        return f"{partes[-2]}::{partes[-1]}"
    elif len(partes) == 2:
        return partes[-1]
    return nodeid
