def register_human_analysis(analysis=None):
    return {
        "ok": True,
        "status": "REGISTERED_FOR_SUPERVISED_STUDY",
        "analysis": analysis or {},
    }
