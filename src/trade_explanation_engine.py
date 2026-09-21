def explicar_trade(
    tendencia,
    estrutura,
    bos,
    choch,
    smc,
    elliott,
    brain_score,
    confianca,
):
    print()
    print("===================================")
    print("TRADE EXPLANATION")
    print("===================================")
    print("MOTIVOS DA OPERACAO")
    print()
    print(f"Tendencia : {tendencia}")
    print(f"Estrutura : {estrutura}")
    print(f"BOS       : {bos}")
    print(f"CHOCH     : {choch}")
    print(f"SMC       : {smc}")
    print(f"Elliott   : {elliott}")
    print(f"Brain     : {brain_score}")
    print(f"Confianca : {confianca}")

    print()
    print("CONCLUSAO")
    if confianca == "MUITO ALTA":
        print("SETUP DE ALTA QUALIDADE")
    elif confianca == "ALTA":
        print("SETUP OBSERVAVEL")
    else:
        print("SETUP FRACO")
