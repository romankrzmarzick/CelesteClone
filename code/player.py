from settings import * 
from event_timers import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, collision_sprites, frames, z=Z_LAYERS["main"]):
        # player general setup
        super().__init__(groups)
        self.z = z

        # // player image
        self.frames, self.frame_index = frames, 0
        self.state, self.doing_state, self.facing_left = "idle", "idle", True
        self.image = self.frames[self.state][self.frame_index]
        
        # // player vectors
        self.dir_vector = vector()
        self.move_vector = vector()
        
        # x-axis speed
        self.x_speed = 7
        self.x_max_speed = 60

        # // y-direction atrributes
        self.is_jumping = False
        self.jump_height = 155
        self.gravity_num = 460
        self.max_fall_speed = 160

        # // special movement
        # player crouching 
        self.crouching = False

        # player long-fall
        self.embrace = False

        # player dash 
        self.dash_speed = 140
        self.can_dash = True

        # player climbing
        self.climbing_speed = 50
        self.climbing_active = False

        # player mantle
        self.mantle_x_speed = 40
        self.mantle_y_speed = 80


        # // player rects
        # player collisions
        self.collision_sprites = collision_sprites
        
        # images are only drawn on self.rect and updates the position with the hitbox.
        self.rect = self.image.get_frect(center=pos)
        
        # an inflated rect that interacts with the collidable rects.
        self.hitbox_rect = self.rect.inflate((-4, 0))
        
        # old_rect is used for the collision logic to find location between two objects. 
        self.old_rect = self.hitbox_rect.copy()

        # detection rects that are based on the player's position for specified use cases. 
        self.on_surface = {"floor" : False, "left" : False, "right" : False, "edge" : False, "dangle" : False, "embrace" : False, "climb-mantle" : False}

        # // timers
        self.timers = {
            "balance_delay" : Timer(1200, func=self.balance_animation_delay),
            "wall_jump" : Timer(190),
            "wall_jump_delay" : Timer(250),
            "dash" : Timer(290),
            "mantle" : Timer(100),
        }

    def dash_move(self, dt):
        if self.on_surface["floor"]:
            self.can_dash = True

        if self.timers["dash"].active and self.dir_vector != vector(0, 0):
            normalized_dir = self.old_dir.normalize() if self.old_dir else self.old_dir
            self.can_dash = False
            self.move_vector = vector(0, 0)
            self.hitbox_rect.center += (self.dash_speed * normalized_dir) * dt
            return True
        return False

    def input(self):
        input_dir = vector()
        keys = pygame.key.get_pressed()
        
        if not self.timers["dash"].active:
            if not self.timers["wall_jump"].active:
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
        
        if keys[pygame.K_x]:
            if self.can_dash and not self.timers["wall_jump"].active:
                self.timers["dash"].activate()
                self.old_dir = input_dir

        if keys[pygame.K_SPACE]:
            self.climbing = True
        else: self.climbing = False

    def balance_animation_delay(self):
        self.on_surface["edge"] = True

    def embrace_active(self):
        """
        This function is used to set the embrace bool according to the state of the embrace surface when falling.
        If the player is high above the ground when it reaches its time to switch to its fall state the embrace/longfall will be switched to True.
        """
        if self.on_surface["embrace"]:
            self.embrace = True
        if self.on_surface["floor"]:
            self.embrace = False
        return self.embrace

    def mantle(self, dt):
        """
        The mantle recorrects the player's position when it is above the top surface of a rect when climbing.
        This is needed to avoid the rect collision correction, because otherwise the player wouldn't be able to clear the edge.
        """
        self.hitbox_rect.y += -self.mantle_y_speed * dt
        self.dir_vector.x = -1 if self.facing_left else 1
        self.hitbox_rect.x += self.mantle_x_speed * self.dir_vector.x * dt

    def climb(self, dt):
        """
        The climb function allows the player to move up and down on a surface while canceling out the y-direction gravity.
        When the climb key is held, the player sticks to the wall without any outside forces. 
        """
        if self.on_surface["climb-mantle"]:
            self.timers["mantle"].activate()
        if self.timers["mantle"].active:
           self.mantle(dt)
        else:
            if self.climbing and not self.on_surface["floor"] and any((self.on_surface["left"], self.on_surface["right"])):
                self.move_vector.y = 0
                self.hitbox_rect.y += (self.climbing_speed * self.dir_vector.y) * dt
                self.climbing_active = True
            else: self.climbing_active = False
    
    def x_move(self, dt):
        if self.dir_vector.x != 0:
            self.move_vector.x += self.x_speed * self.dir_vector.x / 2
            if self.move_vector.x > self.x_max_speed: self.move_vector.x = self.x_max_speed
            elif self.move_vector.x < -self.x_max_speed: self.move_vector.x = -self.x_max_speed
            self.hitbox_rect.x += self.move_vector.x * dt
            self.move_vector.x += self.x_speed * self.dir_vector.x / 2
        else: self.move_vector.x = 0
    
    def gravity(self, dt):
        self.move_vector.y += self.gravity_num / 2 * dt 
        self.move_vector.y = min(self.max_fall_speed, self.move_vector.y)
        self.hitbox_rect.y += self.move_vector.y * dt
        self.move_vector.y += self.gravity_num / 2 * dt

    def jump(self):
        """
        Jump first activates the wall jump delay timer to avoid unwanted wall jumps at the start of the jump.
        Finally the jump simply sets the move_vector.y to the jump height as a negative to move the rect upwards.
        """
        self.timers["wall_jump_delay"].activate()
        self.move_vector.y = -self.jump_height
        # small pixel adjustment for stick glitch
        self.hitbox_rect.bottom -= 1
 
    def wall_jump(self):
        """
        When the player object is on a wall and the jump key is pressed, the wall jump timer is activated to deny x direction input.
        It does the same jump height for the y vector while pushing the object in the opposite direction from the wall.
        """
        self.timers["wall_jump"].activate()
        self.move_vector.y = -self.jump_height
        self.dir_vector.x = 1 if self.on_surface["left"] else -1

    def wall_slide(self, dt):
        """Gets rid of the gravity influence on the player object to then slowly push the character downwards to represent slding."""
        self.move_vector.y = 0
        self.hitbox_rect.y += self.gravity_num / 10 * dt

    def move(self, dt):
        self.climb(dt)
        if self.climbing_active:
            self.collisons("y")
            self.update_rect()
            return

        self.gravity(dt)

        self.collisons("y")
        self.update_rect()

        if self.crouching and self.on_surface["floor"]:
            return

        if not self.on_surface["floor"] and any((self.on_surface["left"], self.on_surface["right"])) and self.move_vector.y > 0:
            self.wall_slide(dt)

        if not self.timers["dash"].active:
            self.x_move(dt)
        self.collisons("x")

        if self.dash_move(dt):
            self.collisons("x")
            self.collisons("y")
            self.update_rect()
            return
        
        if self.is_jumping:
            if self.on_surface["floor"]:
                self.jump()
            if not self.timers["wall_jump_delay"].active and any((self.on_surface["left"], self.on_surface["right"])):
                self.wall_jump()
            self.is_jumping = False 
        
        self.update_rect()

    def update_rect(self):
        """A custom updating func for the self.rect based on the hitbox rect to fix animations."""
        # Below adjusts the climb and wall animation to draw one more px over in the facing direction.
        if self.state == "climb" or self.state == "wall":
            if self.facing_left:
                self.rect.center = self.hitbox_rect.center - vector(1, 0)
            else: self.rect.center = self.hitbox_rect.center - vector(-1, 0)
        else: self.rect.center = self.hitbox_rect.center

    def collisons(self, direction):
        for sprite in self.collision_sprites:
            if self.hitbox_rect.colliderect(sprite.rect):
                if direction == "x":
                    if self.hitbox_rect.right >= sprite.rect.left and self.old_rect.right <= sprite.old_rect.left + 1: 
                        self.hitbox_rect.right = sprite.rect.left
                        self.timers["dash"].deactivate()
                    elif self.hitbox_rect.left <= sprite.rect.right and self.old_rect.left >= sprite.old_rect.right - 1: 
                        self.hitbox_rect.left = sprite.rect.right
                        self.timers["dash"].deactivate()
                else:
                    if self.hitbox_rect.bottom >= sprite.rect.top and self.old_rect.bottom <= sprite.rect.top + 1: 
                        self.hitbox_rect.bottom = sprite.rect.top
                        self.move_vector.y = 0
                        
                    elif self.hitbox_rect.top <= sprite.rect.bottom and self.old_rect.top >= sprite.old_rect.bottom - 1: 
                        self.hitbox_rect.top = sprite.rect.bottom
                        self.move_vector.y = 0
                        
    def update_timers(self):
        """Loops through the self.timers dictionary to update the time for them."""
        for timer in self.timers.values():
            timer.update()

    def now_state(self):
        wall = any((self.on_surface["right"], self.on_surface["left"]))
        if self.timers["dash"].active and not self.climbing and self.dir_vector != vector(0, 0):
            return "dash"
        if self.on_surface["floor"]:
            if wall and self.dir_vector.x != 0:
                return "push"
            if self.crouching:
                return "crouch"
            if self.on_surface["edge"]:
                return "balance"
            return "idle" if self.dir_vector.x == 0 else "run"
        if wall:
            if self.climbing and self.dir_vector.y < 0:
                return "climb"
            if self.on_surface["dangle"]:
                return "dangle"
            if self.move_vector.y >= 0:
                return "wall"   
        if self.move_vector.y < 0:
            return "jump"
        else:
            if self.embrace_active():
                return "embrace"
            else: return "fall"

    def is_touching(self, rect):
        return rect.collidelist(self.collide_rects) >= 0

    def contact(self):
        self.collide_rects = [sprite.rect for sprite in self.collision_sprites]
        

        floor_rect = pygame.Rect(self.hitbox_rect.bottomleft, (self.hitbox_rect.width, 2))
        left_rect = pygame.Rect((self.hitbox_rect.topleft + vector(-1, self.hitbox_rect.height / 3)), (1, self.hitbox_rect.height / 3))
        right_rect = pygame.Rect((self.hitbox_rect.topright + vector(0, self.hitbox_rect.height / 3)), (1, self.hitbox_rect.height / 3))

        if not self.facing_left:
            climb_rect = pygame.Rect((self.hitbox_rect.midright + vector(2, -4)), (1, 6))
        else: climb_rect = pygame.Rect((self.hitbox_rect.midleft + vector(-3, -4)), (1, 6))

        if not self.facing_left:
            edge_rect = pygame.Rect((self.hitbox_rect.bottomright), (2, 2))
        else: edge_rect = pygame.Rect((self.hitbox_rect.bottomleft + vector(-2, 0)), (2, 2))

        if not self.facing_left: 
            dangle_rect = pygame.Rect((self.hitbox_rect.topright + vector(0, (self.hitbox_rect.height / 1.8))), (1, 1))
        else: dangle_rect = pygame.Rect((self.hitbox_rect.topleft + vector(-1, (self.hitbox_rect.height / 1.8))), (1, 1))

        embrace_rect = pygame.Rect(self.hitbox_rect.center + vector(TILE_SIZE * 2, 0), (1, 1))

        self.on_surface["embrace"] = not self.is_touching(embrace_rect) and self.move_vector.y > 0
        self.on_surface["climb-mantle"] = not self.is_touching(climb_rect) and any((self.on_surface["left"], self.on_surface["right"])) and self.climbing_active
        self.on_surface["floor"] = self.is_touching(floor_rect) 
        self.on_surface["left"] = self.is_touching(left_rect)
        self.on_surface["right"] = self.is_touching(right_rect)
        if not self.is_touching(edge_rect) and self.is_touching(floor_rect) and not self.timers["balance_delay"].active:
            self.timers["balance_delay"].activate()  
        elif self.is_touching(edge_rect) >=0 and self.is_touching(floor_rect):
            self.timers["balance_delay"].deactivate()  
            self.on_surface['edge'] = False
        self.on_surface["dangle"] = not self.is_touching(dangle_rect)  and any((self.on_surface["left"], self.on_surface["right"]))

    def animate(self, dt):  
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

        if not self.climbing_active and not self.timers["dash"].active:
            if self.dir_vector.x == 1: self.facing_left = False
            elif self.dir_vector.x == -1: self.facing_left = True

        self.frame_index = self.frame_index + ANIMATION_INFO["player"][self.state][0] * dt
        frames = self.frames[self.state]
        if not ANIMATION_INFO["player"][self.state][1] and int(self.frame_index) >= len(frames):
            self.image = frames[-1]
        else: 
            self.image = frames[int(self.frame_index) % len(frames)]
        if not self.facing_left:
            self.image = pygame.transform.flip(self.image, True, False)

    def update(self, dt):
        self.old_rect = self.hitbox_rect.copy()
        self.update_timers()
        self.input()
        self.move(dt)
        self.contact()
        self.animate(dt)

            
