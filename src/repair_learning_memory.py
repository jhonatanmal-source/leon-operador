import csv
import shutil
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
BACKUP_DIR = ROOT_DIR / "backups" / "learning_audit_20260618"
PRE_OPERATION_FILE = DATA_DIR / "pre_operation_trades.csv"
ORDER_MEMORY_FILE = DATA_DIR / "mt5_order_memory.csv"
PERFORMANCE_FILE = DATA_DIR / "performance.csv"
BRAIN_MEMORY_FILE = DATA_DIR / "brain_memory.csv"


def _read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter=";"))


def rebuild_real_learning_memory():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    for source in [PERFORMANCE_FILE, BRAIN_MEMORY_FILE]:
        if source.exists():
            shutil.copy2(source, BACKUP_DIR / source.name)

    executed_ids = {
        row.get("pre_operation_id")
        for row in _read_csv(ORDER_MEMORY_FILE)
        if row.get("status") == "ENVIADA"
    }

    real_results = []
    for row in _read_csv(PRE_OPERATION_FILE):
        if row.get("id") not in executed_ids:
            continue
        result = row.get("resultado") or ""
        if result != "LOSS" and not result.startswith("WIN"):
            continue
        real_results.append({
            "id": row.get("id"),
            "brain_score": row.get("brain_score") or "0",
            "confianca": row.get("confianca") or "SEM_DADOS",
            "resultado": "ACERTO" if result.startswith("WIN") else "ERRO",
        })

    with PERFORMANCE_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["resultado"])
        for item in real_results:
            writer.writerow([item["resultado"]])

    with BRAIN_MEMORY_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["brain_score", "confianca", "resultado"],
            delimiter=";",
        )
        writer.writeheader()
        for item in real_results:
            writer.writerow({
                "brain_score": item["brain_score"],
                "confianca": item["confianca"],
                "resultado": item["resultado"],
            })

    return {
        "rebuilt_at": datetime.now().isoformat(timespec="seconds"),
        "real_results": len(real_results),
        "wins": sum(
            1 for item in real_results if item["resultado"] == "ACERTO"
        ),
        "losses": sum(
            1 for item in real_results if item["resultado"] == "ERRO"
        ),
        "backup_dir": str(BACKUP_DIR),
    }


if __name__ == "__main__":
    print(rebuild_real_learning_memory())
