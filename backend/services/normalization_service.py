from itertools import chain, combinations
from mysql.connector import Error
from database import get_db_connection
from utils.sanitizer import sanitize_identifier

def get_table_schema_details(table_name):
    """Helper to fetch columns and designated primary key."""
    safe_table_name = sanitize_identifier(table_name)
    if not safe_table_name:
        raise ValueError("Invalid table name provided")

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        if not conn or not conn.is_connected():
            raise ConnectionError("Database connection failed")

        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"DESCRIBE `{safe_table_name}`;")
        cols_raw = cursor.fetchall()
        if not cols_raw:
            raise ValueError(f"Table '{safe_table_name}' not found or has no columns.")

        attributes_info = {}
        all_attributes = set()
        pk_columns = set()
        for col in cols_raw:
            col_name = col.get('Field')
            if not col_name:
                continue
            safe_col_name = sanitize_identifier(col_name)
            all_attributes.add(safe_col_name)
            attributes_info[safe_col_name] = {
                "name": safe_col_name,
                "type": col.get('Type', ''),
                "isPK": col.get('Key') == 'PRI'
            }
            if col.get('Key') == 'PRI':
                pk_columns.add(safe_col_name)

        if not pk_columns:
            print(f"Warning: Table '{safe_table_name}' has no designated Primary Key.")

        return list(all_attributes), list(pk_columns), attributes_info

    except Error as e:
        raise ConnectionError(f"Database error fetching schema for {safe_table_name}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

def calculate_closure(attributes_to_close, fds_dict, all_attributes):
    """Calculates the attribute closure (X+) using basic iterative approach."""
    closure = set(attributes_to_close)
    changed = True
    while changed:
        changed = False
        for determinant_tuple, dependents in fds_dict.items():
            determinant_set = set(determinant_tuple)
            if determinant_set.issubset(closure) and not dependents.issubset(closure):
                new_attributes = dependents - closure
                if new_attributes:
                    closure.update(new_attributes)
                    changed = True
    return closure

def find_candidate_keys(attributes, fds_dict):
    """Basic algorithm to find candidate keys."""
    all_attributes_set = set(attributes)
    candidate_keys = []

    for k in range(1, len(attributes) + 1):
        possible_keys = combinations(attributes, k)
        found_superkey_at_this_level = False

        for key_tuple in possible_keys:
            key_set = set(key_tuple)
            closure = calculate_closure(key_set, fds_dict, all_attributes_set)

            if closure == all_attributes_set:
                found_superkey_at_this_level = True
                is_minimal = True
                for ck in candidate_keys:
                    if set(ck).issubset(key_set):
                        is_minimal = False
                        break
                if is_minimal:
                    candidate_keys = [ck for ck in candidate_keys if not key_set.issubset(set(ck))]
                    candidate_keys.append(key_tuple)

        if found_superkey_at_this_level and candidate_keys:
            pass

    return sorted([tuple(sorted(ck)) for ck in candidate_keys])

def analyze_normalization(table_name, user_fds_raw):
    """
    Performs Normalization Analysis (1NF, 2NF, 3NF, BCNF) on a table
    given user-supplied functional dependencies.
    """
    results = {
        "tableName": table_name,
        "primaryKey": [],
        "candidateKeys": [],
        "analysis": {
            "1NF": {"status": "ASSUMED_COMPLIANT", "message": "Relational databases generally enforce atomicity.", "violations": []},
            "2NF": {"status": "NOT_CHECKED", "message": "Requires PK and FDs.", "violations": []},
            "3NF": {"status": "NOT_CHECKED", "message": "Requires PK and FDs.", "violations": []},
            "BCNF": {"status": "NOT_CHECKED", "message": "Requires Candidate Keys and FDs.", "violations": []}
        },
        "notes": [],
        "error": None
    }

    try:
        # 1. Get Schema Details
        all_attributes_list, pk_columns_list, attributes_info = get_table_schema_details(table_name)
        all_attributes = set(all_attributes_list)
        pk_set = frozenset(pk_columns_list)
        results["primaryKey"] = sorted(pk_columns_list)

        if not pk_set:
            results["error"] = "Designated Primary Key is required for standard normalization analysis."
            return results, 400

        # 2. Process Functional Dependencies
        processed_fds = {}

        non_pk_attributes = all_attributes - pk_set
        if pk_set and non_pk_attributes:
            processed_fds[pk_set] = non_pk_attributes

        for fd in user_fds_raw:
            determinants_raw = fd.get('determinants', [])
            dependents_raw = fd.get('dependents', [])

            if not determinants_raw or not dependents_raw:
                raise ValueError(f"Invalid FD format received: {fd}")

            determinants = frozenset(sanitize_identifier(d) for d in determinants_raw)
            dependents = set(sanitize_identifier(dep) for dep in dependents_raw)

            if not determinants.issubset(all_attributes):
                raise ValueError(f"Determinant column(s) not found in table: {determinants - all_attributes}")
            if not dependents.issubset(all_attributes):
                raise ValueError(f"Dependent column(s) not found in table: {dependents - all_attributes}")
            if not dependents.isdisjoint(determinants):
                raise ValueError(f"FD cannot have same attribute on both sides: {fd}")

            if determinants in processed_fds:
                processed_fds[determinants].update(dependents)
            else:
                processed_fds[determinants] = dependents

        # 3. Find Candidate Keys
        print("Finding candidate keys...")
        candidate_keys_tuples = find_candidate_keys(all_attributes_list, processed_fds)
        candidate_keys_sets = [frozenset(ck) for ck in candidate_keys_tuples]
        results["candidateKeys"] = [sorted(list(ck)) for ck in candidate_keys_sets]
        print(f"Found Candidate Keys: {results['candidateKeys']}")

        if not candidate_keys_sets:
            raise ValueError("Could not determine any Candidate Keys for the table.")

        prime_attributes = set(chain.from_iterable(candidate_keys_sets))
        non_prime_attributes = all_attributes - prime_attributes

        # 4. Perform Normalization Checks
        # --- 1NF ---
        results["analysis"]["1NF"]["message"] = "Assumed compliant (atomic values enforced by RDBMS)."

        # --- 2NF ---
        is_2nf = True
        results["analysis"]["2NF"]["status"] = "COMPLIANT"
        results["analysis"]["2NF"]["message"] = "No partial dependencies found."
        for ck_set in candidate_keys_sets:
            if len(ck_set) > 1:
                for k in range(1, len(ck_set)):
                    subsets = combinations(ck_set, k)
                    for subset_tuple in subsets:
                        subset_set = frozenset(subset_tuple)
                        subset_closure = calculate_closure(subset_set, processed_fds, all_attributes)
                        partially_determined_non_primes = subset_closure.intersection(non_prime_attributes)
                        if partially_determined_non_primes:
                            is_2nf = False
                            violation_str = f"Partial Dependency: {{{', '.join(sorted(subset_set))}}} -> {{{', '.join(sorted(partially_determined_non_primes))}}} (violates dependency on CK {{{', '.join(sorted(ck_set))}}})"
                            if violation_str not in results["analysis"]["2NF"]["violations"]:
                                results["analysis"]["2NF"]["violations"].append(violation_str)

        if not is_2nf:
            results["analysis"]["2NF"]["status"] = "VIOLATION_DETECTED"
            results["analysis"]["2NF"]["message"] = "Partial dependencies found (non-prime attributes depend on only part of a candidate key)."

        # --- 3NF ---
        is_3nf = True
        results["analysis"]["3NF"]["status"] = "COMPLIANT"
        results["analysis"]["3NF"]["message"] = "No transitive dependencies found."
        for determinant_set, dependents_set in processed_fds.items():
            determinant_closure = calculate_closure(determinant_set, processed_fds, all_attributes)
            is_superkey = (determinant_closure == all_attributes)

            if not is_superkey:
                for dependent in dependents_set:
                    if dependent not in determinant_set:
                        is_prime = (dependent in prime_attributes)
                        if not is_prime:
                            is_3nf = False
                            violation_str = f"Transitive Dependency: {{{', '.join(sorted(determinant_set))}}} -> {{{dependent}}} (Determinant is not superkey, Dependent is not prime)"
                            if violation_str not in results["analysis"]["3NF"]["violations"]:
                                results["analysis"]["3NF"]["violations"].append(violation_str)

        if not is_3nf:
            results["analysis"]["3NF"]["status"] = "VIOLATION_DETECTED"
            results["analysis"]["3NF"]["message"] = "Transitive dependencies found (non-prime attributes depend on other non-prime attributes)."

        # --- BCNF ---
        is_bcnf = True
        results["analysis"]["BCNF"]["status"] = "COMPLIANT"
        results["analysis"]["BCNF"]["message"] = "All determinants are superkeys."
        for determinant_set, dependents_set in processed_fds.items():
            if not dependents_set.issubset(determinant_set):
                determinant_closure = calculate_closure(determinant_set, processed_fds, all_attributes)
                is_superkey = (determinant_closure == all_attributes)
                if not is_superkey:
                    is_bcnf = False
                    dependent_part = dependents_set - determinant_set
                    violation_str = f"BCNF Violation: Determinant {{{', '.join(sorted(determinant_set))}}} is not a superkey (determines {{{', '.join(sorted(dependent_part))}}})"
                    if violation_str not in results["analysis"]["BCNF"]["violations"]:
                        results["analysis"]["BCNF"]["violations"].append(violation_str)

        if not is_bcnf:
            results["analysis"]["BCNF"]["status"] = "VIOLATION_DETECTED"
            results["analysis"]["BCNF"]["message"] = "BCNF violation(s) found (determinant of an FD is not a superkey)."

        # Notes
        results["notes"].append("Analysis based on schema, designated PK, and user-provided FDs.")
        if not results["candidateKeys"] or len(results["candidateKeys"]) <= 1:
            results["notes"].append("Full accuracy requires identifying ALL candidate keys. Ensure all relevant FDs were provided.")

        return results, 200

    except (ConnectionError, ValueError, Error) as e:
        print(f"Error during normalization analysis for table '{table_name}': {e}")
        results["error"] = str(e)
        return results, 400
    except Exception as ex:
        print(f"Unexpected Error during normalization analysis: {ex}")
        results["error"] = f"An unexpected server error occurred: {ex}"
        return results, 500
