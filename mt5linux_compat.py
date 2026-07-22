from mt5linux import MetaTrader5 as _ClientBase

_CLIENT = None
_HOST = "localhost"
_PORT = 18812
_TIMEOUT = 10


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = _ClientBase(host=_HOST, port=_PORT, timeout=_TIMEOUT)
    return _CLIENT


def initialize(*args, **kwargs):
    return _get_client().initialize(*args, **kwargs)


def shutdown(*args, **kwargs):
    return _get_client().shutdown(*args, **kwargs)


def login(*args, **kwargs):
    return _get_client().login(*args, **kwargs)


def symbol_select(*args, **kwargs):
    return _get_client().symbol_select(*args, **kwargs)


def symbol_info(*args, **kwargs):
    return _get_client().symbol_info(*args, **kwargs)


def symbol_info_tick(*args, **kwargs):
    return _get_client().symbol_info_tick(*args, **kwargs)


def copy_rates_from_pos(*args, **kwargs):
    return _get_client().copy_rates_from_pos(*args, **kwargs)


def copy_rates_range(*args, **kwargs):
    return _get_client().copy_rates_range(*args, **kwargs)


def copy_rates_from(*args, **kwargs):
    return _get_client().copy_rates_from(*args, **kwargs)


def copy_ticks_from(*args, **kwargs):
    return _get_client().copy_ticks_from(*args, **kwargs)


def copy_ticks_range(*args, **kwargs):
    return _get_client().copy_ticks_range(*args, **kwargs)


def order_send(*args, **kwargs):
    return _get_client().order_send(*args, **kwargs)


def order_check(*args, **kwargs):
    return _get_client().order_check(*args, **kwargs)


def positions_get(*args, **kwargs):
    return _get_client().positions_get(*args, **kwargs)


def positions_total(*args, **kwargs):
    return _get_client().positions_total(*args, **kwargs)


def orders_get(*args, **kwargs):
    return _get_client().orders_get(*args, **kwargs)


def orders_total(*args, **kwargs):
    return _get_client().orders_total(*args, **kwargs)


def history_deals_get(*args, **kwargs):
    return _get_client().history_deals_get(*args, **kwargs)


def history_deals_total(*args, **kwargs):
    return _get_client().history_deals_total(*args, **kwargs)


def history_orders_get(*args, **kwargs):
    return _get_client().history_orders_get(*args, **kwargs)


def history_orders_total(*args, **kwargs):
    return _get_client().history_orders_total(*args, **kwargs)


def account_info(*args, **kwargs):
    return _get_client().account_info(*args, **kwargs)


def terminal_info(*args, **kwargs):
    return _get_client().terminal_info(*args, **kwargs)


def last_error(*args, **kwargs):
    return _get_client().last_error(*args, **kwargs)


def version(*args, **kwargs):
    return _get_client().version(*args, **kwargs)


def symbols_get(*args, **kwargs):
    return _get_client().symbols_get(*args, **kwargs)


def symbols_total(*args, **kwargs):
    return _get_client().symbols_total(*args, **kwargs)


def order_calc_margin(*args, **kwargs):
    return _get_client().order_calc_margin(*args, **kwargs)


def order_calc_profit(*args, **kwargs):
    return _get_client().order_calc_profit(*args, **kwargs)


def market_book_add(*args, **kwargs):
    return _get_client().market_book_add(*args, **kwargs)


def market_book_get(*args, **kwargs):
    return _get_client().market_book_get(*args, **kwargs)


def market_book_release(*args, **kwargs):
    return _get_client().market_book_release(*args, **kwargs)


def eval(*args, **kwargs):
    return _get_client().eval(*args, **kwargs)


def execute(*args, **kwargs):
    return _get_client().execute(*args, **kwargs)


def __getattr__(name):
    return getattr(_ClientBase, name)
