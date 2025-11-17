from __future__ import annotations
from flask import Blueprint, jsonify

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.get("/placeholder")
def analytics_placeholder():
    return jsonify({"message": "analytics placeholder"})
