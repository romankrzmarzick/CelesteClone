"""
The player character: input, movement, collision, and animation.

This is the heart of the game. Read the Player class docstring first -- it lays
out the order things happen in a frame, which is what makes the rest of the
file make sense.
"""

from settings import *
from event_timers import Timer


class Player(pygame.sprite.Sprite):
    """
    A Celeste-style platforming character.

    One frame, in order (see `update`):

        update_timers()  tick every countdown
        old_rect         where the hitbox was, for collision resolution
        input()          keyboard -> dir_vector + mode flags
        contact()        probe the world -> on_surface
        move()           run one movement mode, then resolve collisions
        animate()        pick a state, step the frames

    `contact` runs before `move` so every movement decision is made against the
    world as it was at the start of the frame.

    Rects:
        hitbox_rect  the physical player, 7x13. All movement and collision.
        rect         where the image is drawn. Follows the hitbox each frame,
                     plus a cosmetic per-animation nudge.
        old_rect     the hitbox last frame. Tells `collisions` which side of a
                     tile was hit.

    Vectors:
        dir_vector   input intent; each component is -1, 0 or 1.
        move_vector  velocity in pixels/second.

    `on_surface` is a dict of booleans rebuilt each frame by `contact` -- see
    that method for what each probe means.

    `move` is a priority chain: mantle > climb > crouch > dash > walking. The
    first mode that applies returns early, which is why a mantle cannot be
    interrupted and a dash ignores gravity.

    Timers, all in milliseconds, each gating one rule:
        balance_delay    wait before the idle teeter animation
        wall_jump        lock out steering after a wall jump
        wall_jump_delay  stops a jump instantly becoming a wall jump
        dash, dash_delay dash duration, then its cooldown
        mantle           ledge pull-up duration
        coyote           late-jump grace after walking off a ledge
    """

    def __init__(
        self,
        pos: tuple[float, float],
        groups,
        collision_sprites: pygame.sprite.Group,
        frames: dict[str, list[pygame.Surface]],
        z: int,
    ) -> None:
        """
        Args:
            pos:               spawn point, used as the centre of `rect`.
            groups:            sprite group(s) to join, normally all_sprites.
            collision_sprites: the solid terrain to collide against.
            frames:            {animation_name: [surfaces]} from import_sub_folder.
            z:                 draw layer, see Z_LAYERS.
        """
        # player general setup
        super().__init__(groups)
        self.z = z

        # // player image
        self.frames, self.frame_index = frames, 0
        # state       : the clip currently playing (may be a transition clip)
        # doing_state : the logical state, used to look up transitions
        self.state, self.doing_state, self.facing_left = "idle", "idle", True
        self.image = self.frames[self.state][self.frame_index]

        # // player vectors
        self.dir_vector = vector()   # input intent, components in {-1, 0, 1}
        self.move_vector = vector()  # velocity in pixels/second

        # // y-direction atrributes
        self.is_jumping = False

        # // special movement
        # player crouching
        self.crouching = False

        # player long-fall: True once falling with nothing close below
        self.embrace = False

        # player dash: refreshed on landing, spent on dashing
        self.can_dash = True

        # player climbing
        self.climbing = False         # the grip key is held
        self.climbing_active = False  # actually gripping a wall right now

        # balance bool: the teeter animation has waited long enough to play
        self.can_balance = False

        self.is_sliding = False

        # // player rects
        # player collisions
        self.collision_sprites = collision_sprites

        # images are only drawn on self.rect and updates the position with the hitbox.
        self.rect: pygame.FRect = self.image.get_frect(center=pos)

        # an inflated rect that interacts with the collidable rects.
        self.hitbox_rect: pygame.FRect = self.rect.inflate((-8, -4))

        # old_rect is used for the collision logic to find location between two objects.
        self.old_rect: pygame.FRect = self.hitbox_rect.copy()
        self.old_dir = vector()  # direction latched when the dash started

        # cached rects of every collidable, rebuilt each frame by contact()
        self.collide_rects: list[pygame.FRect] = []

        # detection rects that are based on the player's position for specified use cases.
        self.on_surface: dict[str, bool] = {"floor" : False, "left" : False, "right" : False, "edge" : False, "dangle" : False, "embrace" : False, "mantle" : False}

        # // timers
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
        """
        Read the keyboard into `dir_vector` and the mode flags.

        Arrows move, Up jumps, Down crouches, Space grips a wall, X dashes.

        Steering is suppressed during a dash, wall jump, or mantle: those moves
        own the direction for their duration, so `dir_vector` keeps its old
        value instead of being overwritten.
        """
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
        """
        Run one frame of movement, then resolve collisions.

        A priority chain -- each mode that takes over returns early, so only
        one is ever in charge:

            1. mantle   pulling over a ledge, uninterruptible
            2. climb    gripping a wall, gravity cancelled
            3. crouch   held still mid-crouch clip
            4. dash     fixed-speed burst, gravity cancelled
            5. default  wall slide or gravity, then walking, then jumps

        In the default path y moves and resolves before x. Splitting the axes
        is what stops the player snagging on tile seams.
        """
        self.is_embrace()
        self.balance()

        # // climb
        if not self.timers['mantle'].active:
            self.climb(dt)
            if self.climbing_active:
                self.collisions("x")
                self.collisions("y")
                self.update_rect()
                # re-armed every frame of the climb, so the cooldown is
                # measured from the moment the player lets go of the wall
                self.timers["dash_delay"].activate()
                return

        elif self.timers["mantle"].active:
            self.mantle(dt)
            self.update_rect()
            return

        # // crouching switch
        # Freeze in place while the crouch clip is the active animation.
        if self.crouching and self.on_surface["floor"] and self.state == "crouch":
            return

        # // dash
        if self.dash(dt):
            self.collisions("x")
            self.collisions("y")
            self.update_rect()
            return

        # // gravity
        # A wall slide replaces gravity outright rather than damping it.
        if self.wall_slide(dt):
            pass
        else: self.gravity(dt)

        self.collisions("y")

        if not self.timers["dash"].active:
            self.x_move(dt)
        self.collisions("x")

        # // jumps
        if self.is_jumping:
            if self.on_surface["floor"] or self.timers["coyote"].active:
                self.timers["coyote"].deactivate()
                self.jump()
            if not self.timers["wall_jump_delay"].active and any((self.on_surface["left"], self.on_surface["right"])):
                self.wall_jump()
            self.is_jumping = False

        self.update_rect()

    def is_embrace(self) -> None:
        """
        This function is used to set the embrace bool according to the state of the embrace surface when falling.
        If the player is high above the ground when it reaches its time to switch to its fall state the embrace/longfall will be switched to True.
        """
        if self.on_surface["embrace"]:
            self.embrace = True
        if self.on_surface["floor"]:
            self.embrace = False

    def balance_animation(self) -> None:
        """Callback fired by `balance_delay` -- allows the teeter clip to play."""
        self.can_balance = True

    def balance(self) -> None:
        """
        Gate the ledge-teetering animation behind a short idle delay.

        Standing on an edge starts the timer; leaving the edge or the floor
        cancels it, so the teeter only shows up after loitering on a ledge.
        """
        on_edge = self.on_surface["edge"]

        if on_edge and not self.timers["balance_delay"].active and self.on_surface["floor"]:
            self.timers["balance_delay"].activate()
        if not on_edge or not self.on_surface["floor"]:
            self.timers["balance_delay"].deactivate()
            self.can_balance=False

    def mantle(self, dt: float) -> None:
        """
        The mantle recorrects the player's position when it is above the top surface of a rect when climbing.
        This is needed to avoid the rect collision correction, because otherwise the player wouldn't be able to clear the edge.
        """
        self.hitbox_rect.y += -PLAYER_PHYSICS.mantle_y_speed * dt
        self.dir_vector.x = -1 if self.facing_left else 1
        self.hitbox_rect.x += PLAYER_PHYSICS.mantle_x_speed * self.dir_vector.x * dt

    def climb(self, dt: float) -> None:
        """
        The climb function allows the player to move up and down on a surface while canceling out the y-direction gravity.
        When the climb key is held, the player sticks to the wall without any outside forces.

        If the hand probe has cleared the wall top this hands off to the mantle
        instead, which is how the player gets over a ledge rather than being
        stopped dead by collision correction.
        """
        if self.on_surface["mantle"]:
            self.timers["mantle"].activate()

        else:
            if self.climbing and not self.on_surface["floor"] and not self.on_surface["mantle"] and any((self.on_surface["left"], self.on_surface["right"])):
                self.move_vector.y = 0
                self.hitbox_rect.y += (PLAYER_PHYSICS.climbing_speed * self.dir_vector.y) * dt
                self.climbing_active = True
            else: self.climbing_active = False

    def x_move(self, dt: float) -> None:
        """
        Accelerate horizontally toward the input direction, and apply it.

        Speed ramps up (~0.14s to top speed) rather than snapping, which gives
        the run some weight. Half the acceleration is added either side of the
        position update, same as `gravity`. Releasing the direction drops speed
        to zero at once -- precise platforming, not momentum. In the air, speed
        is forced to 80% of max instead of ramping, so air control stays even.

        Raise `x_acceleration` in PlayerPhysics for a snappier start.
        """
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
        """
        Accelerate downward, capped at terminal velocity.

        Half the acceleration lands before the position update and half after
        (a leapfrog step), which keeps a jump arc the same shape at any
        framerate.
        """
        self.move_vector.y += PLAYER_PHYSICS.gravity_num / 2 * dt
        self.move_vector.y = min(PLAYER_PHYSICS.max_fall_speed, self.move_vector.y)
        self.hitbox_rect.y += self.move_vector.y * dt
        self.move_vector.y += PLAYER_PHYSICS.gravity_num / 2 * dt
        self.move_vector.y = min(PLAYER_PHYSICS.max_fall_speed, self.move_vector.y)

    def jump(self) -> None:
        """
        Jump first activates the wall jump delay timer to avoid unwanted wall jumps at the start of the jump.
        Finally the jump simply sets the move_vector.y to the jump height as a negative to move the rect upwards.
        """
        self.timers["wall_jump_delay"].activate()
        self.move_vector.y = -PLAYER_PHYSICS.jump_height
        # small pixel adjustment for stick glitch
        self.hitbox_rect.bottom -= 1

    def wall_jump(self) -> None:
        """
        When the player object is on a wall and the jump key is pressed, the wall jump timer is activated to deny x direction input.
        It does the same jump height for the y vector while pushing the object in the opposite direction from the wall.
        """
        self.timers["wall_jump"].activate()
        self.move_vector.x = 0
        self.move_vector.y = -PLAYER_PHYSICS.jump_height
        self.dir_vector.x = 1 if self.on_surface["left"] else -1

    def wall_slide(self, dt: float) -> bool:
        """
        Gets rid of the gravity influence on the player object to then slowly push the character downwards to represent slding.

        Needs: airborne, touching a wall, already falling, not mantling, and
        still holding a direction -- let go and you drop off the wall.

        Returns:
            True if the slide handled vertical movement, so `move` skips gravity.
        """
        if not self.on_surface["floor"] and any((self.on_surface["left"], self.on_surface["right"])) and self.move_vector.y > 0 and not self.on_surface["mantle"] and self.move_vector.x != 0:
            self.move_vector.y = 0
            self.hitbox_rect.y += PLAYER_PHYSICS.gravity_num / 8 * dt
            self.is_sliding = True
            return True
        self.is_sliding = False
        return False

    def dash(self, dt: float) -> bool:
        """
        Move at a fixed speed along the direction latched when the dash began.

        The direction is normalised so a diagonal covers the same distance as a
        straight dash. `move_vector` is wiped, so a dash cancels any gravity or
        momentum in progress -- that reset is what makes it save a bad jump.
        One dash per landing: `can_dash` only comes back on the floor.

        Returns:
            True if a dash moved the player, so `move` skips the normal path.
        """
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
        """
        A custom updating func for the self.rect based on the hitbox rect to fix animations.

        The hitbox is the source of truth; the drawn rect follows it plus a
        per-clip offset from ANIMATION_CORRECTION, mirrored when facing right
        so the nudge always leans the same way relative to the character.
        """
        # Below adjusts the climb and wall animation to draw one more px over in the facing direction.
        redraw_num = ANIMATION_CORRECTION["player"][self.state]
        if self.facing_left:
            self.rect.center = self.hitbox_rect.center + redraw_num
        else: self.rect.center = self.hitbox_rect.center + vector(-redraw_num.x, redraw_num.y)

    def collisions(self, direction: str) -> None:
        """
        Push the hitbox back out of any terrain it has moved into.

        Called once per axis, after that axis has moved. `old_rect` decides
        which side the overlap came from: if the player used to be left of a
        tile and now overlaps it, they hit its left face and snap flush. Using
        last frame's position is what stops fast movement ejecting the player
        out of the wrong side.

        Hitting a wall sideways also cancels a dash, so dashing into a wall
        stops dead instead of grinding along it.

        Args:
            direction: "x" for horizontal, anything else for vertical.
        """
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
        """Loops through the self.timers dictionary to update the time for them."""
        for timer in self.timers.values():
            timer.update()

    def now_state(self) -> str:
        """
        Decide which animation state the player is in right now.

        A priority ladder, most specific first: death, dash, grounded states,
        wall states, then plain airborne. First match wins, so the ordering is
        the design. The name returned must match a folder in graphics/player/
        and a key in ANIMATION_INFO.

        Returns:
            The state name, e.g. "idle", "run", "wall", "dangle".
        """
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
        """
        Helper function for contact. Looks to see if the passed in rect collides with any thing.

        A pure query -- no side effects.

        Args:
            rect: a probe rect in world space.

        Returns:
            True if it overlaps any collidable tile.
        """
        return rect.collidelist(self.collide_rects) >= 0

    def contact(self) -> None:
        """
        Rebuild `on_surface` by probing the world with thin feeler rects.

        Each question gets its own 1px rect just outside the hitbox, so the
        answers stay independent and precise. The probes that ask about the
        *leading* edge flip sides with `facing_left`.

            floor       strip along the bottom edge.
            left/right  strips down the middle third of each side, so a shallow
                        ledge at head or foot height isn't counted as a wall.
            climb       7px beside the upper body; once it touches nothing the
                        hand has cleared the wall top -> mantle.
            edge        4px below the leading foot; nothing there while standing
                        means the player is on a ledge.
            dangle      1px beside the upper body; nothing there while on a wall
                        means the upper body is over the lip.
            embrace     5 tiles below the centre; nothing there while falling
                        means a long drop -> curled-up clip.

        Careful: "mantle", "edge", "dangle" and "embrace" are true when their
        probe touches *nothing*.

        This is also the only place that knows the floor state both before and
        after the update, so it is where coyote time gets armed.
        """
        hitbox = self.hitbox_rect

        # grabs only the rect from the sprite to avoid passing in the entire sprite.
        self.collide_rects = [sprite.rect for sprite in self.collision_sprites]

        # core contact rects.
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

        # // core
        was_on_floor = self.on_surface["floor"]
        self.on_surface["floor"] = self.is_touching(floor_rect)
        self.on_surface["left"] = self.is_touching(left_rect)
        self.on_surface["right"] = self.is_touching(right_rect)
        wall = any((self.on_surface["left"], self.on_surface["right"]))

        # // special
        self.on_surface["embrace"] = not self.is_touching(embrace_rect) and self.move_vector.y > 0

        self.on_surface["mantle"] = not self.is_touching(climb_rect) and wall and self.climbing_active

        self.on_surface["edge"] = True if not self.is_touching(edge_rect) and self.is_touching(floor_rect) else False

        self.on_surface["dangle"] = not self.is_touching(dangle_rect) and wall

        # // coyote time
        # Armed on the one frame the floor disappears, so the window is always
        # the full duration. The downward check separates walking off a ledge
        # from jumping off one -- a jump leaves with negative y velocity, and
        # arming here would give a free second jump in mid-air.
        if was_on_floor and not self.on_surface["floor"] and self.move_vector.y >= 0:
            self.timers["coyote"].activate()

    def animate(self, dt: float) -> None:
        """
        Advance the sprite animation and pick this frame's image.

        1. Transition clips. If the state being left and the one being entered
           are a pair in ANIMATION_TRANSITIONS (landing, or springing into a
           jump), that one-shot clip plays instead and finishes before anything
           can interrupt it -- the `clip_in_progress` guard.
        2. Facing. Frozen while climbing, dashing, or wall sliding so the
           character doesn't flip mid-move.
        3. Frames. `frame_index` advances by the clip's fps * dt. Looping clips
           wrap; one-shot clips hold the last frame -- and if that was the
           death clip, the sprite kills itself so Level can swap in a new one.

        The art is drawn facing left, so it is mirrored when facing right.
        """
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
        """
        One frame of the player, called by AllSprites.update.

        While dead, input/contact/movement are skipped so the body freezes
        where it fell, but `animate` keeps running so the death clip plays out
        and eventually `kill()`s the sprite.
        """
        self.update_timers()
        if not self.dead:
            self.old_rect = self.hitbox_rect.copy()
            self.input()
            self.contact()
            self.move(dt)
        self.animate(dt)
