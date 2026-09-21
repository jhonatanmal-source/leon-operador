from institutional_analysis_engine import analyze_fibonacci_wave_setup


def pivot(tipo, preco):
    return {"type": tipo, "price": preco}


def executar_teste():
    onda_tres_alta = analyze_fibonacci_wave_setup(
        [
            pivot("LOW", 100),
            pivot("HIGH", 110),
            pivot("LOW", 103),
        ],
        "ALTA",
    )
    assert onda_tres_alta["valid"] is True
    assert onda_tres_alta["target_wave"] == "ONDA 3"
    assert onda_tres_alta["retracement"] == 0.7

    onda_cinco_baixa = analyze_fibonacci_wave_setup(
        [
            pivot("HIGH", 120),
            pivot("LOW", 110),
            pivot("HIGH", 116),
            pivot("LOW", 96),
            pivot("HIGH", 104),
        ],
        "BAIXA",
    )
    assert onda_cinco_baixa["valid"] is True
    assert onda_cinco_baixa["target_wave"] == "ONDA 5"
    assert onda_cinco_baixa["retracement"] == 0.4

    fora_da_zona = analyze_fibonacci_wave_setup(
        [
            pivot("LOW", 100),
            pivot("HIGH", 110),
            pivot("LOW", 108),
        ],
        "ALTA",
    )
    assert fora_da_zona["valid"] is False
    print("OK: setups Fibonacci de Onda 3 e Onda 5 validados")


if __name__ == "__main__":
    executar_teste()
