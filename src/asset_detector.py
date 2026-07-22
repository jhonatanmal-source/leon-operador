import json
from pathlib import Path

CANDIDATOS = ["Gold_Spot", "XAUUSD", "XAUUSD.fx", "GOLD", "XAU/USD"]
CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "active_symbol_cache.json"


def detectar_ativo():
    cache = _ler_cache()
    if cache:
        return cache

    try:
        import mt5linux_compat as mt5
    except ImportError:
        _salvar_cache("XAUUSD")
        return "XAUUSD"

    if not mt5.initialize():
        _salvar_cache("XAUUSD")
        return "XAUUSD"

    try:
        total = mt5.symbols_total()
        if total and total > 0:
            simbolos = mt5.symbols_get()
            if simbolos:
                nomes = {s.name for s in simbolos}
                for cand in CANDIDATOS:
                    if cand in nomes:
                        select_ok = mt5.symbol_select(cand, True)
                        if select_ok:
                            info = mt5.symbol_info(cand)
                            if info and info.bid and info.bid > 0:
                                _salvar_cache(cand)
                                mt5.shutdown()
                                return cand
    except Exception:
        pass

    mt5.shutdown()
    _salvar_cache("XAUUSD")
    return "XAUUSD"


def _ler_cache():
    try:
        if CACHE_FILE.exists():
            dados = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            if dados.get("ativo"):
                return dados["ativo"]
    except Exception:
        pass
    return None


def _salvar_cache(ativo):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        CACHE_FILE.write_text(
            json.dumps({"ativo": ativo, "detectado_em": __import__("datetime").datetime.now().isoformat(timespec="seconds")}),
            encoding="utf-8",
        )
    except Exception:
        pass


def invalidar_cache():
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
