from emotion_engine import emotional_guard, get_emotional_state


def controlar_emocao():
    estado = get_emotional_state()
    protecao = emotional_guard()

    print("===================================")
    print("EMOTION FILTER")
    print("===================================")
    print(f"Estado: {estado['emotion']}")
    print(f"Intensidade: {estado['intensity']}%")
    print(f"Motivo: {estado['reason']}")
    print(protecao["rule"])

    return {
        "state": estado,
        "guard": protecao,
    }
