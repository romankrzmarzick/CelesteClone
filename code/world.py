from settings import load_pygame, pygame, Path, vector
import json
from level import Level
from player import Player
from debug import debugger
from transition import Transition
from event_timer import Timer


class World:
    def __init__(self, path, internal_canvas, frames, data_storage) -> None:
        self.data_storage = data_storage
        self.internal_canvas = internal_canvas
        self.level_frames = frames
        self.world_data = json.loads(path.read_text())
        self.create_maps()
        self._current_map = self.map_names[self.data_storage.current_map]

        self.create_current_stage()

        self.transitions = []
        self.spawn_delay = Timer(1000)

    @property
    def current_map_rect(self) -> pygame.FRect:
        """Where the map the player is standing in sits in world space."""
        return self.tmx_map_rects[self.data_storage.current_map]

    @property
    def current_map(self):
        return self.map_names[self.data_storage.current_map]

    def create_current_stage(self):
        self.current_stage = Level(
            self.internal_canvas,
            self.current_map,
            self.level_frames,
            self.data_storage,
            self,
            self.tmx_map_rects[self.data_storage.current_map],
        )

    def create_maps(self):
        self.tmx_map_rects = {}
        self.map_names = {}

        for entry in sorted(
            self.world_data["maps"], key=lambda name: name["fileName"].split(".")[0]
        ):
            file_name_int = int(entry["fileName"].split(".")[0])

            map = pygame.FRect(entry["x"], entry["y"], entry["width"], entry["height"])
            self.tmx_map_rects[file_name_int] = map

            name = entry["fileName"]
            self.map_names[file_name_int] = load_pygame(Path("data", "maps", f"{name}"))

    def respawn(self) -> None:

        self.data_storage.player_position = vector(self.data_storage.spawn_position)
        self.data_storage.player_state = None  # a death should cost you your momentum
        self.data_storage.current_map = self.data_storage.last_check_point

        self.transitions.append(Transition())
        self.spawn_delay.activate()
        print("respawned")
        self.create_current_stage()

    def find_map(self) -> None:
        # the hitbox lives in the *current map's* local space, so lift its centre into
        # world space before comparing with the rects that came out of the .world file
        world_position = vector(self.data_storage.player_rect.center) + vector(
            self.current_map_rect.topleft
        )

        for key, map_rect in self.tmx_map_rects.items():
            if key == self.data_storage.current_map:
                continue

            if map_rect.collidepoint(world_position):
                # hand the outgoing player's velocity to the incoming one
                self.data_storage.player_state = self.current_stage.player.snapshot()

                self.data_storage.current_map = key

                # ...and drop the position back into the new map's local space, or the
                # player spawns out of bounds and immediately transitions again
                self.data_storage.player_position = world_position - vector(
                    map_rect.topleft
                )

                self.create_current_stage()
                return

        # no neighbour over there: the player left the world entirely
        self.respawn()

    def run(self, dt: float):
        self.spawn_delay.update()

        if not self.spawn_delay.active:
            self.current_stage.run(dt)

        if self.transitions:
            for transition in self.transitions:
                transition.update(dt)
                transition.draw(self.internal_canvas)

        self.transitions = [
            transition for transition in self.transitions if transition.is_alive
        ]
