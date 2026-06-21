from .analysis_routes import analysis_bp
from .auth_routes import auth_bp
from .dashboard_routes import dashboard_bp
from .health_routes import health_bp
from .leon_routes import leon_bp
from .user_routes import users_bp
from .weekly_audit_routes import weekly_audit_bp


__all__ = [
    "analysis_bp",
    "auth_bp",
    "dashboard_bp",
    "health_bp",
    "leon_bp",
    "users_bp",
    "weekly_audit_bp",
]
