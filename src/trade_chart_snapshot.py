# ===================================
# TRADE CHART SNAPSHOT
# ===================================

import csv
import struct
import zlib
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
CANDLE_HISTORY_FILE = DATA_DIR / "candle_history.csv"
SNAPSHOT_DIR = REPORTS_DIR / "trade_snapshots"


def _ler_candles(ativo, limite=80):

    if not CANDLE_HISTORY_FILE.exists():
        return []

    candles = []

    with CANDLE_HISTORY_FILE.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=";")

        for linha in leitor:
            if len(linha) < 6 or linha[1] != ativo:
                continue

            try:
                candles.append({
                    "time": linha[0],
                    "open": float(linha[2]),
                    "high": float(linha[3]),
                    "low": float(linha[4]),
                    "close": float(linha[5]),
                })
            except ValueError:
                continue

    return candles[-limite:]


def _chunk(tipo, dados):

    return (
        struct.pack(">I", len(dados))
        + tipo
        + dados
        + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
    )


def _salvar_png(caminho, pixels, largura, altura):

    linhas = []

    for y in range(altura):
        linha = bytearray()
        linha.append(0)

        for cor in pixels[y * largura:(y + 1) * largura]:
            linha.extend(cor)

        linhas.append(bytes(linha))

    bruto = b"".join(linhas)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(bruto, 9))
        + _chunk(b"IEND", b"")
    )
    caminho.write_bytes(png)


def _set_pixel(pixels, largura, altura, x, y, cor):

    if 0 <= x < largura and 0 <= y < altura:
        pixels[y * largura + x] = cor


def _linha(pixels, largura, altura, x1, y1, x2, y2, cor):

    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    erro = dx + dy

    while True:
        _set_pixel(pixels, largura, altura, x1, y1, cor)

        if x1 == x2 and y1 == y2:
            break

        dobro = 2 * erro

        if dobro >= dy:
            erro += dy
            x1 += sx

        if dobro <= dx:
            erro += dx
            y1 += sy


def _retangulo(pixels, largura, altura, x1, y1, x2, y2, cor):

    for y in range(max(0, y1), min(altura, y2 + 1)):
        for x in range(max(0, x1), min(largura, x2 + 1)):
            _set_pixel(pixels, largura, altura, x, y, cor)


def gerar_print_entrada(
    ativo,
    direcao,
    entrada,
    stop,
    take_profit,
    pre_operation_id=None,
):

    candles = _ler_candles(ativo)

    if len(candles) < 3:
        return {
            "ok": False,
            "error": "INSUFFICIENT_CANDLES_FOR_SNAPSHOT",
        }

    largura = 1100
    altura = 620
    margem_esq = 70
    margem_dir = 30
    margem_topo = 70
    margem_base = 70
    area_largura = largura - margem_esq - margem_dir
    area_altura = altura - margem_topo - margem_base

    fundo = (9, 11, 15)
    grade = (35, 42, 52)
    texto = (230, 235, 242)
    alta = (99, 197, 139)
    baixa = (228, 91, 91)
    entrada_cor = (212, 175, 55)
    stop_cor = (228, 91, 91)
    tp_cor = (99, 197, 139)

    pixels = [fundo] * (largura * altura)

    precos = []
    for candle in candles:
        precos.extend([candle["high"], candle["low"]])
    precos.extend([float(entrada), float(stop), float(take_profit)])

    minimo = min(precos)
    maximo = max(precos)
    folga = max((maximo - minimo) * 0.08, 0.5)
    minimo -= folga
    maximo += folga

    def y_preco(preco):
        proporcao = (float(preco) - minimo) / (maximo - minimo)
        return int(margem_topo + area_altura - (proporcao * area_altura))

    def x_indice(indice):
        if len(candles) == 1:
            return margem_esq + area_largura // 2
        return int(margem_esq + (indice / (len(candles) - 1)) * area_largura)

    for i in range(6):
        y = margem_topo + int((area_altura / 5) * i)
        _linha(pixels, largura, altura, margem_esq, y, largura - margem_dir, y, grade)

    candle_largura = max(4, min(10, area_largura // max(len(candles), 1) // 2))

    for indice, candle in enumerate(candles):
        x = x_indice(indice)
        y_open = y_preco(candle["open"])
        y_high = y_preco(candle["high"])
        y_low = y_preco(candle["low"])
        y_close = y_preco(candle["close"])
        cor = alta if candle["close"] >= candle["open"] else baixa

        _linha(pixels, largura, altura, x, y_high, x, y_low, cor)
        _retangulo(
            pixels,
            largura,
            altura,
            x - candle_largura,
            min(y_open, y_close),
            x + candle_largura,
            max(y_open, y_close),
            cor,
        )

    niveis = [
        ("ENTRADA", entrada, entrada_cor),
        ("STOP", stop, stop_cor),
        ("TP", take_profit, tp_cor),
    ]

    for _, preco, cor in niveis:
        y = y_preco(preco)
        _linha(pixels, largura, altura, margem_esq, y, largura - margem_dir, y, cor)
        _retangulo(pixels, largura, altura, largura - 145, y - 8, largura - 35, y + 8, cor)

    _retangulo(pixels, largura, altura, 0, 0, largura - 1, 48, (17, 23, 32))
    _retangulo(pixels, largura, altura, 0, altura - 44, largura - 1, altura - 1, (17, 23, 32))

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    nome = (
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
        f"{pre_operation_id or 'PREOP'}_{ativo}_{direcao}.png"
    )
    caminho = SNAPSHOT_DIR / nome
    _salvar_png(caminho, pixels, largura, altura)

    rr = round(abs(float(take_profit) - float(entrada)) / abs(float(entrada) - float(stop)), 2)

    legenda = (
        f"{ativo} {direcao} | Entrada {round(float(entrada), 2)} | "
        f"SL {round(float(stop), 2)} | TP {round(float(take_profit), 2)} | RR {rr}"
    )

    return {
        "ok": True,
        "path": str(caminho),
        "caption": legenda,
        "candles": len(candles),
        "rr": rr,
    }
