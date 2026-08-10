from settings import (
    pygame,
    ProbeType,
    TimerType,
    vector,
    PLAYER_PHYSICS,
    ANIMATION_TRANSITIONS,
    ANIMATION_CORRECTION,
    ANIMATION_INFO,
    TILE_SIZE,
)
from settings import AnimationEntity, PlayerAnimationState
from event_timer import Timer


class Player(pygame.sprite.Sprite):
    def __init__(
        self,
        pos: tuple[float, float],
        groups,
        collision_sprites: pygame.sprite.Group,
        frames: dict[str, list[pygame.Surface]],
        z: int,
    ) -> None:

        super().__init__(groups)
        self.z = z

        self.frames, self.frame_index = frames, 0

        self.state, self.doing_state, self.facing_left = (
            PlayerAnimationState.IDLE,
            PlayerAnimationState.IDLE,
            True,
        )
        self.image = self.frames[self.state.value][self.frame_index]

        self.dir_vector = vector()
        self.move_vector = vector()

        self.is_jumping = False
        self.crouching = False
        self.embrace = False
        self.can_dash = True
        self.climbing = False
        self.climbing_active = False
        self.can_balance = False
        self.is_sliding = False
        self.start_dying = False
        self.dead = False

        self.collision_sprites = collision_sprites

        self.rect: pygame.FRect = self.image.get_frect(center=pos)
        self.hitbox_rect: pygame.FRect = self.rect.inflate((-8, -4))
        self.old_rect: pygame.FRect = self.hitbox_rect.copy()
        self.old_dir = vector()

        self.collide_rects: list[pygame.FRect] = []
        self.on_surface: dict[ProbeType, bool] = {
            ProbeType.FLOOR: False,
            ProbeType.LEFT: False,
            ProbeType.RIGHT: False,
            ProbeType.EDGE: False,
            ProbeType.DANGLE: False,
            ProbeType.EMBRACE_FALL: False,
            ProbeType.MANTLE: False,
        }

        self.timers: dict[TimerType, Timer] = {
            TimerType.DELAY_BALANCE: Timer(500, func=self.balance_animation),
            TimerType.WALL_JUMP_ACTION: Timer(190),
            TimerType.DELAY_WALL_JUMP: Timer(250),
            TimerType.DASH: Timer(290),
            TimerType.MANTLE: Timer(100, func=self.mantle__timer_timeout_fuction),
            TimerType.COYOTE: Timer(180),
            TimerType.DELAY_DASH: Timer(230),
        }

    # what survives a map transition, so momentum carries across the seam
    CARRIED_ATTRIBUTES = (
        "move_vector",
        "dir_vector",
        "old_dir",
        "facing_left",
        "state",
        "doing_state",
        "frame_index",
        "is_jumping",
        "crouching",
        "embrace",
        "can_dash",
        "climbing",
        "climbing_active",
        "is_sliding",
    )

    def snapshot(self) -> dict:
        state = {name: getattr(self, name) for name in self.CARRIED_ATTRIBUTES}

        # vectors are mutable and the outgoing player still owns these
        for name in ("move_vector", "dir_vector", "old_dir"):
            state[name] = vector(state[name])

        # get_ticks() keeps running across the transition, so copying start_time
        # straight over leaves each timer with exactly the time it had left
        state["timers"] = {
            key: (timer.active, timer.start_time) for key, timer in self.timers.items()
        }
        return state

    def restore(self, state: dict) -> None:
        for name in self.CARRIED_ATTRIBUTES:
            setattr(self, name, state[name])

        for key, (active, start_time) in state["timers"].items():
            self.timers[key].active = active
            self.timers[key].start_time = start_time

        # resync the visuals with the animation state we just carried over
        frames = self.frames[self.state.value]
        self.image = frames[int(self.frame_index) % len(frames)]
        if not self.facing_left:
            self.image = pygame.transform.flip(self.image, True, False)
        self.update_rect()

    def input(self) -> None:
        input_dir = vector()
        keys = pygame.key.get_pressed()

        if not any(
            (
                self.timers[TimerType.DASH].active,
                self.timers[TimerType.WALL_JUMP_ACTION].active,
                self.timers[TimerType.MANTLE].active,
            )
        ):
            if keys[pygame.K_RIGHT]:
                input_dir.x = 1
            if keys[pygame.K_LEFT]:
                input_dir.x = -1
            if keys[pygame.K_UP]:
                input_dir.y = -1
            if keys[pygame.K_DOWN]:
                input_dir.y = 1
            self.dir_vector = input_dir

        if keys[pygame.K_UP] and not self.crouching and not self.climbing_active:
            self.is_jumping = True

        if keys[pygame.K_DOWN]:
            self.crouching = True
        else:
            self.crouching = False

        if keys[pygame.K_SPACE]:
            self.climbing = True

        else:
            self.climbing = False

        if keys[pygame.K_x]:
            if not self.timers[TimerType.DELAY_DASH].active and not self.climbing:
                if self.can_dash and not self.timers[TimerType.WALL_JUMP_ACTION].active:
                    if not self.crouching:
                        self.timers[TimerType.DASH].activate()
                        self.old_dir = input_dir

    def move(self, dt: float) -> None:
        self.is_embrace()
        self.balance()

        if not self.timers[TimerType.MANTLE].active:
            self.climb(dt)
            if self.climbing_active:
                self.collisions("x")
                self.collisions("y")
                self.update_rect()

                self.timers[TimerType.DELAY_DASH].activate()
                return

        elif self.timers[TimerType.MANTLE].active:
            self.mantle(dt)
            self.update_rect()
            return

        if (
            self.crouching
            and self.on_surface[ProbeType.FLOOR]
            and self.state == PlayerAnimationState.CROUCH
        ):
            return

        if self.dash(dt):
            self.collisions("x")
            self.collisions("y")
            self.update_rect()
            return

        if self.wall_slide(dt):
            pass
        else:
            self.gravity(dt)

        self.collisions("y")

        if not self.timers[TimerType.DASH].active:
            self.x_move(dt)
        self.collisions("x")

        if self.is_jumping:
            if self.on_surface[ProbeType.FLOOR] or self.timers[TimerType.COYOTE].active:
                self.timers[TimerType.COYOTE].deactivate()
                self.jump()
            if not self.timers[TimerType.DELAY_WALL_JUMP].active and any(
                (self.on_surface[ProbeType.LEFT], self.on_surface[ProbeType.RIGHT])
            ):
                self.wall_jump()
            self.is_jumping = False

        self.update_rect()

    def is_embrace(self) -> None:
        if self.on_surface[ProbeType.EMBRACE_FALL]:
            self.embrace = True
        if self.on_surface[ProbeType.FLOOR]:
            self.embrace = False

    def balance_animation(self) -> None:
        self.can_balance = True

    def balance(self) -> None:
        on_edge = self.on_surface[ProbeType.EDGE]

        if (
            on_edge
            and not self.timers[TimerType.DELAY_BALANCE].active
            and self.on_surface[ProbeType.FLOOR]
        ):
            self.timers[TimerType.DELAY_BALANCE].activate()
        if not on_edge or not self.on_surface[ProbeType.FLOOR]:
            self.timers[TimerType.DELAY_BALANCE].deactivate()
            self.can_balance = False

    def mantle(self, dt: float) -> None:
        self.hitbox_rect.y += -PLAYER_PHYSICS.mantle_y_speed * dt
        self.dir_vector.x = -1 if self.facing_left else 1
        self.hitbox_rect.x += PLAYER_PHYSICS.mantle_x_speed * self.dir_vector.x * dt

    def climb(self, dt: float) -> None:
        if self.on_surface[ProbeType.MANTLE]:
            self.timers[TimerType.MANTLE].activate()

        else:
            if self.climbing:
                if (
                    not self.on_surface[ProbeType.FLOOR]
                    and not self.on_surface[ProbeType.MANTLE]
                    and any(
                        (
                            self.on_surface[ProbeType.LEFT],
                            self.on_surface[ProbeType.RIGHT],
                        )
                    )
                ):
                    self.move_vector.y = 0
                    self.hitbox_rect.y += (
                        PLAYER_PHYSICS.climbing_speed * self.dir_vector.y
                    ) * dt
                    self.climbing_active = True
            else:
                self.climbing_active = False

    def x_move(self, dt: float) -> None:

        if self.dir_vector.x != 0:
            self.move_vector.x += (
                PLAYER_PHYSICS.x_acceleration * self.dir_vector.x / 2 * dt
            )
            if self.move_vector.x > PLAYER_PHYSICS.x_max_speed:
                self.move_vector.x = PLAYER_PHYSICS.x_max_speed
            elif self.move_vector.x < -PLAYER_PHYSICS.x_max_speed:
                self.move_vector.x = -PLAYER_PHYSICS.x_max_speed

            if not self.on_surface[ProbeType.FLOOR]:
                self.move_vector.x = (
                    PLAYER_PHYSICS.x_max_speed * 0.8
                ) * self.dir_vector.x

            self.hitbox_rect.x += self.move_vector.x * dt
            self.move_vector.x += (
                PLAYER_PHYSICS.x_acceleration * self.dir_vector.x / 2 * dt
            )
            if self.move_vector.x > PLAYER_PHYSICS.x_max_speed:
                self.move_vector.x = PLAYER_PHYSICS.x_max_speed
            elif self.move_vector.x < -PLAYER_PHYSICS.x_max_speed:
                self.move_vector.x = -PLAYER_PHYSICS.x_max_speed
        if self.dir_vector.x == 0:
            self.move_vector.x = 0

    def gravity(self, dt: float) -> None:
        self.move_vector.y += PLAYER_PHYSICS.gravity_num / 2 * dt
        self.move_vector.y = min(PLAYER_PHYSICS.max_fall_speed, self.move_vector.y)
        self.hitbox_rect.y += self.move_vector.y * dt
        self.move_vector.y += PLAYER_PHYSICS.gravity_num / 2 * dt
        self.move_vector.y = min(PLAYER_PHYSICS.max_fall_speed, self.move_vector.y)

    def jump(self) -> None:
        self.timers[TimerType.DELAY_WALL_JUMP].activate()
        self.move_vector.y = -PLAYER_PHYSICS.jump_height
        self.hitbox_rect.bottom -= 1

    def wall_jump(self) -> None:
        self.timers[TimerType.WALL_JUMP_ACTION].activate()
        self.move_vector.x = 0
        self.move_vector.y = -PLAYER_PHYSICS.jump_height
        self.dir_vector.x = 1 if self.on_surface[ProbeType.LEFT] else -1

    def wall_slide(self, dt: float) -> bool:

        if (
            not self.on_surface[ProbeType.FLOOR]
            and any((self.on_surface[ProbeType.LEFT], self.on_surface[ProbeType.RIGHT]))
            and self.move_vector.y > 0
            and not self.on_surface[ProbeType.MANTLE]
            and self.move_vector.x != 0
        ):
            self.move_vector.y = 0
            self.hitbox_rect.y += PLAYER_PHYSICS.gravity_num / 8 * dt
            self.is_sliding = True
            return True
        self.is_sliding = False
        return False

    def dash(self, dt: float) -> bool:
        if self.on_surface[ProbeType.FLOOR]:
            self.can_dash = True

        if (
            self.timers[TimerType.DASH].active
            and self.dir_vector != vector(0, 0)
            and self.state != "wall"
            and self.state != "climb"
            and not self.timers[TimerType.MANTLE].active
        ):
            normalized_dir = self.old_dir.normalize() if self.old_dir else self.old_dir
            self.can_dash = False
            self.move_vector = vector(0, 0)
            self.hitbox_rect.center += (PLAYER_PHYSICS.dash_speed * normalized_dir) * dt
            return True
        return False

    def update_rect(self) -> None:
        redraw_num = ANIMATION_CORRECTION[AnimationEntity.PLAYER][self.state]
        if self.facing_left:
            self.rect.center = self.hitbox_rect.center + redraw_num
        else:
            self.rect.center = self.hitbox_rect.center + vector(
                -redraw_num.x, redraw_num.y
            )

    def collisions(self, direction: str) -> None:
        hitbox = self.hitbox_rect

        for sprite in self.collision_sprites:
            if hitbox.colliderect(sprite.rect):
                if direction == "x":

                    if (
                        hitbox.right >= sprite.rect.left
                        and self.old_rect.right <= sprite.old_rect.left + 1
                    ):
                        hitbox.right = sprite.rect.left
                        self.timers[TimerType.DASH].deactivate()

                    elif (
                        hitbox.left <= sprite.rect.right
                        and self.old_rect.left >= sprite.old_rect.right - 1
                    ):
                        hitbox.left = sprite.rect.right
                        self.timers[TimerType.DASH].deactivate()
                else:

                    if (
                        hitbox.bottom >= sprite.rect.top
                        and self.old_rect.bottom <= sprite.old_rect.top + 1
                    ):
                        hitbox.bottom = sprite.rect.top
                        self.move_vector.y = 0

                    elif (
                        hitbox.top <= sprite.rect.bottom
                        and self.old_rect.top >= sprite.old_rect.bottom - 1
                    ):
                        hitbox.top = sprite.rect.bottom
                        self.move_vector.y = 0

    def update_timers(self) -> None:
        for timer in self.timers.values():
            timer.update()

    def now_state(self) -> PlayerAnimationState:
        is_dashing = (
            self.timers[TimerType.DASH].active
            and not self.climbing
            and self.dir_vector != vector(0, 0)
            and not self.state == "crouch"
        )
        wall = any((self.on_surface[ProbeType.RIGHT], self.on_surface[ProbeType.LEFT]))
        is_pushing = wall and self.dir_vector.x != 0 and not self.is_jumping

        if self.start_dying:
            return PlayerAnimationState.DEATH
        if is_dashing:
            return PlayerAnimationState.DASH

        if self.on_surface[ProbeType.FLOOR]:
            if is_pushing:
                return PlayerAnimationState.PUSH
            if self.crouching:
                return PlayerAnimationState.CROUCH
            if self.can_balance:
                return PlayerAnimationState.BALANCE
            return (
                PlayerAnimationState.IDLE
                if self.dir_vector.x == 0
                else PlayerAnimationState.RUN
            )

        if wall and not self.on_surface[ProbeType.MANTLE]:
            if self.climbing and self.dir_vector.y != 0:
                return PlayerAnimationState.CLIMB
            if self.on_surface[ProbeType.DANGLE]:
                return PlayerAnimationState.DANGLE
            if self.move_vector.y >= 0:
                return PlayerAnimationState.WALL
        if self.move_vector.y < 0:
            return PlayerAnimationState.JUMP

        if self.move_vector.y > 0:
            if self.embrace:
                return PlayerAnimationState.EMBRACE_FALL
            return PlayerAnimationState.FALL

        return PlayerAnimationState.IDLE

    def is_touching(self, rect: pygame.Rect) -> bool:
        return rect.collidelist(self.collide_rects) >= 0

    def contact(self) -> None:
        hitbox = self.hitbox_rect

        self.collide_rects = [sprite.rect for sprite in self.collision_sprites]

        floor_rect = pygame.Rect(hitbox.bottomleft, (hitbox.width, 1))
        left_rect = pygame.Rect(
            (hitbox.topleft + vector(-1, hitbox.height / 3)), (1, hitbox.height / 3)
        )
        right_rect = pygame.Rect(
            (hitbox.topright + vector(0, hitbox.height / 3)), (1, hitbox.height / 3)
        )

        if not self.facing_left:
            climb_rect = pygame.Rect((hitbox.midright + vector(2, -7)), (1, 7))
        else:
            climb_rect = pygame.Rect((hitbox.midleft + vector(-3, -7)), (1, 7))

        if not self.facing_left:
            edge_rect = pygame.Rect((hitbox.bottomright - vector(1, 0)), (1, 4))
        else:
            edge_rect = pygame.Rect((hitbox.bottomleft), (1, 4))

        if not self.facing_left:
            dangle_rect = pygame.Rect(
                (hitbox.topright + vector(0, (hitbox.height / 1.8))), (1, 1)
            )
        else:
            dangle_rect = pygame.Rect(
                (hitbox.topleft + vector(-1, (hitbox.height / 1.8))), (1, 1)
            )

        embrace_rect = pygame.Rect(self.hitbox_rect.center, (1, TILE_SIZE * 5))

        was_on_floor = self.on_surface[ProbeType.FLOOR]
        self.on_surface[ProbeType.FLOOR] = self.is_touching(floor_rect)
        self.on_surface[ProbeType.LEFT] = self.is_touching(left_rect)
        self.on_surface[ProbeType.RIGHT] = self.is_touching(right_rect)
        wall = any((self.on_surface[ProbeType.LEFT], self.on_surface[ProbeType.RIGHT]))

        self.on_surface[ProbeType.EMBRACE_FALL] = (
            not self.is_touching(embrace_rect) and self.move_vector.y > 0
        )
        self.on_surface[ProbeType.MANTLE] = (
            not self.is_touching(climb_rect) and wall and self.climbing_active
        )
        self.on_surface[ProbeType.EDGE] = (
            True
            if not self.is_touching(edge_rect) and self.is_touching(floor_rect)
            else False
        )
        self.on_surface[ProbeType.DANGLE] = not self.is_touching(dangle_rect) and wall

        if (
            was_on_floor
            and not self.on_surface[ProbeType.FLOOR]
            and self.move_vector.y >= 0
        ):
            self.timers[TimerType.COYOTE].activate()

    def mantle__timer_timeout_fuction(self) -> None:
        self.climbing = False
        self.climbing_active = False

    def animate(self, dt: float) -> None:
        now = self.now_state()
        transitional_clips = ANIMATION_TRANSITIONS[AnimationEntity.PLAYER].values()
        transition_playing = self.state in transitional_clips
        clip_finished = int(self.frame_index) >= len(self.frames[self.state.value])
        clip_in_progress = transition_playing and not clip_finished

        if not clip_in_progress:
            state = ANIMATION_TRANSITIONS[AnimationEntity.PLAYER].get(
                (self.doing_state, now), now
            )
            if state != self.state:
                self.state = state
                self.frame_index = 0
            self.doing_state = now

        if (
            not self.climbing_active
            and not self.timers[TimerType.DASH].active
            and not self.is_sliding
        ):
            if self.dir_vector.x == 1:
                self.facing_left = False
            elif self.dir_vector.x == -1:
                self.facing_left = True

        self.frame_index = (
            self.frame_index
            + ANIMATION_INFO[AnimationEntity.PLAYER][self.state][0] * dt
        )
        frames = self.frames[self.state.value]
        if not ANIMATION_INFO[AnimationEntity.PLAYER][self.state][1] and int(
            self.frame_index
        ) >= len(frames):
            self.image = frames[-1]
            if self.start_dying:
                self.dead = True
                return
        else:
            self.image = frames[int(self.frame_index) % len(frames)]
        if not self.facing_left:
            self.image = pygame.transform.flip(self.image, True, False)

    def update(self, dt: float) -> None:
        self.update_timers()
        if not self.start_dying:
            self.old_rect = self.hitbox_rect.copy()
            self.input()
            self.contact()
            self.move(dt)
        self.animate(dt)
