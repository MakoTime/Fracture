from abc import ABC, abstractmethod
from uuid import uuid4

class BlockObject(ABC):
    def __init__(self, name="", guid=None, comments=""):
        self.name = name
        self.guid = guid or str(uuid4())
        self.comments = comments

    @abstractmethod
    def prepare(self):
        """Prepare the block object for use in a project.

        This method is called when the block object is added to a project and
        should be used to perform any necessary initialization or validation.
        """
        pass

    @abstractmethod
    def process(self, progress_callback=None):
        """Process the block object to generate any derived data.

        This method is called after the block object has been prepared and
        should be used to perform any necessary processing or computation.
        """
        pass

    @abstractmethod
    def serialise(self, path):
        """
        Serialise any serialisable objects owned by the block object after the result is processed.
        """
        pass