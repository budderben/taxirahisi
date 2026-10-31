import functools
from flask import session, redirect, url_for, flash, request, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database import SessionLocal, User, Role, AuditLog

def hash_password(password: str) -> str:
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return check_password_hash(hashed_password, plain_password)

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    finally:
        db.close()

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session:
            flash("Tafadhali ingia kwenye akaunti yako ili kuendelea.", "warning")
            return redirect(url_for('public.login', next=request.url))
        return view(**kwargs)
    return wrapped_view

def roles_required(*allowed_roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped_view(**kwargs):
            if 'user_id' not in session:
                flash("Tafadhali ingia kwenye akaunti yako.", "warning")
                return redirect(url_for('public.login', next=request.url))
            
            user_role = session.get('user_role')
            if user_role not in allowed_roles:
                log_audit_event(
                    actor_username=session.get('username', 'anonymous'),
                    action="UNAUTHORIZED_ACCESS_ATTEMPT",
                    entity_type="ROUTE_SECURITY",
                    details=f"Attempted to access {request.path} requiring roles: {allowed_roles}"
                )
                flash("Huna idhini ya kutembelea ukurasa huu (Access Denied).", "danger")
                return redirect(url_for('public.index'))
            
            return view(**kwargs)
        return wrapped_view
    return decorator

def log_audit_event(actor_username: str, action: str, entity_type: str, entity_id: str = None, details: str = None):
    db = SessionLocal()
    try:
        audit = AuditLog(
            actor_username=actor_username or "SYSTEM",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            details=details,
            ip_address=request.remote_addr if request else "127.0.0.1"
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging audit: {e}")
    finally:
        db.close()
