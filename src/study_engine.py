# ===================================
# STUDY ENGINE
# ===================================

import json
from datetime import datetime
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
STUDIES_DIR = ROOT_DIR / "studies"
LEARNING_DIR = ROOT_DIR / "data" / "learning"
STUDY_PROGRESS_FILE = LEARNING_DIR / "study_progress.json"
STUDY_NOTES_FILE = LEARNING_DIR / "study_notes.json"
MARKET_OBSERVATIONS_FILE = LEARNING_DIR / "market_observations.json"


def _ensure_learning_files():

    LEARNING_DIR.mkdir(parents=True, exist_ok=True)

    if not STUDY_PROGRESS_FILE.exists():
        save_json(STUDY_PROGRESS_FILE, {})

    if not STUDY_NOTES_FILE.exists():
        save_json(STUDY_NOTES_FILE, [])

    if not MARKET_OBSERVATIONS_FILE.exists():
        save_json(MARKET_OBSERVATIONS_FILE, [])


def load_json(path):

    path = Path(path)

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8-sig") as arquivo:
        return json.load(arquivo)


def save_json(path, data):

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as arquivo:
        json.dump(data, arquivo, ensure_ascii=False, indent=2)

    return data


def load_all_studies():

    studies = []

    if not STUDIES_DIR.exists():
        return studies

    for path in sorted(STUDIES_DIR.rglob("*.json")):
        data = load_json(path)

        if isinstance(data, dict):
            data["_path"] = str(path.relative_to(ROOT_DIR))
            studies.append(data)

    return studies


def get_study_topics():

    return [
        study.get("topic")
        for study in load_all_studies()
        if study.get("topic")
    ]


def get_study_by_topic(topic):

    normalized = str(topic).strip().lower()

    for study in load_all_studies():
        if str(study.get("topic", "")).strip().lower() == normalized:
            return study

    return None


def register_study_note(topic, note):

    _ensure_learning_files()
    notes = load_json(STUDY_NOTES_FILE) or []

    entry = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "note": note,
    }
    notes.append(entry)
    save_json(STUDY_NOTES_FILE, notes)

    return entry


def register_market_observation(topic, observation):

    _ensure_learning_files()
    observations = load_json(MARKET_OBSERVATIONS_FILE) or []

    entry = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "topic": topic,
        "observation": observation,
    }
    observations.append(entry)
    save_json(MARKET_OBSERVATIONS_FILE, observations)

    return entry


def update_study_progress(topic, status):

    _ensure_learning_files()
    progress = load_json(STUDY_PROGRESS_FILE) or {}

    progress[topic] = {
        "status": status,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_json(STUDY_PROGRESS_FILE, progress)

    return progress[topic]


def generate_study_report():

    _ensure_learning_files()
    studies = load_all_studies()
    notes = load_json(STUDY_NOTES_FILE) or []
    observations = load_json(MARKET_OBSERVATIONS_FILE) or []
    progress = load_json(STUDY_PROGRESS_FILE) or {}

    pending_topics = [
        study.get("topic")
        for study in studies
        if study.get("topic") not in progress
    ]

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total_studies": len(studies),
        "topics": get_study_topics(),
        "notes_count": len(notes),
        "observations_count": len(observations),
        "progress_count": len(progress),
        "pending_topics": pending_topics,
        "last_note": notes[-1] if notes else None,
        "last_observation": observations[-1] if observations else None,
    }
