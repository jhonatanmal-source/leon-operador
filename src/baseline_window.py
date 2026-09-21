"""Janela de dias corridos para a base de desempenho do LEON.

Fornece um helper único para ler a janela configurada em [BASELINE] window_days
(fallback 30) e um parser de datas robusto/tolerante, compartilhados pelos
módulos que calculam winrate e liberam a base operacional.

Missão: MISSION-20260817-BASE-DIAS-CORRIDOS
"""

import configparser
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"

DEFAULT_WINDOW_DAYS = 30


def obter_window_days():
    """Retorna a janela de dias corridos da base de desempenho (fallback 30).

    Lê a seção [BASELINE] do config.ini. Se ausente ou inválida, retorna
    DEFAULT_WINDOW_DAYS.
    """
    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE, encoding="utf-8")
    except (configparser.Error, OSError):
        return DEFAULT_WINDOW_DAYS

    if not config.has_section("BASELINE"):
        return DEFAULT_WINDOW_DAYS

    try:
        valor = config.getint("BASELINE", "window_days", fallback=DEFAULT_WINDOW_DAYS)
    except (ValueError, configparser.Error):
        return DEFAULT_WINDOW_DAYS

    return valor if valor > 0 else DEFAULT_WINDOW_DAYS


def parse_datetime(valor):
    """Parser de data robusto e tolerante.

    Aceita ISO 8601 com 'T' ou espaço (ex.: '2026-08-12T23:05:15' e
    '2026-08-12 23:05:15.156821'). Retorna datetime ou None se inválida.
    Datas inválidas/vazias devem ser EXCLUÍDAS da janela pelo chamador.
    """
    if not valor:
        return None

    texto = str(valor).strip()
    if not texto:
        return None

    resultado = None
    try:
        resultado = datetime.fromisoformat(texto)
    except ValueError:
        pass

    # Fallback: normaliza espaço para 'T' e tenta novamente
    if resultado is None:
        try:
            resultado = datetime.fromisoformat(texto.replace(" ", "T", 1))
        except ValueError:
            pass

    # Fallback final: formatos comuns sem frações
    if resultado is None:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                resultado = datetime.strptime(texto, fmt)
                break
            except ValueError:
                continue

    if resultado is None:
        return None

    # Normaliza para naive: descarta tzinfo para evitar comparacao
    # offset-aware vs offset-naive (datetime.now() e naive).
    if resultado.tzinfo is not None:
        resultado = resultado.replace(tzinfo=None)

    return resultado


def dentro_da_janela(valor, window_days, agora=None):
    """Retorna True se 'valor' (data) está dentro da janela de dias corridos.

    - window_days None/<=0: sem filtro → sempre True (compatibilidade)
    - data inválida/vazia: EXCLUÍDA da janela → False (quando há filtro)
    """
    if not window_days or window_days <= 0:
        return True

    momento = parse_datetime(valor)
    if momento is None:
        return False

    referencia = agora or datetime.now()
    limite = referencia - timedelta(days=window_days)
    return momento >= limite
