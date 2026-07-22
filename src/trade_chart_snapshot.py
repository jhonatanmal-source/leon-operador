# ===================================
# TRADE CHART SNAPSHOT V2
# Suporta zonas SMC, POIs, estrutura
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


def _texto(pixels, largura, altura, x, y, texto_str, cor, tamanho=6):

    fonte = {
        "A": "0110 1001 1111 1001 1001",
        "B": "1110 1001 1110 1001 1110",
        "C": "0110 1001 1000 1001 0110",
        "D": "1110 1001 1001 1001 1110",
        "E": "1111 1000 1110 1000 1111",
        "F": "1111 1000 1110 1000 1000",
        "G": "0110 1000 1011 1001 0110",
        "H": "1001 1001 1111 1001 1001",
        "I": "111 010 010 010 111",
        "J": "0011 0001 0001 1001 0110",
        "K": "1001 1010 1100 1010 1001",
        "L": "1000 1000 1000 1000 1111",
        "M": "1001 1111 1111 1001 1001",
        "N": "1001 1101 1011 1011 1001",
        "O": "0110 1001 1001 1001 0110",
        "P": "1110 1001 1110 1000 1000",
        "Q": "0110 1001 1001 1011 0111",
        "R": "1110 1001 1110 1010 1001",
        "S": "0111 1000 0110 0001 1110",
        "T": "111 010 010 010 010",
        "U": "1001 1001 1001 1001 0110",
        "V": "10001 10001 01010 01010 00100",
        "W": "10001 10001 10101 11111 01010",
        "X": "1001 1001 0110 1001 1001",
        "Y": "10001 01010 00100 01000 10000",
        "Z": "1111 0001 0010 0100 1111",
        "0": "0110 1001 1001 1001 0110",
        "1": "010 110 010 010 111",
        "2": "0110 1001 0010 0100 1111",
        "3": "1110 0001 0110 0001 1110",
        "4": "1001 1001 1111 0001 0001",
        "5": "1111 1000 1110 0001 1110",
        "6": "0110 1000 1110 1001 0110",
        "7": "1111 0001 0010 0100 0100",
        "8": "0110 1001 0110 1001 0110",
        "9": "0110 1001 0111 0001 0110",
        ".": "00 00 00 00 11",
        "-": "00 00 11 00 00",
        ":": "11 00 11",
        "/": "0001 0010 0100 1000",
        "%": "1001 0010 0100 1001",
        "+": "010 111 010",
        " ": "",
    }

    dx = 0
    for char in texto_str.upper():
        if char in fonte:
            padrao = fonte[char]
            linhas_char = padrao.split()
            char_w = len(linhas_char[0]) if linhas_char else 0
            char_h = len(linhas_char)
            for cy, linha_char in enumerate(linhas_char):
                for cx, bit in enumerate(linha_char):
                    if bit == "1":
                        for sx_ in range(tamanho):
                            for sy_ in range(tamanho):
                                _set_pixel(
                                    pixels, largura, altura,
                                    x + dx + cx * tamanho + sx_,
                                    y + cy * tamanho + sy_,
                                    cor,
                                )
            dx += (char_w + 1) * tamanho
        elif char == " ":
            dx += 4 * tamanho


def _desenhar_zona(
    pixels, largura, altura,
    y1, y2, x1, x2, cor, rotulo="",
):

    alpha = 4
    for y in range(max(0, y1), min(altura, y2 + 1)):
        for x in range(max(0, x1), min(largura, x2 + 1)):
            if (y - y1) < alpha or (y2 - y) < alpha or (x - x1) < alpha or (x2 - x) < alpha:
                _set_pixel(pixels, largura, altura, x, y, cor)
            elif (y - y1) < alpha + 3 or (y2 - y) < alpha + 3 or (x - x1) < alpha + 3 or (x2 - x) < alpha + 3:
                pixel_atual = pixels[y * largura + x]
                cor_misturada = tuple(
                    min(255, max(0, int(p * 0.5 + c * 0.5)))
                    for p, c in zip(pixel_atual, cor)
                )
                _set_pixel(pixels, largura, altura, x, y, cor_misturada)

    if rotulo:
        cor_label = tuple(min(255, c + 40) for c in cor)
        _texto(pixels, largura, altura, x1 + 4, y1 + 4, rotulo, cor_label, tamanho=5)


def _desenhar_poi(
    pixels, largura, altura,
    y, x_esq, x_dir, cor, rotulo="",
    estilo="tracejado",
):

    if estilo == "tracejado":
        passo = 6
        for x in range(x_esq, x_dir):
            if (x // passo) % 2 == 0:
                _set_pixel(pixels, largura, altura, x, y, cor)
    else:
        _linha(pixels, largura, altura, x_esq, y, x_dir, y, cor)

    _set_pixel(pixels, largura, altura, x_esq, y, cor)
    _set_pixel(pixels, largura, altura, x_esq - 1, y, cor)
    _set_pixel(pixels, largura, altura, x_esq - 2, y, cor)
    _set_pixel(pixels, largura, altura, x_dir, y, cor)
    _set_pixel(pixels, largura, altura, x_dir + 1, y, cor)
    _set_pixel(pixels, largura, altura, x_dir + 2, y, cor)

    if rotulo:
        _texto(pixels, largura, altura, x_dir + 6, y - 10, rotulo, cor, tamanho=4)


def _desenhar_seta(
    pixels, largura, altura,
    x, y, direcao, cor,
):

    if direcao == "CIMA":
        for i in range(8):
            _set_pixel(pixels, largura, altura, x - i, y + i, cor)
            _set_pixel(pixels, largura, altura, x + i, y + i, cor)
        _linha(pixels, largura, altura, x - 7, y + 7, x + 7, y + 7, cor)
    elif direcao == "BAIXO":
        for i in range(8):
            _set_pixel(pixels, largura, altura, x - i, y - i, cor)
            _set_pixel(pixels, largura, altura, x + i, y - i, cor)
        _linha(pixels, largura, altura, x - 7, y - 7, x + 7, y - 7, cor)


def _info_topo(pixels, largura, altura, textos, cor_texto):

    x_atual = 10
    for texto_str in textos:
        _texto(pixels, largura, altura, x_atual, 6, texto_str, cor_texto, tamanho=5)
        x_atual += len(texto_str) * 7 * 5 + 20


def gerar_print_entrada(
    ativo,
    direcao,
    entrada,
    stop,
    take_profit,
    pre_operation_id=None,
    zonas=None,
    pois=None,
    estrutura=None,
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
    texto_cor = (230, 235, 242)
    alta = (99, 197, 139)
    baixa = (228, 91, 91)
    entrada_cor = (212, 175, 55)
    stop_cor = (228, 91, 91)
    tp_cor = (99, 197, 139)
    zona_bull = (45, 120, 80)
    zona_bear = (120, 45, 45)
    poi_cor = (160, 160, 200)
    arrow_up = (99, 197, 139)
    arrow_down = (228, 91, 91)

    pixels = [fundo] * (largura * altura)

    precos = []
    for candle in candles:
        precos.extend([candle["high"], candle["low"]])
    precos.extend([float(entrada), float(stop), float(take_profit)])

    if zonas:
        for z in zonas:
            if z.get("high"):
                precos.append(float(z["high"]))
            if z.get("low"):
                precos.append(float(z["low"]))

    if pois:
        for p in pois:
            precos.append(float(p["price"]))

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

    if zonas:
        x_esq_zona = margem_esq
        x_dir_zona = largura - margem_dir
        for z in zonas:
            z_tipo = str(z.get("tipo", "")).upper()
            z_high = float(z["high"])
            z_low = float(z["low"])
            y_z_high = y_preco(z_high)
            y_z_low = y_preco(z_low)
            z_cor = zona_bull if "BULL" in z_tipo else zona_bear if "BEAR" in z_tipo else (80, 80, 100)
            z_rotulo = z.get("rotulo", z_tipo[:8])
            _desenhar_zona(
                pixels, largura, altura,
                min(y_z_high, y_z_low), max(y_z_high, y_z_low),
                x_esq_zona, x_dir_zona,
                z_cor, rotulo=z_rotulo,
            )

    if pois:
        for p in pois:
            y_poi = y_preco(float(p["price"]))
            p_cor = p.get("cor", poi_cor)
            if isinstance(p_cor, str):
                p_cor = poi_cor
            _desenhar_poi(
                pixels, largura, altura,
                y_poi, margem_esq, largura - margem_dir,
                p_cor, rotulo=p.get("rotulo", ""),
                estilo=p.get("estilo", "tracejado"),
            )

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

    if estrutura:
        for evt in estrutura:
            if "index" in evt and "price" in evt:
                x_evt = x_indice(int(evt["index"]))
                y_evt = y_preco(float(evt["price"]))
                if "BOS" in str(evt.get("tipo", "")).upper():
                    _desenhar_seta(
                        pixels, largura, altura,
                        x_evt, y_evt,
                        "BAIXO" if "BEAR" in str(evt.get("tipo", "")).upper() else "CIMA",
                        arrow_down if "BEAR" in str(evt.get("tipo", "")).upper() else arrow_up,
                    )
                elif "CHOCH" in str(evt.get("tipo", "")).upper():
                    _desenhar_seta(
                        pixels, largura, altura,
                        x_evt, y_evt,
                        "CIMA" if "BULL" in str(evt.get("tipo", "")).upper() else "BAIXO",
                        arrow_up if "BULL" in str(evt.get("tipo", "")).upper() else arrow_down,
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

    info_textos = [f"LEON | {ativo} | {direcao} | {len(candles)} candles"]
    if zonas:
        info_textos.append(f"Zonas: {len(zonas)}")
    _info_topo(pixels, largura, altura, info_textos, texto_cor)

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
    if zonas:
        legenda += f" | {len(zonas)} zona(s)"

    return {
        "ok": True,
        "path": str(caminho),
        "caption": legenda,
        "candles": len(candles),
        "rr": rr,
        "zonas": len(zonas) if zonas else 0,
    }


def gerar_print_analise(
    ativo,
    direcao="NEUTRO",
    score=0,
    smc_direction="NEUTRO",
    zonas=None,
    pois=None,
    estrutura=None,
    elliott_info=None,
):

    candles = _ler_candles(ativo)

    if len(candles) < 3:
        return {
            "ok": False,
            "error": "INSUFFICIENT_CANDLES",
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
    texto_cor = (230, 235, 242)
    alta = (99, 197, 139)
    baixa = (228, 91, 91)
    zona_bull = (45, 120, 80)
    zona_bear = (120, 45, 45)
    poi_cor = (160, 160, 200)
    arrow_up = (99, 197, 139)
    arrow_down = (228, 91, 91)

    pixels = [fundo] * (largura * altura)

    precos = []
    for candle in candles:
        precos.extend([candle["high"], candle["low"]])

    if zonas:
        for z in zonas:
            if z.get("high"):
                precos.append(float(z["high"]))
            if z.get("low"):
                precos.append(float(z["low"]))

    if pois:
        for p in pois:
            precos.append(float(p["price"]))

    minimo = min(precos) if precos else 4100
    maximo = max(precos) if precos else 4200
    folga = max((maximo - minimo) * 0.08, 1.0)
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

    if zonas:
        x_esq_zona = margem_esq
        x_dir_zona = largura - margem_dir
        for z in zonas:
            z_tipo = str(z.get("tipo", "")).upper()
            z_high = float(z["high"])
            z_low = float(z["low"])
            y_z_high = y_preco(z_high)
            y_z_low = y_preco(z_low)
            z_cor = zona_bull if "BULL" in z_tipo else zona_bear if "BEAR" in z_tipo else (80, 80, 100)
            z_rotulo = z.get("rotulo", z_tipo[:8])
            _desenhar_zona(
                pixels, largura, altura,
                min(y_z_high, y_z_low), max(y_z_high, y_z_low),
                x_esq_zona, x_dir_zona,
                z_cor, rotulo=z_rotulo,
            )

    if pois:
        for p in pois:
            y_poi = y_preco(float(p["price"]))
            p_cor = p.get("cor", poi_cor)
            if isinstance(p_cor, str):
                p_cor = poi_cor
            _desenhar_poi(
                pixels, largura, altura,
                y_poi, margem_esq, largura - margem_dir,
                p_cor, rotulo=p.get("rotulo", ""),
                estilo=p.get("estilo", "tracejado"),
            )

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

    if estrutura:
        for evt in estrutura:
            if "index" in evt and "price" in evt:
                x_evt = x_indice(int(evt["index"]))
                y_evt = y_preco(float(evt["price"]))
                if "BOS" in str(evt.get("tipo", "")).upper():
                    _desenhar_seta(
                        pixels, largura, altura,
                        x_evt, y_evt,
                        "BAIXO" if "BEAR" in str(evt.get("tipo", "")).upper() else "CIMA",
                        arrow_down if "BEAR" in str(evt.get("tipo", "")).upper() else arrow_up,
                    )
                elif "CHOCH" in str(evt.get("tipo", "")).upper():
                    _desenhar_seta(
                        pixels, largura, altura,
                        x_evt, y_evt,
                        "CIMA" if "BULL" in str(evt.get("tipo", "")).upper() else "BAIXO",
                        arrow_up if "BULL" in str(evt.get("tipo", "")).upper() else arrow_down,
                    )

    _retangulo(pixels, largura, altura, 0, 0, largura - 1, 48, (17, 23, 32))
    _retangulo(pixels, largura, altura, 0, altura - 44, largura - 1, altura - 1, (17, 23, 32))

    info_textos = [f"LEON ANALISE | {ativo} | SMC:{smc_direction} | Score:{score}"]
    if zonas:
        info_textos.append(f"Zonas:{len(zonas)}")
    if elliott_info:
        info_textos.append(f"Elliott:{elliott_info}")
    _info_topo(pixels, largura, altura, info_textos, texto_cor)

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    nome = (
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_ANALISE_"
        f"{ativo}_{smc_direction}.png"
    )
    caminho = SNAPSHOT_DIR / nome
    _salvar_png(caminho, pixels, largura, altura)

    legenda = (
        f"LEON | {ativo} | SMC:{smc_direction} | Score:{score}"
    )
    if zonas:
        legenda += f" | {len(zonas)} zona(s)"

    return {
        "ok": True,
        "path": str(caminho),
        "caption": legenda,
        "candles": len(candles),
        "zonas": len(zonas) if zonas else 0,
    }
