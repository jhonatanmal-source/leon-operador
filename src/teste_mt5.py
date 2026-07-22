import mt5linux_compat as mt5

if not mt5.initialize():

    print(mt5.last_error())

else:

    simbolo = "XAUUSD"

    mt5.symbol_select(simbolo, True)

    tick = mt5.symbol_info_tick(simbolo)

    print("===================================")
    print("LEON PRICE TEST")
    print("===================================")

    print(f"Símbolo: {simbolo}")
    print(f"Bid: {tick.bid}")
    print(f"Ask: {tick.ask}")
    print(f"Spread: {tick.ask - tick.bid}")

    mt5.shutdown()