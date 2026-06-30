from __future__ import annotations
"""
ferias_calc.py — Cálculo de Férias CLT
Regras: 30 dias corridos por ano de trabalho, divisão em até 3 períodos
"""
from datetime import datetime, timedelta
from typing import List, Dict


class FeriasCalculador:
    """Calculadora de férias segundo CLT brasileira."""

    # Constantes CLT
    DIAS_FERIAS_POR_ANO = 30  # 30 dias corridos por ano
    ADICIONAL_FERIAS = 1/3    # Adicional constitucional de 1/3

    # Regras de fracionamento
    FRACIONAMENTO_OPCOES = [
        {
            "nome": "Período integral",
            "descricao": "Todas as férias em um único período",
            "periodos": [30],  # 30 dias em uma única parte
            "regra": "Sem restrições"
        },
        {
            "nome": "Período fracionado em 2 partes",
            "descricao": "Dividido em dois períodos",
            "periodos": [14, 16],  # 14 dias + 16 dias
            "regra": "Mínimo 5 dias corridos por período"
        },
        {
            "nome": "Período fracionado em 3 partes",
            "descricao": "Dividido em três períodos",
            "periodos": [14, 8, 8],  # 14 dias + 8 dias + 8 dias
            "regra": "Mínimo 14 dias em um período e 5 dias nos demais"
        }
    ]

    @staticmethod
    def calcular_dias_ferias(dias_trabalhados: int) -> int:
        """
        Calcula dias de férias proporcionais baseado em dias trabalhados.

        CLT:
        - 12 meses completos: 30 dias
        - Proporcionais: 2,5 dias por mês de trabalho
        """
        if dias_trabalhados >= 330:  # ~12 meses
            return 30
        # 2,5 dias por mês de trabalho (30 / 12)
        meses = dias_trabalhados / 30
        return int(meses * 2.5)

    @staticmethod
    def calcular_valor_ferias(salario_mensal: float, dias: int, incluir_adicional: bool = True) -> Dict[str, float]:
        """
        Calcula o valor total das férias.

        Args:
            salario_mensal: Salário mensal bruto do colaborador
            dias: Dias de férias a usufruir
            incluir_adicional: Se deve incluir o adicional de 1/3 (padrão: True)

        Returns:
            Dicionário com valores discriminados
        """
        valor_diario = salario_mensal / 30
        valor_base = valor_diario * dias
        valor_adicional = valor_base * FeriasCalculador.ADICIONAL_FERIAS if incluir_adicional else 0

        return {
            "salario_mensal": salario_mensal,
            "dias": dias,
            "valor_diario": round(valor_diario, 2),
            "valor_base": round(valor_base, 2),
            "valor_adicional": round(valor_adicional, 2),
            "valor_total": round(valor_base + valor_adicional, 2),
        }

    @staticmethod
    def validar_fracionamento(periodos: List[int]) -> tuple[bool, str]:
        """
        Valida se o fracionamento está dentro das regras CLT.

        Regras:
        - Máximo 3 períodos
        - Mínimo 14 dias em um dos períodos
        - Mínimo 5 dias nos demais períodos
        - Soma total = 30 dias (ou valor especificado)
        """
        total_dias = sum(periodos)

        # Validação 1: Máximo 3 períodos
        if len(periodos) > 3:
            return False, "Máximo de 3 períodos permitidos"

        # Validação 2: Soma total
        if total_dias != 30:
            return False, f"Total deve ser 30 dias, obtido {total_dias}"

        # Validação 3: Regra de dias mínimos
        if len(periodos) == 1:
            # Um único período: OK (sem limite mínimo especial)
            return True, ""

        if len(periodos) == 2:
            # Dois períodos: ambos devem ter mínimo 5 dias
            if any(d < 5 for d in periodos):
                return False, "Dois períodos: mínimo 5 dias cada"
            return True, ""

        if len(periodos) == 3:
            # Três períodos: mínimo 14 em um e 5 nos demais
            periodos_sorted = sorted(periodos, reverse=True)
            if periodos_sorted[0] < 14:
                return False, "Três períodos: mínimo 14 dias no maior"
            if periodos_sorted[1] < 5 or periodos_sorted[2] < 5:
                return False, "Três períodos: mínimo 5 dias nos demais"
            return True, ""

        return False, "Configuração inválida"

    @staticmethod
    def gerar_opcoes_fracionamento(dias_totais: int = 30) -> List[Dict]:
        """
        Gera todas as opções válidas de fracionamento para a quantidade de dias.
        """
        opcoes = []

        # Opção 1: Período integral
        opcoes.append({
            "id": 1,
            "nome": "Período Integral",
            "descricao": "Usar todas as férias em um único período",
            "periodos": [dias_totais],
            "valido": True,
            "observacao": "Sem restrições de data"
        })

        # Opção 2: Fracionado em 2 partes
        # Distribuições: (5,25), (10,20), (15,15), (20,10), (25,5)
        if dias_totais >= 10:
            opcoes_2 = []
            for p1 in range(5, dias_totais - 4):
                p2 = dias_totais - p1
                if p1 >= 5 and p2 >= 5:
                    opcoes_2.append({
                        "id": 2.0 + (len(opcoes_2) * 0.1),
                        "nome": f"Fracionado em 2 períodos: {p1} + {p2} dias",
                        "descricao": f"{p1} dias em um período e {p2} dias em outro",
                        "periodos": [p1, p2],
                        "valido": True,
                        "observacao": "Um período pode ser fracionado em até 2 vezes"
                    })
            opcoes.extend(opcoes_2[:5])  # Limita a 5 opções para não poluir

        # Opção 3: Fracionado em 3 partes
        # Distribuição padrão: (14, 8, 8)
        if dias_totais >= 24:
            opcoes.append({
                "id": 3,
                "nome": "Fracionado em 3 períodos",
                "descricao": f"Dividido em {dias_totais // 3} + {dias_totais // 3} + {dias_totais % 3 + dias_totais // 3} dias",
                "periodos": [14, 8, 8] if dias_totais == 30 else [dias_totais // 3] * 3,
                "valido": True,
                "observacao": "Máximo 3 períodos (mínimo 14 em um e 5 nos demais)"
            })

        return opcoes

    @staticmethod
    def classificar_status_ferias(data_admissao: str, ferias_list: List[Dict]) -> Dict:
        """
        Classifica o status de férias baseado na data de admissão e histórico de marcações.

        Regras:
        - "Férias programadas": Se houver pedido pendente ou aprovado no futuro.
        - "Férias em aberto": 12 meses de empresa completados e sem marcação.
        - "Férias vencendo": 6 meses antes de vencer o período concessivo (18 meses de empresa).
        - "Programar Férias Urgente": 3 meses antes de vencer o período concessivo (21 meses de empresa).
        """
        if not data_admissao:
            return {"status": "Sem data de admissão", "cor": "#94a3b8", "classe": "aberto"}

        try:
            # Formatos aceitos: YYYY-MM-DD ou DD/MM/YYYY
            if "/" in data_admissao:
                adm = datetime.strptime(data_admissao, "%d/%m/%Y")
            else:
                adm = datetime.strptime(data_admissao, "%Y-%m-%d")
        except Exception:
            return {"status": "Data inválida", "cor": "#94a3b8", "classe": "aberto"}

        hoje = datetime.now()
        dias_empresa = (hoje - adm).days

        # Verifica se já tem alguma férias futura programada (pendente ou aprovada)
        tem_programada = any(f.get("status") in ("pendente", "aprovada") for f in ferias_list)

        if tem_programada:
            return {"status": "Férias programadas", "cor": "#16a34a", "classe": "programada"}

        # Se não tem programada, avalia prazos legais
        # Período aquisitivo = 12 meses (365 dias)
        # Período concessivo = +12 meses (limite 730 dias)

        if dias_empresa < 365:
            return {"status": "Em período aquisitivo", "cor": "#0369a1", "classe": "aquisitivo"}

        # Dias restantes para o limite do período concessivo (24 meses)
        dias_limite = 730 - dias_empresa

        if dias_limite <= 90:  # 3 meses ou menos
            return {"status": "Programar Férias Urgente", "cor": "#dc2626", "classe": "urgente"}
        if dias_limite <= 180: # 6 meses ou menos
            return {"status": "Férias vencendo", "cor": "#d97706", "classe": "vencendo"}

        return {"status": "Férias em aberto", "cor": "#0369a1", "classe": "aberto"}
    @staticmethod
    def calcular_ferias_detalhado(
        salario_mensal: float,
        dias_ferias: int,
        data_inicio: str,
        periodos: List[Dict] = None
    ) -> Dict:
        """
        Cálculo completo de férias com fracionamento.

        Args:
            salario_mensal: Salário mensal bruto
            dias_ferias: Total de dias de férias
            data_inicio: Data de início (formato YYYY-MM-DD)
            periodos: Lista de períodos [{data_inicio, duracao_dias}, ...]

        Returns:
            Dicionário com informações completas de férias
        """
        # Calcula valores
        valores = FeriasCalculador.calcular_valor_ferias(salario_mensal, dias_ferias)

        # Valida fracionamento se especificado
        duracao_periodos = [p.get("duracao_dias", 0) for p in (periodos or [])]
        valido = True
        mensagem = ""

        if periodos:
            valido, mensagem = FeriasCalculador.validar_fracionamento(duracao_periodos)

        return {
            "resumo": {
                "salario_mensal": salario_mensal,
                "dias_totais": dias_ferias,
                "data_inicio": data_inicio,
                "fracionado": len(periodos) > 1 if periodos else False,
                "total_periodos": len(periodos) if periodos else 1,
            },
            "valores": valores,
            "periodos": periodos or [{"data_inicio": data_inicio, "duracao_dias": dias_ferias}],
            "validacao": {
                "valido": valido,
                "mensagem": mensagem
            },
            "regras_clt": {
                "dias_minimos_periodo_unico": 0,
                "dias_minimos_dois_periodos": 5,
                "dias_minimos_periodo_maior_tres": 14,
                "dias_minimos_demais_periodos_tres": 5,
                "maximo_periodos": 3
            }
        }
