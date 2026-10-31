import os
import datetime
from flask import Flask, render_template, session, request
from config import Config
from database import SessionLocal, User, Taxpayer, Association, AssociationAgent
from routes.public import public_bp
from routes.taxpayer import taxpayer_bp
from routes.association import association_bp
from routes.agent import agent_bp
from routes.admin import admin_bp
from routes.api import api_bp
from icons import render_icon

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register global Jinja functions
    app.jinja_env.globals['icon'] = render_icon

    # Register blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(taxpayer_bp)
    app.register_blueprint(association_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # Template filters
    @app.template_filter('currency')
    def currency_filter(val):
        if val is None:
            return "TZS 0"
        try:
            return f"TZS {float(val):,.0f}"
        except (ValueError, TypeError):
            return f"TZS {val}"

    @app.template_filter('date')
    def date_filter(val):
        if not val:
            return "-"
        if isinstance(val, (datetime.datetime, datetime.date)):
            return val.strftime("%d %b %Y")
        return str(val)

    @app.template_filter('datetime')
    def datetime_filter(val):
        if not val:
            return "-"
        if isinstance(val, (datetime.datetime, datetime.date)):
            return val.strftime("%d %b %Y, %H:%M")
        return str(val)

    # Context processors
    @app.context_processor
    def inject_globals():
        user_info = None
        user_id = session.get('user_id')
        if user_id:
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    user_info = {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "phone": user.phone_number,
                        "role": user.role.name if user.role else "taxpayer",
                        "full_name": user.full_name or user.username
                    }
                    if user.role and user.role.name == "taxpayer":
                        tp = db.query(Taxpayer).filter(Taxpayer.user_id == user.id).first()
                        if tp:
                            user_info["tin"] = tp.tin
                            user_info["taxpayer_id"] = tp.id
                            user_info["business_name"] = tp.businesses[0].name if tp.businesses else ""
                    elif user.role and user.role.name == "association_admin":
                        assoc = db.query(Association).filter((Association.email == user.email) | (Association.phone_number == user.phone_number)).first() or db.query(Association).first()
                        if assoc:
                            user_info["association_name"] = assoc.name
                            user_info["association_code"] = assoc.registration_number
                    elif user.role and user.role.name == "association_agent":
                        ag = db.query(AssociationAgent).filter(AssociationAgent.user_id == user.id).first()
                        if ag:
                            user_info["agent_code"] = ag.agent_code
            finally:
                db.close()

        return {
            "current_user": user_info,
            "now": datetime.datetime.utcnow(),
            "year": datetime.datetime.utcnow().year,
            "platform_name": "TaxRahisi",
            "tagline": "Every trader counted. Every shilling fairly collected."
        }

    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('public/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('public/403.html'), 403

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('public/500.html'), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
