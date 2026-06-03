class Entity:
    def __init__(self, name, health, damage):
        self.name = name
        self._health = health
        self._damage = damage
        self.max_health = health


    @property
    def health(self):
        return self._health

    @property
    def damage(self):
        return self._damage
    
    @damage.setter
    def damage(self, value):
        self._damage = value

    @health.setter
    def health(self, value):
        was_alive = self._health > 0
        self._health = min(max(value, 0), self.max_health)
    
        if was_alive and self.health == 0:
            print(f"{self.name} died!")

    def attack(self, entity):
        print(f"{self.name} attacked {entity.name} for {self.damage} damage")
        entity.take_damage(self.damage)

    def take_damage(self, amount):
        print(f"{self.name} lost {amount} hp")
        self.health -= amount

    @staticmethod
    def battlecry():
        print("jf*#$DF93")

class Hero(Entity):
    pass

class Monster(Entity):
    global_damage_multiplier = 1
    global_multiplier_cap = 5
    def __init__(self, name, health, damage):
       super().__init__(name, health, damage)

    @property
    def damage(self):
        return self._damage * self.global_damage_multiplier

    @classmethod
    def modify_damage(cls, amount):
        previous_value = cls.global_damage_multiplier
        cls.global_damage_multiplier = min(max(amount, 0), cls.global_damage_multiplier)
        if previous_value != cls.global_damage_multiplier:
            decision = "increased" if cls.global_damage_multiplier > previous_value else "decreased" 
            print(f"Monster's damage has been {decision}".upper())

linc = Hero("Linc", 150, 45)
monster = Monster("Monster", 100, 10)


# // Test
linc.attack(monster)


linc.attack(monster)

monster.attack(linc)
Monster.modify_damage(2)
monster.attack(linc)

linc.attack(monster)

# // staticmethod
linc.battlecry()



