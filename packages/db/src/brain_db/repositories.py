from sqlalchemy.orm import Session


class Repository:
    """Base for repositories participating in a caller-owned unit of work."""

    def __init__(self, session: Session) -> None:
        self.session = session
