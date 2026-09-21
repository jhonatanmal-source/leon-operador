from datetime import datetime
from pathlib import Path
import time

import requests

from src.telegram_config import (
    CHAT_ID,
    TELEGRAM_DEDUPE_SECONDS,
    TELEGRAM_ENABLED,
    TELEGRAM_TIMEOUT,
    TOKEN,
)


_ultima_mensagem = {
    "texto": None,
    "quando": None,
}


def _registrar_log(mensagem):

    try:
        from log_engine import registrar_log

        registrar_log(mensagem)

    except Exception:
        pass


def _registrar_erro(mensagem):

    try:
        from error_logger import registrar_erro

        registrar_erro(mensagem)

    except Exception:
        pass


def _mensagem_duplicada(texto):

    agora = datetime.now()

    if (
        _ultima_mensagem["texto"] == texto
        and _ultima_mensagem["quando"] is not None
        and (agora - _ultima_mensagem["quando"]).total_seconds()
        < TELEGRAM_DEDUPE_SECONDS
    ):
        return True

    _ultima_mensagem["texto"] = texto
    _ultima_mensagem["quando"] = agora

    return False


def enviar_mensagem(texto):

    if not TELEGRAM_ENABLED:
        _registrar_log("TELEGRAM | envio bloqueado: modulo desativado")
        return {
            "ok": False,
            "error": "TELEGRAM_DISABLED",
        }

    if not TOKEN or not CHAT_ID:
        erro = "TELEGRAM | TOKEN ou CHAT_ID nao configurado"
        _registrar_erro(erro)
        return {
            "ok": False,
            "error": "TELEGRAM_CONFIG_MISSING",
        }

    if not texto or not str(texto).strip():
        erro = "TELEGRAM | mensagem vazia bloqueada"
        _registrar_erro(erro)
        return {
            "ok": False,
            "error": "TELEGRAM_EMPTY_MESSAGE",
        }

    texto = str(texto).strip()

    if _mensagem_duplicada(texto):
        _registrar_log("TELEGRAM | mensagem duplicada bloqueada")
        return {
            "ok": False,
            "error": "TELEGRAM_DUPLICATE_MESSAGE",
        }

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
    }

    resposta = None
    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            resposta = requests.post(
                url,
                data=payload,
                timeout=TELEGRAM_TIMEOUT,
            )
            resposta.raise_for_status()
            break
        except requests.exceptions.RequestException as erro:
            ultimo_erro = erro
            if tentativa < 3:
                _registrar_log(
                    "TELEGRAM | conexao instavel; "
                    f"nova tentativa {tentativa + 1}/3"
                )
                time.sleep(tentativa * 2)

    if resposta is None:
        _registrar_erro(f"TELEGRAM | falha de conexao: {ultimo_erro}")
        return {
            "ok": False,
            "error": "TELEGRAM_CONNECTION_ERROR",
            "details": str(ultimo_erro),
        }

    try:
        dados = resposta.json()
    except ValueError as erro:
        _registrar_erro(f"TELEGRAM | resposta invalida: {erro}")
        return {
            "ok": False,
            "error": "TELEGRAM_INVALID_RESPONSE",
            "details": str(erro),
        }

    if not dados.get("ok"):
        _registrar_erro(f"TELEGRAM | API recusou envio: {dados}")
        return dados

    _registrar_log("TELEGRAM | mensagem enviada com sucesso")

    return dados


def enviar_foto(caminho, legenda=""):

    if not TELEGRAM_ENABLED:
        _registrar_log("TELEGRAM | envio de foto bloqueado: modulo desativado")
        return {
            "ok": False,
            "error": "TELEGRAM_DISABLED",
        }

    if not TOKEN or not CHAT_ID:
        erro = "TELEGRAM | TOKEN ou CHAT_ID nao configurado para foto"
        _registrar_erro(erro)
        return {
            "ok": False,
            "error": "TELEGRAM_CONFIG_MISSING",
        }

    arquivo = Path(caminho)

    if not arquivo.exists():
        erro = f"TELEGRAM | foto nao encontrada: {arquivo}"
        _registrar_erro(erro)
        return {
            "ok": False,
            "error": "TELEGRAM_PHOTO_NOT_FOUND",
            "details": str(arquivo),
        }

    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"

    try:
        with arquivo.open("rb") as imagem:
            resposta = requests.post(
                url,
                data={
                    "chat_id": CHAT_ID,
                    "caption": str(legenda or "")[:1024],
                },
                files={
                    "photo": imagem,
                },
                timeout=TELEGRAM_TIMEOUT,
            )

        resposta.raise_for_status()
        dados = resposta.json()

    except requests.exceptions.RequestException as erro:
        _registrar_erro(f"TELEGRAM | falha ao enviar foto: {erro}")
        return {
            "ok": False,
            "error": "TELEGRAM_PHOTO_CONNECTION_ERROR",
            "details": str(erro),
        }

    except ValueError as erro:
        _registrar_erro(f"TELEGRAM | resposta invalida no envio de foto: {erro}")
        return {
            "ok": False,
            "error": "TELEGRAM_PHOTO_INVALID_RESPONSE",
            "details": str(erro),
        }

    if not dados.get("ok"):
        _registrar_erro(f"TELEGRAM | API recusou foto: {dados}")
        return dados

    _registrar_log("TELEGRAM | foto enviada com sucesso")

    return dados
