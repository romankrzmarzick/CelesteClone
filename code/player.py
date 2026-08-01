from settings import *
from event_timers import Timer


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
        # state is the clip actually playing (could be a transition clip), doing_state
        # is the real logical state, used to look up what transition to play next
        self.state, self.doing_state, self.facing_left = "idle", "idle", True
        self.image = self.frames[self.state][self.frame_index]

        self.dir_vector = vector()   # input intent, -1/0/1 per axis
        self.move_vector = vector()  # actual velocity, pixels/second

        self.is_jumping = False

        self.crouching = False
        self.embrace = False    # true once falling with nothing close below (long fall)
        self.can_dash = True    # only comes back once you land

        self.climbing = False         # grip key held
        self.climbing_active = False  # actually gripping a wall right now

        self.can_balance = False  # teeter animation waited long enough to play
        self.is_sliding = False

        self.collision_sprites = collision_sprites

        # rect is just for drawing, hitbox_rect is what actually collides
        self.rect: pygame.FRect = self.image.get_frect(center=pos)
        self.hitbox_rect: pygame.FRect = self.rect.inflate((-8, -4))
        self.old_rect: pygame.FRect = self.hitbox_rect.copy()
        self.old_dir = vector()  # direction latched when the dash started

        self.collide_rects: list[pygame.FRect] = []  # rebuilt each frame by contact()
        self.on_surface: dict[str, bool] = {"floor" : False, "left" : False, "right" : False, "edge" : False, "dangle" : False, "embrace" : False, "mantle" : False}

        self.timers: dict[str, Timer] = {
            "balance_delay" : Timer(500, func=self.balance_animation),
            "wall_jump" : Timer(190),
            "wall_jump_delay" : Timer(250),
            "dash" : Timer(290),
            "mantle" : Timer(100),
            "coyote" : Timer(180),
            "dash_delay" : Timer(230)
        }

        self.dead = False

    def input(self) -> None:
        input_dir = vector()
        keys = pygame.key.get_pressed()

        if not self.timers["dash"].active:
            if not self.timers["wall_jump"].active:
                if not self.timers["mantle"].active:
                    if keys[pygame.K_RIGHT]:
                        input_dir.x = 1
                    if keys[pygame.K_LEFT]:
                        input_dir.x = - 1
                    if keys[pygame.K_UP]:
                        input_dir.y = -1
                    if keys[pygame.K_DOWN]:
                        input_dir.y =  1
                    self.dir_vector = input_dir

        if keys[pygame.K_UP] and not self.crouching and not self.climbing_active:
            self.is_jumping = True

        if keys[pygame.K_DOWN]:
            self.crouching = True
        else: self.crouching = False


        if keys[pygame.K_SPACE]:
            self.climbing = True

        else: self.climbing = False

        if keys[pygame.K_x]:
            # old_dir latches the direction now, so the dash keeps going that
            # way even after the keys are released mid-dash.
            if not self.timers["dash_delay"].active and not self.climbing:
                if self.can_dash and not self.timers["wall_jump"].active:
                    self.timers["dash"].activate()
                    self.old_dir = input_dir

    def move(self, dt: float) -> None:
        self.is_embrace()
        self.balance()

        if not self.timers['mantle'].active:
            self.climb(dt)
            if self.climbing_active:
                self.collisions("x")
                self.collisions("y")
                self.update_rect()
                # re-armed every frame you're climbing, so the cooldown counts from
                # the moment you actually let go of the wall
                self.timers["dash_delay"].activate()
                return

        elif self.timers["mantle"].active:
            self.mantle(dt)
            self.update_rect()
            return

        # freeze in place while the crouch clip is playing
        if self.crouching and self.on_surface["floor"] and self.state == "crouch":
            return

        if self.dash(dt):
            self.collisions("x")
            self.collisions("y")
            self.update_rect()
            return

        # wall slide replaces gravity outright instead of just damping it
        if self.wall_slide(dt):
            pass
        else: self.gravity(dt)

        self.collisions("y")

        if not self.timers["dash"].active:
            self.x_move(dt)
        self.collisions("x")

        if self.is_jumping:
            if self.on_surface["floor"] or self.timers["coyote"].active:
                self.timers["coyote"].deactivate()
                self.jump()
            if not self.timers["wall_jump_delay"].active and any((self.on_surface["left"], self.on_surface["right"])):
                self.wall_jump()
            self.is_jumping = False

        self.update_rect()

    def is_embrace(self) -> None:
        if self.on_surface["embrace"]:
            self.embrace = True
        if self.on_surface["floor"]:
            self.embrace = False

    def balance_animation(self) -> None:  # callback for balance_delay timer
        self.can_balance = True

    def balance(self) -> None:
        on_edge = self.on_surface["edge"]

        if on_edge and not self.timers["balance_delay"].active and self.on_surface["floor"]:
            self.timers["balance_delay"].activate()
        if not on_edge or not self.on_surface["floor"]:
            self.timers["balance_delay"].deactivate()
            self.can_balance=False

    def mantle(self, dt: float) -> None:
        self.hitbox_rect.y += -PLAYER_PHYSICS.mantle_y_speed * dt
        self.dir_vector.x = -1 if self.facing_left else 1
        self.hitbox_rect.x += PLAYER_PHYSICS.mantle_x_speed * self.dir_vector.x * dt

    def climb(self, dt: float) -> None:
        if self.on_surface["mantle"]:
            self.timers["mantle"].activate()

        else:
            if self.climbing and not self.on_surface["floor"] and not self.on_surface["mantle"] and any((self.on_surface["left"], self.on_surface["right"])):
                self.move_vector.y = 0
                self.hitbox_rect.y += (PLAYER_PHYSICS.climbing_speed * self.dir_vector.y) * dt
                self.climbing_active = True
            else: self.climbing_active = False

    def x_move(self, dt: float) -> None:
        # ramps up to top speed instead of snapping to it (gives running some weight),
        # but letting go of the direction key drops speed to 0 immediately - no momentum
        if self.dir_vector.x != 0:
            self.move_vector.x += PLAYER_PHYSICS.x_acceleration * self.dir_vector.x / 2 * dt
            if self.move_vector.x > PLAYER_PHYSICS.x_max_speed: self.move_vector.x = PLAYER_PHYSICS.x_max_speed
            elif self.move_vector.x < -PLAYER_PHYSICS.x_max_speed: self.move_vector.x = -PLAYER_PHYSICS.x_max_speed

            # x speed when moving from a wall.
            if not self.on_surface["floor"]:
                self.move_vector.x = (PLAYER_PHYSICS.x_max_speed * .8) * self.dir_vector.x


            self.hitbox_rect.x += self.move_vector.x * dt
            self.move_vector.x += PLAYER_PHYSICS.x_acceleration * self.dir_vector.x / 2 * dt
            if self.move_vector.x > PLAYER_PHYSICS.x_max_speed: self.move_vector.x = PLAYER_PHYSICS.x_max_speed
            elif self.move_vector.x < -PLAYER_PHYSICS.x_max_speed: self.move_vector.x = -PLAYER_PHYSICS.x_max_speed
        if self.dir_vector.x == 0: self.move_vector.x = 0

    def gravity(self, dt: float) -> None:
        # split the acceleration before/after the position update so the jump arc
        # stays the same shape no matter the framerate
        self.move_vector.y += PLAYER_PHYSICS.gravity_num / 2 * dt
        self.move_vector.y = min(PLAYER_PHYSICS.max_fall_speed, self.move_vector.y)
        self.hitbox_rect.y += self.move_vector.y * dt
        self.move_vector.y += PLAYER_PHYSICS.gravity_num / 2 * dt
        self.move_vector.y = min(PLAYER_PHYSICS.max_fall_speed, self.move_vector.y)

    def jump(self) -> None:
        self.timers["wall_jump_delay"].activate()  # avoid an accidental wall jump right after this
        self.move_vector.y = -PLAYER_PHYSICS.jump_height
        self.hitbox_rect.bottom -= 1  # nudge to fix a stick-to-ground glitch

    def wall_jump(self) -> None:
        self.timers["wall_jump"].activate()  # blocks x input while it's active
        self.move_vector.x = 0
        self.move_vector.y = -PLAYER_PHYSICS.jump_height
        self.dir_vector.x = 1 if self.on_surface["left"] else -1

    def wall_slide(self, dt: float) -> bool:
        # needs: airborne, touching a wall, falling, not mantling, still holding a
        # direction - let go and you just drop off the wall instead
        if not self.on_surface["floor"] and any((self.on_surface["left"], self.on_surface["right"])) and self.move_vector.y > 0 and not self.on_surface["mantle"] and self.move_vector.x != 0:
            self.move_vector.y = 0
            self.hitbox_rect.y += PLAYER_PHYSICS.gravity_num / 8 * dt
            self.is_sliding = True
            return True
        self.is_sliding = False
        return False

    def dash(self, dt: float) -> bool:
        # wipes move_vector, so a dash cancels whatever gravity/momentum was happening -
        # that's what makes it useful for saving a bad jump. one per landing.
        if self.on_surface["floor"]:
            self.can_dash = True

        if self.timers["dash"].active and self.dir_vector != vector(0, 0) and self.state != "wall" and self.state != "climb" and not self.timers["mantle"].active:
            normalized_dir = self.old_dir.normalize() if self.old_dir else self.old_dir
            self.can_dash = False
            self.move_vector = vector(0, 0)
            self.hitbox_rect.center += (PLAYER_PHYSICS.dash_speed * normalized_dir) * dt
            return True
        return False

    def update_rect(self) -> None:
        # hitbox is the source of truth, rect just follows it plus a per-clip
        # offset (mirrored when facing right so it leans the same way)
        redraw_num = ANIMATION_CORRECTION["player"][self.state]
        if self.facing_left:
            self.rect.center = self.hitbox_rect.center + redraw_num
        else: self.rect.center = self.hitbox_rect.center + vector(-redraw_num.x, redraw_num.y)

    def collisions(self, direction: str) -> None:
        hitbox = self.hitbox_rect

        for sprite in self.collision_sprites:
            if hitbox.colliderect(sprite.rect):
                if direction == "x":
                    # moving right into the tile's left face
                    if hitbox.right >= sprite.rect.left and self.old_rect.right <= sprite.old_rect.left + 1:
                        hitbox.right = sprite.rect.left
                        self.timers["dash"].deactivate()
                    # moving left into the tile's right face
                    elif hitbox.left <= sprite.rect.right and self.old_rect.left >= sprite.old_rect.right - 1:
                        hitbox.left = sprite.rect.right
                        self.timers["dash"].deactivate()
                else:
                    # landing on top of the tile
                    if hitbox.bottom >= sprite.rect.top and self.old_rect.bottom <= sprite.old_rect.top + 1:
                        hitbox.bottom = sprite.rect.top
                        self.move_vector.y = 0

                    # bonking the underside of the tile
                    elif hitbox.top <= sprite.rect.bottom and self.old_rect.top >= sprite.old_rect.bottom - 1:
                        hitbox.top = sprite.rect.bottom
                        self.move_vector.y = 0

    def update_timers(self) -> None:
        for timer in self.timers.values():
            timer.update()

    def now_state(self) -> str:
        # priority ladder, most specific first - death, dash, grounded, wall, airborne.
        # first match wins, and whatever name comes back has to match a folder in
        # graphics/player/ and a key in ANIMATION_INFO
        if self.dead:
            return "death"

        wall = any((self.on_surface["right"], self.on_surface["left"]))
        if self.timers["dash"].active and not self.climbing and self.dir_vector != vector(0, 0) and not self.state == "crouch":
            return "dash"
        if self.on_surface["floor"]:
            if wall and self.dir_vector.x != 0 and not self.is_jumping:
                return "push"
            if self.crouching:
                return "crouch"
            if self.can_balance:
                return "balance"
            return "idle" if self.dir_vector.x == 0 else "run"
        if wall and not self.on_surface["mantle"]:
            if self.climbing and self.dir_vector.y != 0:
                return "climb"
            if self.on_surface["dangle"]:
                return "dangle"
            if self.move_vector.y >= 0:
                return "wall"
        if self.move_vector.y < 0:
            return "jump"

        if self.move_vector.y > 0:
            if self.embrace:
                return "embrace"
            return "fall"
        return "idle"

    def is_touching(self, rect: pygame.Rect) -> bool:
        return rect.collidelist(self.collide_rects) >= 0

    def contact(self) -> None:
        hitbox = self.hitbox_rect

        self.collide_rects = [sprite.rect for sprite in self.collision_sprites]

        floor_rect = pygame.Rect(hitbox.bottomleft, (hitbox.width, 1))
        left_rect = pygame.Rect((hitbox.topleft + vector(-1, hitbox.height / 3)), (1, hitbox.height / 3))
        right_rect = pygame.Rect((hitbox.topright + vector(0, hitbox.height / 3)), (1, hitbox.height / 3))

        # speical contact rects.
        if not self.facing_left:
            climb_rect = pygame.Rect((hitbox.midright + vector(2, -7)), (1, 7))
        else: climb_rect = pygame.Rect((hitbox.midleft + vector(-3, -7)), (1, 7))

        if not self.facing_left:
            edge_rect = pygame.Rect((hitbox.bottomright - vector(1, 0)), (1, 4))
        else: edge_rect = pygame.Rect((hitbox.bottomleft), (1, 4))

        if not self.facing_left:
            dangle_rect = pygame.Rect((hitbox.topright + vector(0, (hitbox.height / 1.8))), (1, 1))
        else: dangle_rect = pygame.Rect((hitbox.topleft + vector(-1, (hitbox.height / 1.8))), (1, 1))

        embrace_rect = pygame.Rect(self.hitbox_rect.center, (1, TILE_SIZE * 5))

        was_on_floor = self.on_surface["floor"]
        self.on_surface["floor"] = self.is_touching(floor_rect)
        self.on_surface["left"] = self.is_touching(left_rect)
        self.on_surface["right"] = self.is_touching(right_rect)
        wall = any((self.on_surface["left"], self.on_surface["right"]))

        self.on_surface["embrace"] = not self.is_touching(embrace_rect) and self.move_vector.y > 0
        self.on_surface["mantle"] = not self.is_touching(climb_rect) and wall and self.climbing_active
        self.on_surface["edge"] = True if not self.is_touching(edge_rect) and self.is_touching(floor_rect) else False
        self.on_surface["dangle"] = not self.is_touching(dangle_rect) and wall

        # coyote time: only arms the one frame the floor disappears out from under you,
        # and only if you were falling normally - if you jumped off, y velocity is
        # already negative here, so this wouldn't give you a free double jump
        if was_on_floor and not self.on_surface["floor"] and self.move_vector.y >= 0:
            self.timers["coyote"].activate()

    def animate(self, dt: float) -> None:
        now = self.now_state()
        transitional_clips = ANIMATION_TRANSITIONS["player"].values()
        transition_playing = self.state in transitional_clips
        clip_finished = int(self.frame_index) >= len(self.frames[self.state])
        clip_in_progress = transition_playing and not clip_finished

        if not clip_in_progress:
            state = ANIMATION_TRANSITIONS["player"].get((self.doing_state, now), now)
            if state != self.state:
                self.state = state
                self.frame_index = 0
            self.doing_state = now

        if not self.climbing_active and not self.timers["dash"].active and not self.is_sliding:
            if self.dir_vector.x == 1: self.facing_left = False
            elif self.dir_vector.x == -1: self.facing_left = True

        self.frame_index = self.frame_index + ANIMATION_INFO["player"][self.state][0] * dt
        frames = self.frames[self.state]
        if not ANIMATION_INFO["player"][self.state][1] and int(self.frame_index) >= len(frames):
            self.image = frames[-1]
            if self.dead:
                self.kill()
        else:
            self.image = frames[int(self.frame_index) % len(frames)]
        if not self.facing_left:
            self.image = pygame.transform.flip(self.image, True, False)

    def update(self, dt: float) -> None:
        self.update_timers()
        if not self.dead:
            self.old_rect = self.hitbox_rect.copy()
            self.input()
            self.contact()
            self.move(dt)
        self.animate(dt)
