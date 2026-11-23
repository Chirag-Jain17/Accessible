def sanitize_identifier(name):
    """
    Sanitizes SQL identifiers (table names, column names) to prevent SQL injection
    and avoid keyword conflicts.
    """
    if not name:
        return None
    sanitized = "".join(c if c.isalnum() or c == '_' else '_' for c in name.replace(' ', '_'))
    if not sanitized or not (sanitized[0].isalpha() or sanitized[0] == '_'):
        sanitized = f"tbl_{sanitized}"
    if sanitized.upper() in [
        'TABLE', 'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WHERE',
        'FROM', 'CREATE', 'ALTER', 'DROP', 'INDEX', 'KEY', 'PRIMARY', 'FOREIGN'
    ]:
        sanitized = f"tbl_{sanitized}"
    return sanitized
