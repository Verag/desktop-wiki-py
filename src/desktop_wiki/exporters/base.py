from abc import ABC, abstractmethod
from pathlib import Path


class Exporter(ABC):
    """
    Base class for all exporters.
    Defines a common interface that all exporters must implement.
    """

    def __init__(self, db):
        self.db = db

    @abstractmethod
    def export(self, *args, **kwargs) -> Path:
        """
        Execute the export process and return the output path.
        """
        pass