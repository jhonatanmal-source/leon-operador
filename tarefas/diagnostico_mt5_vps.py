#!/usr/bin/env python3
"""Health check oficial MT5 VPS ??? LEON XAU ELITE AI
Estados:
  MT5_OK
  MT5_TERMINAL_NAO_ENCONTRADO
  MT5_PROCESSO_NAO_EXECUTANDO
  MT5_INITIALIZE_FALHOU
  MT5_SEM_CONTA
  MT5_SEM_CONEXAO
  MT5_SIMBOLO_INDISPONIVEL
  MT5_SEM_TICK
  MT5_MERCADO_FECHADO
"""
import os, sys, platform, json, subprocess
from datetime import datetime

HOST = "127.0.0.1"
PORT = 18812
TERMINAL_PATH = "/home/leon/.mt5/drive_c/Program Files/MetaTrader 5/terminal64.exe"
XAU_SYMBOLS = ["Gold_Spot", "XAUUSD", "XAUUSD.fx", "GOLD", "XAU/USD"]


def checar_processos():
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
    linhas = r.stdout.split("\n")
    return {
        "terminal64": [l for l in linhas if "terminal64" in l.lower()],
        "wineserver": [l for l in linhas if "wineserver" in l.lower()],
        "rpyc": [l for l in linhas if "rpyc_classic" in l.lower()],
        "xvfb": [l for l in linhas if "Xvfb" in l.lower()],
    }


def checar_terminal_existe():
    return os.path.exists(TERMINAL_PATH)


def testar_mt5():
    from mt5linux import MetaTrader5 as mt5
    resultado = {
        "initialize": False,
        "last_error": None,
        "version": None,
        "terminal_info": None,
        "account_info": None,
        "symbols": None,
        "tick": None,
        "estado": None,
    }

    conn = mt5(host=HOST, port=PORT, timeout=30)
    r_init = conn.initialize()
    resultado["initialize"] = r_init
    resultado["last_error"] = conn.last_error()

    if not r_init:
        resultado["estado"] = "MT5_INITIALIZE_FALHOU"
        conn.shutdown()
        return resultado

    r_ver = conn.version()
    resultado["version"] = r_ver

    ti = conn.terminal_info()
    resultado["terminal_info"] = {
        "name": ti.name if ti else None,
        "connected": ti.connected if ti else None,
        "path": ti.path if ti else None,
    } if ti else None

    if not ti or not ti.connected:
        resultado["estado"] = "MT5_SEM_CONEXAO"
        conn.shutdown()
        return resultado

    ai = conn.account_info()
    resultado["account_info"] = {
        "login": ai.login if ai else None,
        "server": ai.server if ai else None,
        "balance": ai.balance if ai else None,
        "currency": ai.currency if ai else None,
        "trade_allowed": ai.trade_allowed if ai else None,
    } if ai else None

    if not ai:
        resultado["estado"] = "MT5_SEM_CONTA"
        conn.shutdown()
        return resultado

    # Find XAU symbol
    todos = conn.symbols_get()
    if todos:
        nomes = {s.name for s in todos}
        ativo = None
        for cand in XAU_SYMBOLS:
            if cand in nomes:
                ativo = cand
                break
        resultado["symbols"] = {"total": len(todos), "xau_encontrado": ativo}

        if not ativo:
            resultado["estado"] = "MT5_SIMBOLO_INDISPONIVEL"
            conn.shutdown()
            return resultado

        conn.symbol_select(ativo, True)
        tick = conn.symbol_info_tick(ativo)
        if tick:
            resultado["tick"] = {
                "bid": tick.bid,
                "ask": tick.ask,
                "time": tick.time,
                "spread": abs(tick.ask - tick.bid),
            }
        else:
            resultado["estado"] = "MT5_SEM_TICK"
            conn.shutdown()
            return resultado

    resultado["estado"] = "MT5_OK"
    conn.shutdown()
    return resultado


def main():
    print("=" * 72)
    print("  DIAGNOSTICO MT5 VPS ??? LEON XAU ELITE AI")
    print("=" * 72)

    # Ambiente
    procs = checar_processos()
    terminal_existe = checar_terminal_existe()

    print(f"\n  HOSTNAME:       {platform.node()}")
    print(f"  SISTEMA:        {platform.platform()}")
    print(f"  USUARIO:        {os.getenv('USER') or os.getenv('USERNAME')}")
    print(f"  SESSAO:         {os.getenv('DISPLAY', 'N/A')}")
    print(f"  PYTHON:         {sys.executable}")
    print(f"  PYTHON_VER:     {sys.version.split()[0]}")
    print(f"  TERMINAL64.EXE: {'EXISTE' if terminal_existe else 'NAO ENCONTRADO'}")

    print(f"\n  PROCESSOS:")
    print(f"    terminal64:   {len(procs['terminal64'])} {' '.join([p.split()[1] for p in procs['terminal64']]) if procs['terminal64'] else 'INATIVO'}")
    print(f"    wineserver:   {len(procs['wineserver'])}")
    print(f"    rpyc_classic: {len(procs['rpyc'])}")
    print(f"    Xvfb:         {len(procs['xvfb'])}")

    if not procs['terminal64']:
        print(f"\n  >>> PROCESSO TERMINAL64: INATIVO")
        print(f"  >>> ESTADO FINAL: MT5_PROCESSO_NAO_EXECUTANDO")
        print("=" * 72)
        return

    if not procs['rpyc']:
        print(f"\n  >>> SERVICO RPYc: INATIVO (porta {PORT})")
        print(f"  >>> ESTADO FINAL: MT5_INITIALIZE_FALHOU")
        print("=" * 72)
        return

    # Teste real
    print(f"\n  --- TESTE MT5 VIA RPyc (mt5linux) ---")
    try:
        res = testar_mt5()
        print(f"  initialize:     {res['initialize']}")
        print(f"  last_error:     {res['last_error']}")
        print(f"  version:        {res['version']}")

        if res['terminal_info']:
            ti = res['terminal_info']
            print(f"  terminal:       {ti['name']}")
            print(f"  conectado:      {ti['connected']}")
        else:
            print(f"  terminal:       INDISPONIVEL")

        if res['account_info']:
            ai = res['account_info']
            print(f"  conta:          {ai['login']}")
            print(f"  servidor:       {ai['server']}")
            print(f"  saldo:          {ai['balance']} {ai['currency']}")
            print(f"  trade_allowed:  {ai['trade_allowed']}")
            tipo = "REAL" if ai.get('server') and "Real" in str(ai.get('server', '')) else "DEMO"
            print(f"  tipo_conta:     {tipo}")
        else:
            print(f"  conta:          INDISPONIVEL")

        if res['symbols']:
            sym = res['symbols']
            print(f"  symbols_total:  {sym['total']}")
            print(f"  symbol_xau:     {sym['xau_encontrado']}")
        else:
            print(f"  symbols:        INDISPONIVEL")

        if res['tick']:
            tk = res['tick']
            print(f"  tick_bid:       {tk['bid']}")
            print(f"  tick_ask:       {tk['ask']}")
            print(f"  tick_spread:    {tk['spread']}")
            idade_tick = (datetime.now() - datetime.fromtimestamp(tk['time'])).total_seconds() if tk['time'] else -1
            print(f"  tick_idade_seg: {idade_tick:.0f}")
        else:
            print(f"  tick:           INDISPONIVEL")

        print(f"\n  >>> ESTADO FINAL: {res['estado']}")

    except Exception as e:
        print(f"  ERRO: {type(e).__name__}: {e}")
        print(f"  >>> ESTADO FINAL: MT5_INITIALIZE_FALHOU")

    print("=" * 72)
    print("  DIAGNOSTICO CONCLUIDO")


if __name__ == "__main__":
    main()
