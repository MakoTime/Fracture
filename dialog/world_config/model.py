from dataclasses import dataclass

from objects.world_config import WorldConfig


@dataclass
class WorldConfigModel:
    """Editable view of the singleton world configuration."""

    world_config: WorldConfig
    name: str
    centre: tuple[float, float, float]

    @classmethod
    def from_object(cls, world_config):
        return cls(
            world_config=world_config,
            name=world_config.name,
            centre=world_config.centre,
        )

    def apply(self):
        self.world_config.update_configuration(
            name=self.name,
            centre=self.centre,
        )
        return self.world_config