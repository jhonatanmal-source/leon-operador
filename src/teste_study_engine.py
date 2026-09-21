# ===================================
# TESTE STUDY ENGINE
# ===================================

import sys

from elliott_study_engine import study_elliott_context
from operational_study_engine import (
    generate_entry_checklist,
    validate_setup_a_plus,
)
from smc_study_engine import analyze_smc_context
from study_engine import (
    generate_study_report,
    get_study_by_topic,
    get_study_topics,
    load_all_studies,
    register_market_observation,
    register_study_note,
    update_study_progress,
)


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def main():

    studies = load_all_studies()
    topics = get_study_topics()
    liquidity = get_study_by_topic("Liquidez")

    note = register_study_note(
        "Liquidez",
        "LEON deve esperar varredura e reação antes de considerar entrada.",
    )
    observation = register_market_observation(
        "Liquidez",
        "XAUUSD frequentemente busca máxima/minima anterior antes de deslocar.",
    )
    progress = update_study_progress("Liquidez", "em_estudo")
    report = generate_study_report()

    fake_market_data = {
        "candles": [
            {"open": 1, "high": 3, "low": 0.5, "close": 2},
            {"open": 2, "high": 4, "low": 1.5, "close": 3},
            {"open": 3, "high": 5, "low": 2.5, "close": 4},
            {"open": 4, "high": 6, "low": 3.5, "close": 5},
            {"open": 5, "high": 7, "low": 4.5, "close": 6},
            {"open": 6, "high": 8, "low": 5.5, "close": 7},
        ]
    }
    fake_context = {
        "direction": "COMPRA",
        "trend": "ALTA",
        "momentum": "ALTA",
        "liquidity": True,
        "bos": True,
        "choch": False,
        "fvg": True,
        "order_block": False,
        "rr": 3,
        "high_impact_news": False,
        "market_state": "TENDENCIA",
    }

    print("===================================")
    print("TESTE STUDY ENGINE")
    print("===================================")
    print(f"Estudos carregados: {len(studies)}")
    print("Tópicos:")
    for topic in topics:
        print(f"- {topic}")

    print()
    print("Estudo Liquidez:")
    print(liquidity)

    print()
    print("Nota registrada:")
    print(note)

    print()
    print("Observação registrada:")
    print(observation)

    print()
    print("Progresso:")
    print(progress)

    print()
    print("Relatório:")
    print(report)

    print()
    print("SMC Context:")
    print(analyze_smc_context(fake_market_data))

    print()
    print("Elliott Context:")
    print(study_elliott_context(fake_market_data))

    print()
    print("Setup A+:")
    print(validate_setup_a_plus(fake_context))

    print()
    print("Checklist:")
    print(generate_entry_checklist(fake_context))


if __name__ == "__main__":
    main()
