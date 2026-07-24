import os
import re
import csv
from datetime import datetime, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VAULT_DIR = ROOT_DIR / "obsidian_vault"
DATA_DIR = ROOT_DIR / "data"
ARQUIVO_MEMORIA = DATA_DIR / "memory_context_log.csv"
ARQUIVO_APRENDIZADO = DATA_DIR / "memory_learned.csv"

SHADOW_ENV = "LEON_MEMORY_SHADOW_MODE"
SHADOW_ACTIVE = os.environ.get(SHADOW_ENV, "true").lower() == "true"

CAMPOS_MEMORIA = [
    "data", "tipo_evento", "contexto_hash", "tendencia", "direcao",
    "zona", "sessao", "smc", "elliott", "resultado", "licao", "observacao",
]

CAMPOS_APRENDIZADO = [
    "data", "status", "contexto_hash", "padrao", "resultado_historico",
    "vitorias", "derrotas", "licao_aplicada", "confianca",
]

SINONIMOS = {
    "alta": ["compra", "bullish", "buy", "comprar", "alinhado", "positivo", "subindo"],
    "baixa": ["venda", "bearish", "sell", "vender", "negativo", "descendo"],
    "compra": ["alta", "bullish", "buy", "long"],
    "venda": ["baixa", "bearish", "sell", "short"],
    "smc": ["estrutura", "bos", "choch", "liquidez", "fvg", "order", "block", "break", "alinhamento"],
    "elliott": ["onda", "impulso", "correcao", "abc", "fibonacci", "wave", "pivot", "ondas"],
    "xauusd": ["ouro", "gold", "spot", "xau"],
    "confirmada": ["confirmacao", "valido", "setup", "zona", "pronto"],
    "bloqueado": ["bloqueio", "invalido", "negado", "falha", "erro"],
}

SECOES_CHAVE = [
    "erro", "corre", "decis", "padrao", "recomen",
    "aprend", "missao", "diagnos", "causa", "ajuste",
    "result", "licao",
]


def _garantir_arquivo(caminho, campos):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not caminho.exists():
        with caminho.open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=campos, delimiter=";").writeheader()


def _ler_csv(caminho, campos, limite=50):
    if not caminho.exists():
        return []
    with caminho.open("r", encoding="utf-8", errors="replace") as f:
        leitor = csv.DictReader(f, delimiter=";")
        linhas = [linha for linha in leitor if any(linha.values())]
    return linhas[-limite:]


def _escrever_csv(caminho, campos, dados):
    _garantir_arquivo(caminho, campos)
    with caminho.open("a", encoding="utf-8", newline="") as f:
        csv.DictWriter(f, fieldnames=campos, delimiter=";").writerow(dados)


def _gerar_hash_contexto(tendencia, direcao, smc, elliott):
    partes = [
        str(tendencia or "?"), str(direcao or "?"),
        str(smc or "?"), str(elliott or "?"),
    ]
    return "_".join(partes).lower().replace(" ", "_")


def _expandir_tags(tags_base):
    expandidas = set(tags_base)
    for tag in tags_base:
        if tag in SINONIMOS:
            expandidas.update(SINONIMOS[tag])
    return [t for t in expandidas if t]


def _scan_vault_markdowns():
    if not VAULT_DIR.exists():
        return []
    resultados = []
    for root, _, files in os.walk(str(VAULT_DIR)):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            caminho = Path(root) / fname
            try:
                with caminho.open("r", encoding="utf-8", errors="replace") as f:
                    conteudo = f.read()
                if len(conteudo.strip()) < 20:
                    continue
                resultados.append({
                    "arquivo": str(caminho.relative_to(VAULT_DIR)),
                    "conteudo": conteudo,
                    "modificado": os.path.getmtime(str(caminho)),
                })
            except (OSError, UnicodeDecodeError):
                continue
    return resultados


def _extrair_palavras_chave(texto):
    palavras = re.findall(r"[a-zA-Z]{4,}", texto.lower())
    stopwords = {
        "para", "com", "que", "dos", "das", "uma", "mais", "mas",
        "como", "por", "ser", "tem", "sua", "seus", "pode", "sobre",
        "este", "esta", "entre", "apos", "antes", "durante", "atraves",
        "mesmo", "forma", "todas", "todos", "sao", "pois", "alem",
        "isso", "essa", "esse", "seu", "seus", "sua", "suas", "foram",
        "tambem", "ainda", "quando", "depois", "sendo", "foram", "tinha",
        "pelos", "pelas", "qual", "numa", "nela", "nele", "este",
    }
    return [p for p in palavras if p not in stopwords]


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    inter = sa & sb
    uniao = sa | sb
    return len(inter) / len(uniao) if uniao else 0.0


def _tags_contexto(tendencia, direcao, smc, elliott):
    tags = []
    for v in [tendencia, direcao, smc, elliott]:
        if v:
            tags.append(v.lower())
    return tags


def _extrair_secoes(texto):
    secoes = []
    linhas = texto.split("\n")
    secao_atual = None
    conteudo_atual = []
    for linha in linhas:
        if linha.startswith("##") or linha.startswith("###"):
            if secao_atual and conteudo_atual:
                secoes.append({
                    "titulo": secao_atual.lower(),
                    "conteudo": " ".join(conteudo_atual),
                })
            secao_atual = linha.lstrip("#").strip()
            conteudo_atual = []
        else:
            conteudo_atual.append(linha)
    if secao_atual and conteudo_atual:
        secoes.append({
            "titulo": secao_atual.lower(),
            "conteudo": " ".join(conteudo_atual),
        })
    return secoes


def _secao_relevante(titulo):
    # Match without accents - just check if any key char sequence appears
    t = titulo.lower()
    return any(p in t for p in [
        "erro", "corre", "decis", "padrao",
        "recomen", "aprend", "missao", "diagnos",
        "causa", "ajuste", "result", "licao",
    ])


def _calcular_score_vault(tags_exp, palavras, secoes):
    if not tags_exp or not palavras:
        return 0.0

    jaccard = _jaccard(tags_exp, palavras)

    # Bonus for matching sections
    score_secao = 0.0
    for secao in secoes:
        if _secao_relevante(secao["titulo"]):
            pal_secao = _extrair_palavras_chave(secao["conteudo"])
            s = _jaccard(tags_exp, pal_secao)
            if s > 0:
                score_secao += s * 2.0

    # Bonus for partial word matches
    score_match = 0.0
    for tag in tags_exp:
        for palavra in palavras:
            if len(tag) >= 4 and (tag in palavra or palavra in tag):
                score_match += 0.15

    return jaccard + score_secao + score_match


def _buscar_memorias_semelhantes(tendencia, direcao, smc, elliott, limite=5):
    memorias = _ler_csv(ARQUIVO_MEMORIA, CAMPOS_MEMORIA, limite=100)
    tags_base = _tags_contexto(tendencia, direcao, smc, elliott)
    tags_exp = _expandir_tags(tags_base) if tags_base else []
    if not memorias or not tags_exp:
        return []
    pontuadas = []
    for mem in memorias:
        tags_mem = _tags_contexto(
            mem.get("tendencia"), mem.get("direcao"),
            mem.get("smc"), mem.get("elliott"),
        )
        tags_mem_exp = _expandir_tags(tags_mem) if tags_mem else []
        score = _jaccard(tags_exp, tags_mem_exp)
        if score > 0:
            pontuadas.append((score, mem))
    pontuadas.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in pontuadas[:limite]]


def _buscar_vault_semelhante(tendencia, direcao, smc, elliott, limite=3):
    try:
        docs = _scan_vault_markdowns()
    except Exception:
        return []
    if not docs:
        return []
    tags_base = _tags_contexto(tendencia, direcao, smc, elliott)
    tags_exp = _expandir_tags(tags_base) if tags_base else []
    if not tags_exp:
        return []

    pontuados = []
    for doc in docs:
        secoes = _extrair_secoes(doc["conteudo"])
        palavras = _extrair_palavras_chave(doc["conteudo"])
        score = _calcular_score_vault(tags_exp, palavras, secoes)
        if score > 0.01:
            licoes = []
            for secao in secoes:
                if _secao_relevante(secao["titulo"]):
                    # Check if section has keyword overlap with tags
                    pal_secao = _extrair_palavras_chave(secao["conteudo"])
                    secao_score = _jaccard(tags_exp, pal_secao)
                    if secao_score > 0 or score > 0.5:
                        # Extract informative sentences from section
                        linhas = [l.strip() for l in secao["conteudo"].split(".") if l.strip()]
                        for linha in linhas[:2]:
                            palavras_linha = _extrair_palavras_chave(linha)
                            if len(palavras_linha) >= 3:
                                licoes.append(linha[:200])
            pontuados.append((score, doc, licoes))

    pontuados.sort(key=lambda x: x[0], reverse=True)
    return [(s, d, l) for s, d, l in pontuados[:limite]]


def _contar_resultados(memorias):
    v = sum(1 for m in memorias if m.get("resultado", "").upper() in ("VITORIA", "WIN", "LUCRO"))
    d = sum(1 for m in memorias if m.get("resultado", "").upper() in ("DERROTA", "LOSS", "PERDA"))
    return v, d


def consultar_contexto(tendencia=None, direcao=None, smc=None, elliott=None):
    ctx_hash = _gerar_hash_contexto(tendencia, direcao, smc, elliott)
    resultado = {
        "contexto_hash": ctx_hash,
        "encontrados": 0, "memorias_validadas": 0, "em_validacao": 0,
        "ultimo_caso_semelhante": None,
        "padrao_recorrente": None, "erro_recorrente": None,
        "licao_aplicada": None, "licoes_vault": [],
        "confianca_memoria": 0.0, "tempo_consulta_ms": 0,
        "shadow_mode": SHADOW_ACTIVE,
    }
    inicio = datetime.now()
    try:
        memorias = _buscar_memorias_semelhantes(tendencia, direcao, smc, elliott)
        vault_docs = _buscar_vault_semelhante(tendencia, direcao, smc, elliott)

        resultado["encontrados"] = len(memorias)
        resultado["memorias_validadas"] = len([m for m in memorias if m.get("resultado") in ("VITORIA", "DERROTA")])
        resultado["em_validacao"] = len([m for m in memorias if m.get("resultado", "").upper() == "OBSERVATION"])

        if memorias:
            v, d = _contar_resultados(memorias)
            total = v + d
            resultado["ultimo_caso_semelhante"] = memorias[0].get("data", "desconhecido")
            if total > 0:
                taxa = v / total
                resultado["confianca_memoria"] = round(taxa * 100, 1)
                if taxa >= 0.6:
                    resultado["padrao_recorrente"] = memorias[0].get("licao", "Padrao identificado")
                if d > v and total >= 3:
                    resultado["erro_recorrente"] = memorias[0].get("observacao", "Revisar abordagem")
            for m in reversed(memorias):
                if m.get("licao"):
                    resultado["licao_aplicada"] = m["licao"]
                    break

        if vault_docs:
            resultado["vault_insights"] = []
            vault_licoes = []
            for score, doc, licoes in vault_docs:
                resultado["vault_insights"].append({
                    "arquivo": doc["arquivo"],
                    "relevancia": round(score * 100, 1),
                })
                vault_licoes.extend(licoes)
            vault_licoes = [l for l in vault_licoes if l.strip()]
            vault_licoes = list(dict.fromkeys(vault_licoes))
            if vault_licoes:
                resultado["licoes_vault"] = vault_licoes[:3]
                if not resultado["licao_aplicada"]:
                    resultado["licao_aplicada"] = vault_licoes[0][:200]

        resultado["tempo_consulta_ms"] = round((datetime.now() - inicio).total_seconds() * 1000, 1)
    except Exception:
        resultado["tempo_consulta_ms"] = round((datetime.now() - inicio).total_seconds() * 1000, 1)
        resultado["fallback"] = True
    return resultado


def gerar_resumo_operacional(tendencia=None, direcao=None, smc=None, elliott=None):
    ctx = consultar_contexto(tendencia, direcao, smc, elliott)
    linhas = []
    linhas.append("=" * 40)
    linhas.append("CONTEXTO DA MEMORIA")
    linhas.append("=" * 40)
    linhas.append(f"Zona: {direcao or 'N/A'}")
    linhas.append(f"Tendencia: {tendencia or 'N/A'}")
    linhas.append(f"SMC: {smc or 'N/A'}")
    linhas.append(f"Elliott: {elliott or 'N/A'}")
    linhas.append(f"Contextos semelhantes: {ctx['encontrados']}")
    linhas.append(f"Memorias validadas: {ctx['memorias_validadas']}")
    if ctx["confianca_memoria"] > 0:
        linhas.append(f"Confianca: {ctx['confianca_memoria']}%")
    if ctx["padrao_recorrente"]:
        linhas.append(f"Padrao: {ctx['padrao_recorrente']}")
    if ctx["erro_recorrente"]:
        linhas.append(f"Erro: {ctx['erro_recorrente']}")
    if ctx["licao_aplicada"]:
        linhas.append(f"Licao: {ctx['licao_aplicada']}")
    if ctx.get("licoes_vault"):
        for l in ctx["licoes_vault"][:2]:
            linhas.append(f"  - {l[:120]}")
    linhas.append("Apenas informativo. Nao libera operacao.")
    linhas.append("=" * 40)
    return "\n".join(linhas)


def gerar_resumo_professor(tendencia=None, direcao=None, smc=None, elliott=None):
    ctx = consultar_contexto(tendencia, direcao, smc, elliott)
    linhas = [f"Observacao: Top-Down {direcao or 'misto'}."]
    if ctx["encontrados"] > 0:
        v, d = _contar_resultados(_buscar_memorias_semelhantes(tendencia, direcao, smc, elliott))
        linhas.append(f"Experiencia semelhante: {ctx['encontrados']} operacoes.")
        if v + d > 0:
            linhas.append(f"Resultado: {v}v {d}d")
    if ctx["licao_aplicada"]:
        linhas.append(f'Licao: "{ctx["licao_aplicada"]}"')
    if ctx.get("licoes_vault"):
        for l in ctx["licoes_vault"][:2]:
            linhas.append(f"- {l[:150]}")
    linhas.append(f"Confianca: {ctx['confianca_memoria']}%")
    return "\n".join(linhas)


def registrar_evento(tipo_evento, tendencia=None, direcao=None, smc=None, elliott=None,
                     zona=None, sessao=None, resultado=None, licao=None, observacao=""):
    if SHADOW_ACTIVE and tipo_evento not in ("operacao", "aprendizado"):
        return False
    linha = {
        "data": datetime.now().isoformat(timespec="seconds"),
        "tipo_evento": tipo_evento,
        "contexto_hash": _gerar_hash_contexto(tendencia, direcao, smc, elliott),
        "tendencia": tendencia or "", "direcao": direcao or "",
        "zona": zona or "", "sessao": sessao or "",
        "smc": smc or "", "elliott": elliott or "",
        "resultado": resultado or "", "licao": licao or "", "observacao": observacao,
    }
    _escrever_csv(ARQUIVO_MEMORIA, CAMPOS_MEMORIA, linha)
    if tipo_evento == "aprendizado" and licao:
        la = {
            "data": linha["data"], "status": "OBSERVATION",
            "contexto_hash": linha["contexto_hash"],
            "padrao": observacao[:100] if observacao else "Novo padrao",
            "resultado_historico": "", "vitorias": "0", "derrotas": "0",
            "licao_aplicada": licao, "confianca": "0.0",
        }
        _escrever_csv(ARQUIVO_APRENDIZADO, CAMPOS_APRENDIZADO, la)
    return True


def obter_metricas_memoria():
    memorias = _ler_csv(ARQUIVO_MEMORIA, CAMPOS_MEMORIA, limite=1000)
    if not memorias:
        return {"total": 0, "vitorias": 0, "derrotas": 0, "taxa_acerto": 0.0, "ultima_consulta": None, "shadow_mode": SHADOW_ACTIVE}
    v = sum(1 for m in memorias if m.get("resultado", "").upper() in ("VITORIA", "WIN", "LUCRO"))
    d = sum(1 for m in memorias if m.get("resultado", "").upper() in ("DERROTA", "LOSS", "PERDA"))
    total = v + d
    return {
        "total": len(memorias), "vitorias": v, "derrotas": d,
        "taxa_acerto": round(v / total * 100, 1) if total > 0 else 0.0,
        "ultima_consulta": memorias[-1].get("data") if memorias else None,
        "shadow_mode": SHADOW_ACTIVE,
    }
