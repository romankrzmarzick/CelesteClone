from settings import * 
from track_time import *

class Player(pygame.sprite.Sprite):
    FRAME_DURATION = {
            "idle" : 5,
            "run" : 12,
            "crouch" : 25,
            "push" : 10,
            "climb" : 17,
            "balance" : 6,
            "jump" : 1,
            "wall" : 1,
            "fall" : 3,
            "embrace" : 3,
            "dash" : 15,
            "fall-ground" : 35,
            "ground-jump" : 25,
            "death" :  20,
            "dangle" : 7,
    }
    DOES_LOOP = {
            "idle" : True,
            "run" : True,
            "crouch" : False,
            "push" : True,
            "jump" : False,
            "wall" : False,
            "fall" : False,
            "embrace" : False,
            "climb" : True,
            "balance" : True,
            "dash" : False,
            "fall-ground" : False,
            "ground-jump" : False,
            "death" :  False,
            "dangle" : True,
        }
    TRANSITIONS = {
        ("embrace", "idle") : "fall-ground",
        ("embrace", "run") : "fall-ground",
        ("fall", "idle") : "fall-ground",
        ("fall", "run") : "fall-ground",
        ("idle", "jump") : "ground-jump",
        ("run", "jump") : "ground-jump",
    }

    def __init__(self, pos, groups, collision_sprites, frames):
        # // general setup
        super().__init__(groups)

        # // image
        self.frames, self.frame_index = frames, 0
        self.state, self.doing_state, self.facing_left = "idle", "idle", True
        self.image = self.frames[self.state][self.frame_index]
        

        # // movement
        self.move_vector = Vector2()
        self.gravity_vector = Vector2()
        self.x_speed = 70
       
        self.jump = False
        self.jump_height = 155
        self.gravity = 500
        self.max_fall_speed = 175
       
        self.crouching = False
        self.embrace = False
        self.dash_speed = 130
        self.can_dash = True
        self.climbing_speed = 50
        self.climbing_active = False

        # // collision
        self.collision_sprites = collision_sprites
        self.rect = self.image.get_frect(center=pos)
        self.hitbox_rect = self.rect.inflate((-4, 0))
        self.old_rect = self.hitbox_rect.copy()
        self.on_surface = {
            "floor" : False, 
            "left" : False,
            "right" : False,
            "edge" : False,
            "dangle" : False,
        }

        # // timers
        self.timers = {
            "balance_delay" : Timer(1200, func=self.balance_animation_delay),
            "wall_jump" : Timer(175),
            "wall_jump_delay" : Timer(250),
            "dash" : Timer(300),
        }
    
    def dash_move(self, dt):
        if self.on_surface["floor"]:
            self.can_dash = True

        if self.timers["dash"].active and self.move_vector != Vector2(0, 0):
            self.old_dir.normalize() if self.old_dir else self.old_dir
            self.can_dash = False
            self.gravity_vector.y = 0
            self.hitbox_rect.center += (self.dash_speed * self.old_dir) * dt
            return True
        return False

    def input(self):
        input_dir = Vector2()
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
                self.move_vector = input_dir


        if keys[pygame.K_UP] and not self.crouching:
            self.jump = True

        if keys[pygame.K_DOWN]:
            self.crouching = True
        else: self.crouching = False
        
        if keys[pygame.K_x]:
            if self.can_dash:
                self.timers["dash"].activate()
                self.old_dir = input_dir

        if keys[pygame.K_SPACE]:
            self.climbing = True
        else: self.climbing = False

    def balance_animation_delay(self):
        self.on_surface["edge"] = True

    def climb(self, dt):
        if self.climbing and not self.on_surface["floor"] and any((self.on_surface["left"], self.on_surface["right"])):
            self.gravity_vector.y = 0
            self.hitbox_rect.y += (self.climbing_speed * self.move_vector.y) * dt
            self.climbing_active = True
        else: self.climbing_active = False
    
    def move(self, dt):
        
        self.climb(dt)
        if self.climbing_active:
            self.collisons("y")
            self.update_rect()
            return

        self.gravity_vector.y += self.gravity / 2 * dt 
        self.gravity_vector.y = min(self.max_fall_speed, self.gravity_vector.y)
        self.hitbox_rect.y += self.gravity_vector.y * dt
        self.gravity_vector.y += self.gravity / 2 * dt
        self.collisons("y")
        self.update_rect()

        if self.crouching and self.on_surface["floor"]:
            return

        if not self.on_surface["floor"] and any((self.on_surface["left"], self.on_surface["right"])) and self.gravity_vector.y > 0:
            self.gravity_vector.y = 0
            self.hitbox_rect.y += self.gravity / 10 * dt

        if not self.timers["dash"].active:
            self.hitbox_rect.x += self.move_vector.x * self.x_speed * dt
        self.collisons("x")

        if self.dash_move(dt):
            self.collisons("x")
            self.collisons("y")
            return

        # // jump 
        if self.jump:
            if self.on_surface["floor"]:
                self.timers["wall_jump_delay"].activate()
                self.gravity_vector.y = -self.jump_height
                self.hitbox_rect.bottom -= 1
 
            if not self.timers["wall_jump_delay"].active:
                if any((self.on_surface["left"], self.on_surface["right"])):
                    self.timers["wall_jump"].activate()
                    self.gravity_vector.y = -self.jump_height
                    self.move_vector.x = 1 if self.on_surface["left"] else -1
            self.jump = False 


        self.update_rect()

    def update_rect(self):
        if self.state == "climb" or self.state == "wall":
            if self.facing_left:
                self.rect.center = self.hitbox_rect.center - Vector2(1, 0)
            else: self.rect.center = self.hitbox_rect.center - Vector2(-1, 0)
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
                        self.gravity_vector.y = 0
                        
                    elif self.hitbox_rect.top <= sprite.rect.bottom and self.old_rect.top >= sprite.old_rect.bottom - 1: 
                        self.hitbox_rect.top = sprite.rect.bottom
                        self.gravity_vector.y = 0
                        
    def update_timers(self):
        for timer in self.timers.values():
            timer.update()

    def now_state(self):
        wall = any((self.on_surface["right"], self.on_surface["left"]))
        if self.timers["dash"].active and not self.climbing and self.move_vector != Vector2(0, 0):
            return "dash"
        if self.on_surface["floor"]:
            if wall and self.move_vector.x != 0:
                return "push"
            if self.crouching:
                return "crouch"
            if self.on_surface["edge"]:
                return "balance"
            return "idle" if self.move_vector.x == 0 else "run"
        if wall:
            if self.climbing and self.move_vector.y < 0:
                return "climb"
            if self.on_surface["dangle"]:
                return "dangle"
            return "wall"   
        return "jump" if self.gravity_vector.y < 0 else "fall"

    def close_rects(self, pos_1, pos_2):
        pos_1 = Vector2(pos_1)
        pos_2 = Vector2(pos_2)
        if pos_1.distance_squared_to(pos_2) <= 300:
            return True
        return False


    def contact(self):
        floor_rect = pygame.Rect(self.hitbox_rect.bottomleft, (self.hitbox_rect.width, 2))
        left_rect = pygame.Rect((self.hitbox_rect.topleft + Vector2(-1, self.hitbox_rect.height / 3)), (1, self.hitbox_rect.height / 3))
        right_rect = pygame.Rect((self.hitbox_rect.topright + Vector2(0, self.hitbox_rect.height / 3)), (1, self.hitbox_rect.height / 3))
        
        if not self.facing_left:
            edge_rect = pygame.Rect((self.hitbox_rect.bottomright), (2, 2))
        else: edge_rect = pygame.Rect((self.hitbox_rect.bottomleft + Vector2(-2, 0)), (2, 2))

        if not self.facing_left: 
            dangle_rect = pygame.Rect((self.hitbox_rect.topright + Vector2(0, (self.hitbox_rect.height / 2) + 1.5)), (1, 1))
        else: dangle_rect = pygame.Rect((self.hitbox_rect.topleft + Vector2(-1, (self.hitbox_rect.height / 2) + 1.5)), (1, 1))



        
        collide_rects = [sprite.rect for sprite in self.collision_sprites if self.close_rects(self.rect.center, sprite.rect.center) ]

        



        self.on_surface["floor"] = True if floor_rect.collidelist(collide_rects) >=0 else False
        self.on_surface["left"] = True if left_rect.collidelist(collide_rects) >=0 else False
        self.on_surface["right"] = True if right_rect.collidelist(collide_rects) >=0 else False


        if not edge_rect.collidelist(collide_rects) >=0 and floor_rect.collidelist(collide_rects) >=0 and not self.timers["balance_delay"].active:
            self.timers["balance_delay"].activate()  
        elif edge_rect.collidelist(collide_rects) >=0 and floor_rect.collidelist(collide_rects) >=0:
            self.timers["balance_delay"].deactivate()  
            self.on_surface['edge'] = False

        
        self.on_surface["dangle"] = True if not dangle_rect.collidelist(collide_rects) >=0  and any((self.on_surface["left"], self.on_surface["right"])) else False
        
    def animate(self, dt):  
        now = self.now_state()
        transitional_clips = self.TRANSITIONS.values()
        transition_playing = self.state in transitional_clips 
        clip_finished = int(self.frame_index) >= len(self.frames[self.state])
        clip_in_progress = transition_playing and not clip_finished
        
        if not clip_in_progress:
            state = self.TRANSITIONS.get((self.doing_state, now), now)
            if state != self.state:
                self.state = state
                self.frame_index = 0
            self.doing_state = now

        if not self.climbing_active:
            if self.move_vector.x == 1: self.facing_left = False
            elif self.move_vector.x == -1: self.facing_left = True


        self.frame_index = self.frame_index + self.FRAME_DURATION[self.state] * dt
        frames = self.frames[self.state]
        if not self.DOES_LOOP[self.state] and int(self.frame_index) >= len(frames):
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
