from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from src.operator_reputation_engine import calculate_reputation
from web_app.database.db import get_connection
from web_app.services.access_log_service import log_action
from web_app.services.auth_service import (
    current_user,
    login_required,
    role_required,
)
from web_app.services.leon_understanding_service import (
    generate_leon_understanding,
)
from web_app.services.upload_service import save_uploaded_file


analysis_bp = Blueprint("analysis", __name__, url_prefix="/analysis")

TIMEFRAMES = {"M5", "M15", "M30", "H1", "H4", "D1"}
DIRECTIONS = {"COMPRA", "VENDA", "NEUTRO"}
ANALYSIS_TYPES = {
    "SMC",
    "ELLIOTT",
    "LIQUIDEZ",
    "BOS",
    "CHOCH",
    "FVG",
    "OB",
    "SETUP_A_PLUS",
    "NOTICIA",
    "OUTRO",
}
REVIEW_STATUSES = {"APROVADA", "REJEITADA", "PARCIAL"}


def _refresh_reputation(user_id):
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        data = connection.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'APROVADA' THEN 1 ELSE 0 END) AS approved,
                SUM(CASE WHEN status = 'REJEITADA' THEN 1 ELSE 0 END) AS rejected,
                AVG(CASE
                    WHEN status IN ('APROVADA', 'REJEITADA', 'PARCIAL')
                    THEN quality_score
                END) AS average_quality
            FROM human_analyses
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

        total = int(data["total"] or 0)
        approved = int(data["approved"] or 0)
        rejected = int(data["rejected"] or 0)
        average_quality = int(round(data["average_quality"] or 0))
        level = calculate_reputation(
            total,
            approved,
            rejected,
            average_quality,
        )
        connection.execute(
            """
            INSERT INTO operator_reputation (
                user_id, total_analyses, approved_analyses,
                rejected_analyses, average_quality,
                confidence_level, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                total_analyses = excluded.total_analyses,
                approved_analyses = excluded.approved_analyses,
                rejected_analyses = excluded.rejected_analyses,
                average_quality = excluded.average_quality,
                confidence_level = excluded.confidence_level,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                total,
                approved,
                rejected,
                average_quality,
                level,
                now,
            ),
        )


def _get_analysis_or_404(analysis_id):
    with get_connection() as connection:
        analysis = connection.execute(
            """
            SELECT human_analyses.*, users.username,
                   reviewer.username AS reviewer_username,
                   leon_understanding.leon_summary,
                   leon_understanding.detected_keywords,
                   leon_understanding.confidence_score
            FROM human_analyses
            JOIN users ON users.id = human_analyses.user_id
            LEFT JOIN users AS reviewer
                ON reviewer.id = human_analyses.reviewed_by
            LEFT JOIN leon_understanding
                ON leon_understanding.analysis_id = human_analyses.id
            WHERE human_analyses.id = ?
            """,
            (analysis_id,),
        ).fetchone()
    if not analysis:
        abort(404)
    return analysis


def _can_view(user, analysis):
    if user["role"] in {"ADMIN", "SUPERVISOR"}:
        return True
    if user["role"] == "COLABORADOR":
        return analysis["user_id"] == user["id"]
    return analysis["status"] == "APROVADA"


@analysis_bp.route("/upload", methods=["GET", "POST"])
@role_required("ADMIN", "SUPERVISOR", "COLABORADOR")
def upload():
    user = current_user()
    if request.method == "POST":
        symbol = request.form.get("symbol", "XAUUSD").strip().upper() or "XAUUSD"
        timeframe = request.form.get("timeframe", "").upper()
        direction = request.form.get("direction", "").upper()
        analysis_type = request.form.get("analysis_type", "").upper()
        text_analysis = request.form.get("text_analysis", "").strip()

        if timeframe not in TIMEFRAMES:
            flash("Timeframe inválido.", "error")
            return redirect(url_for("analysis.upload"))
        if direction not in DIRECTIONS:
            flash("Direção inválida.", "error")
            return redirect(url_for("analysis.upload"))
        if analysis_type not in ANALYSIS_TYPES:
            flash("Tipo de análise inválido.", "error")
            return redirect(url_for("analysis.upload"))
        if len(text_analysis) < 20:
            flash("Descreva a análise com pelo menos 20 caracteres.", "error")
            return redirect(url_for("analysis.upload"))

        try:
            image_path = save_uploaded_file(request.files.get("image"))
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("analysis.upload"))

        now = datetime.now().isoformat(timespec="seconds")
        understanding = generate_leon_understanding(
            text_analysis,
            direction,
            timeframe,
            analysis_type,
        )

        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO human_analyses (
                    user_id, symbol, timeframe, direction, analysis_type,
                    text_analysis, image_path, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDENTE', ?)
                """,
                (
                    user["id"],
                    symbol,
                    timeframe,
                    direction,
                    analysis_type,
                    text_analysis,
                    image_path,
                    now,
                ),
            )
            analysis_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO leon_understanding (
                    analysis_id, leon_summary, detected_keywords,
                    confidence_score, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    analysis_id,
                    understanding["leon_summary"],
                    understanding["detected_keywords"],
                    understanding["confidence_score"],
                    now,
                ),
            )

        _refresh_reputation(user["id"])
        log_action(
            f"ANALISE_ENVIADA:{analysis_id}",
            user["id"],
            user["username"],
        )
        flash("Análise registrada e interpretada pelo LEON.", "success")
        return redirect(url_for("analysis.detail", analysis_id=analysis_id))

    return render_template(
        "upload_analysis.html",
        timeframes=sorted(TIMEFRAMES),
        directions=sorted(DIRECTIONS),
        analysis_types=sorted(ANALYSIS_TYPES),
    )


@analysis_bp.get("/history")
@login_required
def history():
    user = current_user()
    if user["role"] in {"ADMIN", "SUPERVISOR"}:
        where = ""
        params = ()
    elif user["role"] == "COLABORADOR":
        where = "WHERE human_analyses.user_id = ?"
        params = (user["id"],)
    else:
        where = "WHERE human_analyses.status = 'APROVADA'"
        params = ()

    with get_connection() as connection:
        analyses = connection.execute(
            f"""
            SELECT human_analyses.*, users.username
            FROM human_analyses
            JOIN users ON users.id = human_analyses.user_id
            {where}
            ORDER BY human_analyses.id DESC
            """,
            params,
        ).fetchall()
    return render_template("analysis_history.html", analyses=analyses)


@analysis_bp.get("/<int:analysis_id>")
@login_required
def detail(analysis_id):
    user = current_user()
    analysis = _get_analysis_or_404(analysis_id)
    if not _can_view(user, analysis):
        abort(403)
    return render_template("analysis_detail.html", analysis=analysis)


@analysis_bp.post("/<int:analysis_id>/review")
@role_required("ADMIN", "SUPERVISOR")
def review(analysis_id):
    reviewer = current_user()
    analysis = _get_analysis_or_404(analysis_id)
    status = request.form.get("status", "").upper()
    supervisor_comment = request.form.get("supervisor_comment", "").strip()

    try:
        quality_score = int(request.form.get("quality_score", "0"))
    except ValueError:
        quality_score = -1

    if status not in REVIEW_STATUSES:
        flash("Status de revisão inválido.", "error")
        return redirect(url_for("analysis.detail", analysis_id=analysis_id))
    if not 0 <= quality_score <= 100:
        flash("A qualidade deve estar entre 0 e 100.", "error")
        return redirect(url_for("analysis.detail", analysis_id=analysis_id))

    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE human_analyses
            SET status = ?, supervisor_comment = ?, quality_score = ?,
                reviewed_at = ?, reviewed_by = ?
            WHERE id = ?
            """,
            (
                status,
                supervisor_comment,
                quality_score,
                now,
                reviewer["id"],
                analysis_id,
            ),
        )

    _refresh_reputation(analysis["user_id"])
    log_action(
        f"ANALISE_REVISADA:{analysis_id}:{status}:{quality_score}",
        reviewer["id"],
        reviewer["username"],
    )
    flash("Revisão salva com sucesso.", "success")
    return redirect(url_for("analysis.detail", analysis_id=analysis_id))
