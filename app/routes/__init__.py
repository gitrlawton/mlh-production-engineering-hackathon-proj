def register_routes(app):
    """Register all route blueprints with the Flask app.

    Add your blueprints here. Example:
        from app.routes.products import products_bp
        app.register_blueprint(products_bp)
    """
    import os
    from app.routes.urls import urls_bp
    from app.routes.metrics import metrics_bp
    from app.routes.logs import logs_bp
    from app.routes.alerts import alerts_bp
    app.register_blueprint(urls_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(alerts_bp)

    if os.environ.get("FLASK_DEBUG", "").lower() == "true":
        from app.routes.debug import debug_bp
        app.register_blueprint(debug_bp)
