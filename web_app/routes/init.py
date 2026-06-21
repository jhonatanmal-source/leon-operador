from . import (
    analysis_bp,
    auth_bp,
    dashboard_bp,
    health_bp,
    leon_bp,
    users_bp,
    weekly_audit_bp,
)


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(leon_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(weekly_audit_bp)
