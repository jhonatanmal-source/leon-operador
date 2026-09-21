def validar_decisao(qualidade, reputacao):
    reputacao_normalizada = str(reputacao or "").upper()

    if qualidade == "A+" and reputacao_normalizada in {
        "CONFIANCA ALTA",
        "CONFIANÇA ALTA",
        "CONFIANÃ‡A ALTA",
    }:
        return "EXECUTAR"

    if qualidade == "A+":
        return "OBSERVAR"

    return "BLOQUEAR"
