from smc_engine import analisar_smc
from elliott_engine import analisar_elliott

smc = analisar_smc(
    "ALTA",
    "COMPRADOR"
)

elliott = analisar_elliott(
    "ALTA",
    "COMPRADOR"
)

print()
print("RESULTADO")

print(smc)

print(elliott)