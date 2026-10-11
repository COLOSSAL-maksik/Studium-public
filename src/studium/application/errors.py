class ApplicationError(Exception):
    """Stable message key translated at the presentation boundary."""


class FrozenTaxonomyDependencyError(ApplicationError):
    """Concrete saved dependencies, rendered by the presentation boundary."""

    def __init__(self, dependencies):
        super().__init__("frozen_taxonomy_dependency")
        self.dependencies = tuple(dependencies)
