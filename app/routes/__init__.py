def register_routes(app):
    """Register all route blueprints with the Flask app.

    Add your blueprints here. Example:
        from app.routes.products import products_bp
        app.register_blueprint(products_bp)
    """
    from app.routes.urls import urls_bp
    from app.routes.metrics import metrics_bp
    from app.routes.logs import logs_bp
    from app.routes.alerts import alerts_bp
    app.register_blueprint(urls_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(alerts_bp)
