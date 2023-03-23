from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy import Engine, MetaData


class DBMigration(ABC):
    """Class for handling database migrations between module updates"""
    @abstractmethod
    def apply(self, session: Session, engine: Engine, metadata: MetaData):
        """Main method where migration happens"""
