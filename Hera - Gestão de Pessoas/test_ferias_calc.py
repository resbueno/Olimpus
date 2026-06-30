from __future__ import annotations
"""
test_ferias_calc.py — Testes para o módulo de cálculo de férias CLT
"""
import sys
import os

# Adiciona diretório ao path
sys.path.insert(0, os.path.dirname(__file__))

# Força encoding UTF-8 em Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from ferias_calc import FeriasCalculador


def test_calcular_valor_ferias():
    """Testa cálculo básico de férias."""
    resultado = FeriasCalculador.calcular_valor_ferias(
        salario_mensal=3000.00,
        dias=30,
        incluir_adicional=True
    )

    assert resultado["salario_mensal"] == 3000.00
    assert resultado["dias"] == 30
    assert resultado["valor_diario"] == 100.00
    assert resultado["valor_base"] == 3000.00
    assert resultado["valor_adicional"] == 1000.00
    assert resultado["valor_total"] == 4000.00
    print("[PASS] test_calcular_valor_ferias")


def test_calcular_valor_ferias_proporcional():
    """Testa cálculo de férias proporcionais."""
    resultado = FeriasCalculador.calcular_valor_ferias(
        salario_mensal=2000.00,
        dias=15,
        incluir_adicional=True
    )

    assert resultado["valor_diario"] == round(2000.00 / 30, 2)
    assert resultado["valor_base"] == round(2000.00 / 30 * 15, 2)
    expected_adicional = round(resultado["valor_base"] * (1/3), 2)
    assert resultado["valor_adicional"] == expected_adicional
    print("[PASS] test_calcular_valor_ferias_proporcional")


def test_validar_fracionamento_1_periodo():
    """Testa validação de 1 período."""
    valido, msg = FeriasCalculador.validar_fracionamento([30])
    assert valido is True
    assert msg == ""
    print("[PASS] test_validar_fracionamento_1_periodo")


def test_validar_fracionamento_2_periodos_valido():
    """Testa validação de 2 períodos válidos."""
    valido, msg = FeriasCalculador.validar_fracionamento([14, 16])
    assert valido is True
    print("[PASS] test_validar_fracionamento_2_periodos_valido (14/16)")

    valido, msg = FeriasCalculador.validar_fracionamento([15, 15])
    assert valido is True
    print("[PASS] test_validar_fracionamento_2_periodos_valido (15/15)")


def test_validar_fracionamento_2_periodos_invalido():
    """Testa validação de 2 períodos inválidos."""
    # Um período menor que 5 dias
    valido, msg = FeriasCalculador.validar_fracionamento([4, 26])
    assert valido is False
    assert "mínimo 5 dias" in msg
    print("[PASS] test_validar_fracionamento_2_periodos_invalido (4/26)")

    # Soma diferente de 30
    valido, msg = FeriasCalculador.validar_fracionamento([14, 15])
    assert valido is False
    assert "Total deve ser 30 dias" in msg
    print("[PASS] test_validar_fracionamento_2_periodos_invalido (14/15)")


def test_validar_fracionamento_3_periodos_valido():
    """Testa validação de 3 períodos válidos."""
    valido, msg = FeriasCalculador.validar_fracionamento([14, 8, 8])
    assert valido is True
    print("[PASS] test_validar_fracionamento_3_periodos_valido (14/8/8)")

    # Variação: 15, 10, 5
    valido, msg = FeriasCalculador.validar_fracionamento([15, 10, 5])
    assert valido is True
    print("[PASS] test_validar_fracionamento_3_periodos_valido (15/10/5)")


def test_validar_fracionamento_3_periodos_invalido():
    """Testa validação de 3 períodos inválidos."""
    # Maior período < 14 dias
    valido, msg = FeriasCalculador.validar_fracionamento([13, 10, 7])
    assert valido is False
    assert "mínimo 14 dias" in msg
    print("[PASS] test_validar_fracionamento_3_periodos_invalido (13/10/7)")

    # Um dos menores períodos < 5 dias
    valido, msg = FeriasCalculador.validar_fracionamento([14, 4, 12])
    assert valido is False
    assert "mínimo 5 dias" in msg
    print("[PASS] test_validar_fracionamento_3_periodos_invalido (14/4/12)")


def test_validar_fracionamento_4_periodos():
    """Testa que 4 períodos é inválido."""
    valido, msg = FeriasCalculador.validar_fracionamento([10, 8, 7, 5])
    assert valido is False
    assert "Máximo de 3 períodos" in msg
    print("[PASS] test_validar_fracionamento_4_periodos")


def test_gerar_opcoes_fracionamento():
    """Testa geração de opções de fracionamento."""
    opcoes = FeriasCalculador.gerar_opcoes_fracionamento(30)

    # Deve ter pelo menos 3 opções
    assert len(opcoes) >= 3
    print(f"[PASS] test_gerar_opcoes_fracionamento ({len(opcoes)} opcoes)")

    # Primeira opção deve ser integral (1 período)
    assert opcoes[0]["periodos"] == [30]
    print("[INFO] Primeira opcao eh integral")

    # Todas as opções devem ter periodos que somam 30
    for opt in opcoes:
        assert sum(opt["periodos"]) == 30, f"Opcao {opt['nome']} nao soma 30"
    print("[INFO] Todas as opcoes somam 30 dias")


def test_calcular_dias_ferias():
    """Testa cálculo de dias proporcionais."""
    # 12 meses = 30 dias
    dias = FeriasCalculador.calcular_dias_ferias(365)
    assert dias == 30
    print("[PASS] test_calcular_dias_ferias (12 meses)")

    # 6 meses = ~15 dias
    dias = FeriasCalculador.calcular_dias_ferias(180)
    assert dias == 15
    print("[PASS] test_calcular_dias_ferias (6 meses)")

    # 1 mês = ~2.5 dias (arredonda para 2)
    dias = FeriasCalculador.calcular_dias_ferias(30)
    assert dias == 2
    print("[PASS] test_calcular_dias_ferias (1 mes)")


def test_calcular_ferias_completo():
    """Testa cálculo completo com fracionamento."""
    periodos = [
        {"data_inicio": "2024-01-15", "data_fim": "2024-01-28", "duracao_dias": 14},
        {"data_inicio": "2024-06-01", "data_fim": "2024-06-08", "duracao_dias": 8},
        {"data_inicio": "2024-12-01", "data_fim": "2024-12-08", "duracao_dias": 8}
    ]

    resultado = FeriasCalculador.calcular_ferias_completo(
        salario_mensal=3000.00,
        dias_ferias=30,
        data_inicio="2024-01-15",
        periodos=periodos
    )

    assert resultado["resumo"]["dias_totais"] == 30
    assert resultado["resumo"]["total_periodos"] == 3
    assert resultado["resumo"]["fracionado"] is True
    assert resultado["validacao"]["valido"] is True
    assert resultado["valores"]["valor_total"] == 4000.00
    print("[PASS] test_calcular_ferias_completo")


def run_all_tests():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("Executando testes de Calculo de Ferias CLT")
    print("="*60 + "\n")

    tests = [
        test_calcular_valor_ferias,
        test_calcular_valor_ferias_proporcional,
        test_validar_fracionamento_1_periodo,
        test_validar_fracionamento_2_periodos_valido,
        test_validar_fracionamento_2_periodos_invalido,
        test_validar_fracionamento_3_periodos_valido,
        test_validar_fracionamento_3_periodos_invalido,
        test_validar_fracionamento_4_periodos,
        test_gerar_opcoes_fracionamento,
        test_calcular_dias_ferias,
        test_calcular_ferias_completo,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {test.__name__}: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Resultados: {passed} passou, {failed} falhou")
    print("="*60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
