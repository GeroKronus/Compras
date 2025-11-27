# API Utilities - DRY Helpers
from app.api.utils.db_helpers import get_by_id, validate_fk, validate_unique, bulk_validate_fks
from app.api.utils.pagination import paginate_query, paginate_response, apply_search_filter, apply_filters
from app.api.utils.sequencers import generate_sequential_number, Prefixes
from app.api.utils.updates import update_entity, bulk_update
from app.api.utils.status import require_status, forbid_status, transition_status

__all__ = [
    # db_helpers
    "get_by_id",
    "validate_fk",
    "validate_unique",
    "bulk_validate_fks",
    # pagination
    "paginate_query",
    "paginate_response",
    "apply_search_filter",
    "apply_filters",
    # sequencers
    "generate_sequential_number",
    "Prefixes",
    # updates
    "update_entity",
    "bulk_update",
    # status
    "require_status",
    "forbid_status",
    "transition_status",
]
