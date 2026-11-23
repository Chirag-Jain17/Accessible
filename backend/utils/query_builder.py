from config import ALLOWED_OPERATORS
from .sanitizer import sanitize_identifier

def build_where_clause(conditions_list):
    """
    Builds a WHERE clause string and parameter list from a list of condition objects.
    Handles AND/OR connectors between conditions.
    """
    where_clause_parts = []
    where_params = []
    if not isinstance(conditions_list, list):
        raise ValueError("WHERE conditions must be a list")

    for index, condition in enumerate(conditions_list):
        column = sanitize_identifier(condition.get('column'))
        operator = str(condition.get('operator', '=')).strip().upper()
        value = condition.get('value')
        # Get connector, default to AND for conditions after the first
        connector = str(condition.get('connector', 'AND')).strip().upper() if index > 0 else None

        if not column:
            raise ValueError(f"Incomplete where condition (missing column): {condition}")
        if operator not in ALLOWED_OPERATORS:
            raise ValueError(f"Invalid where operator: {operator}")
        if connector and connector not in ('AND', 'OR'):
            raise ValueError(f"Invalid connector: {connector}")

        # Add connector (AND/OR) before the condition (if not the first condition)
        if connector:
            where_clause_parts.append(connector)

        # Build the condition part
        safe_col_ref = f"`{column}`" # Table name comes from the main query part (FROM/UPDATE/DELETE)
        if operator in ('IS NULL', 'IS NOT NULL'):
            where_clause_parts.append(f"{safe_col_ref} {operator}")
            if value is not None and value != '':
                print(f"Warning: Value '{value}' provided for operator '{operator}' will be ignored.")
        else:
            where_clause_parts.append(f"{safe_col_ref} {operator} %s")
            where_params.append(value)

    if not where_clause_parts:
        return "", []

    final_where_sql = " ".join(where_clause_parts)
    return final_where_sql, where_params
