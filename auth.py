from werkzeug.security import generate_password_hash, check_password_hash


def hash_password(password):
    """Hashes the given password."""
    return generate_password_hash(password)


def validate_password(stored_password, provided_password):
    """Validates a provided password against the stored hashed password."""
    return check_password_hash(stored_password, provided_password)