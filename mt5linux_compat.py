import threading

from mt5linux import MetaTrader5 as _ClientBase

_CLIENT = None
_HOST = "localhost"
_PORT = 18812
_TIMEOUT = 6
_TERMINAL_PATH = r"C:\Program Files\FTMO Global Markets MT5 Terminal\terminal64.exe"

# A conexao RPyC subjacente NAO e thread-safe para chamadas concorrentes:
# waitress roda 4 threads que compartilhavam o mesmo _CLIENT sem sincronizacao.
# Sob gateway MT5 lento/travado, multiplas threads ficavam presas juntas em
# `sync_request` (py-spy dump de 25/08). O lock serializa o acesso ao cliente
# RPyC, garantindo que apenas uma chamada MT5 por vez trafega na conexao —
# combinado com _TIMEOUT, uma chamada presa nunca trava mais que _TIMEOUT
# segundos, e as demais threads aguardam a liberacao do lock (nao do socket).
_CLIENT_LOCK = threading.Lock()


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _ClientBase(host=_HOST, port=_PORT, timeout=_TIMEOUT)
    return _CLIENT


def _reset_client():
    global _CLIENT
    _CLIENT = None


def _call_locked(method_name, *args, **kwargs):
    """Executa uma chamada no cliente RPyC sob lock, com reset em falha.

    Serializa o acesso porque a conexao RPyC subjacente nao suporta
    requisicoes concorrentes de multiplas threads com seguranca. Qualquer
    exececao (incluindo timeout de sync_request) reseta o cliente para
    forcar reconexao limpa na proxima chamada, evitando ficar com um
    socket em estado inconsistente.
    """
    with _CLIENT_LOCK:
        try:
            client = _get_client()
            method = getattr(client, method_name)
            return method(*args, **kwargs)
        except Exception:
            _reset_client()
            raise


def _with_terminal_path(args, kwargs):
    if args:
        return args, kwargs
    updated = dict(kwargs)
    updated.setdefault("portable", True)
    updated.setdefault("timeout", 6000)
    return (_TERMINAL_PATH,), updated


def initialize(*args, **kwargs):
    try:
        args, kwargs = _with_terminal_path(args, kwargs)
        return _call_locked("initialize", *args, **kwargs)
    except Exception:
        return False


def shutdown(*args, **kwargs):
    try:
        return _call_locked("shutdown", *args, **kwargs)
    except Exception:
        return None


def login(*args, **kwargs):
    return _call_locked("login", *args, **kwargs)


def symbol_select(*args, **kwargs):
    return _call_locked("symbol_select", *args, **kwargs)


def symbol_info(*args, **kwargs):
    return _call_locked("symbol_info", *args, **kwargs)


def symbol_info_tick(*args, **kwargs):
    return _call_locked("symbol_info_tick", *args, **kwargs)


def copy_rates_from_pos(*args, **kwargs):
    return _call_locked("copy_rates_from_pos", *args, **kwargs)


def copy_rates_range(*args, **kwargs):
    return _call_locked("copy_rates_range", *args, **kwargs)


def copy_rates_from(*args, **kwargs):
    return _call_locked("copy_rates_from", *args, **kwargs)


def copy_ticks_from(*args, **kwargs):
    return _call_locked("copy_ticks_from", *args, **kwargs)


def copy_ticks_range(*args, **kwargs):
    return _call_locked("copy_ticks_range", *args, **kwargs)


def order_send(*args, **kwargs):
    return _call_locked("order_send", *args, **kwargs)


def order_check(*args, **kwargs):
    return _call_locked("order_check", *args, **kwargs)


def positions_get(*args, **kwargs):
    return _call_locked("positions_get", *args, **kwargs)


def positions_total(*args, **kwargs):
    return _call_locked("positions_total", *args, **kwargs)


def orders_get(*args, **kwargs):
    return _call_locked("orders_get", *args, **kwargs)


def orders_total(*args, **kwargs):
    return _call_locked("orders_total", *args, **kwargs)


def history_deals_get(*args, **kwargs):
    return _call_locked("history_deals_get", *args, **kwargs)


def history_deals_total(*args, **kwargs):
    return _call_locked("history_deals_total", *args, **kwargs)


def history_orders_get(*args, **kwargs):
    return _call_locked("history_orders_get", *args, **kwargs)


def history_orders_total(*args, **kwargs):
    return _call_locked("history_orders_total", *args, **kwargs)


def account_info(*args, **kwargs):
    return _call_locked("account_info", *args, **kwargs)


def terminal_info(*args, **kwargs):
    return _call_locked("terminal_info", *args, **kwargs)


def last_error(*args, **kwargs):
    return _call_locked("last_error", *args, **kwargs)


def version(*args, **kwargs):
    return _call_locked("version", *args, **kwargs)


def symbols_get(*args, **kwargs):
    return _call_locked("symbols_get", *args, **kwargs)


def symbols_total(*args, **kwargs):
    return _call_locked("symbols_total", *args, **kwargs)


def order_calc_margin(*args, **kwargs):
    return _call_locked("order_calc_margin", *args, **kwargs)


def order_calc_profit(*args, **kwargs):
    return _call_locked("order_calc_profit", *args, **kwargs)


def market_book_add(*args, **kwargs):
    return _call_locked("market_book_add", *args, **kwargs)


def market_book_get(*args, **kwargs):
    return _call_locked("market_book_get", *args, **kwargs)


def market_book_release(*args, **kwargs):
    return _call_locked("market_book_release", *args, **kwargs)


def eval(*args, **kwargs):
    return _call_locked("eval", *args, **kwargs)


def execute(*args, **kwargs):
    return _call_locked("execute", *args, **kwargs)


def __getattr__(name):
    return getattr(_ClientBase, name)
