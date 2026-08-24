__all__ = ["ProjectController"]


def __getattr__(name):
    if name == "ProjectController":
        from .project_controller import ProjectController

        return ProjectController
    raise AttributeError(name)
