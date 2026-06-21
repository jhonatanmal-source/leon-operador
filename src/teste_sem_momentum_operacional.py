from operator_status import _diagnosticar_alinhamento


def executar_teste():
    alinhamento = _diagnosticar_alinhamento(
        {"tendencia": "BAIXA", "momentum": "ALTA"},
        {
            "smc": "BEARISH",
            "direcao": "VENDA",
            "elliott": "ONDA 3",
        },
    )

    assert alinhamento["status"] == "ALINHADO"
    assert alinhamento["alinhamento"] == "BAIXA"
    print("OK: momentum nao participa do bloqueio operacional")


if __name__ == "__main__":
    executar_teste()
