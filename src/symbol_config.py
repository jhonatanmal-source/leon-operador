import configparser
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "config.ini"


def obter_simbolo_padrao():

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding="utf-8")

    if config.has_section("OPERATOR"):
        simbolo = config["OPERATOR"].get("market_symbol", "").strip()
        if simbolo:
            return simbolo

    if config.has_section("LEON"):
        simbolo = config["LEON"].get("market", "").strip()
        if simbolo:
            return simbolo

    return "XAUUSD"
