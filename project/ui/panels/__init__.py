"""UI panels package.

Each panel is a separate module that implements the following contract:

    render(user: dict) -> None
    
    Reads from and modifies st.session_state as needed.
    May call external agents, services, or utilities.
    Responsible for all UI rendering for its domain.

Owned by specific team members (see PLAN1.md):
- booking.py: Thevindu
- chat.py: Janidu (not yet split)
- emergency.py: Chanupa (not yet split)
- medicine.py: Nisal (not yet split)
- prescription.py: Nisal (not yet split)
- report.py: Chanupa (not yet split)
- sidebar.py: Janidu (not yet split)
"""

from . import booking

__all__ = ["booking"]
