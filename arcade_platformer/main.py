"""
https://realpython.com/platformer-python-arcade/
"""

import arcade
import pathlib
import math

# Screen constants
SCREEN_WIDTH = 1520
SCREEN_HEIGHT = 900
SCREEN_TITLE = "Revenge of the Bowling Pins"

ASSETS_PATH = pathlib.Path(__file__).resolve().parent.parent / "assets"

MAP_SCALING = 1.0

# Player constants
GRAVITY = 1.0
PLAYER_START_X = 400
PLAYER_START_Y = 300
PLAYER_MOVE_SPEED = 10
PLAYER_JUMP_SPEED = 20

# Weapon constants
WEAPON_OFFSET_X = 60
WEAPON_OFFSET_Y = 10
WEAPON_SPEED = 20
WEAPON_DISTANCE = 500
WEAPON_POWER = 1

# Enemies constants
ENEMY_HEALTH_1 = 3
ENEMY_HEALTH_2 = 5
ENEMY_HEALTH_3 = 10

# Viewport margins
# how close to scroll viewport?
LEFT_VIEWPORT_MARGIN = SCREEN_WIDTH / 2.2
RIGHT_VIEWPORT_MARGIN = SCREEN_WIDTH / 1.8
TOP_VIEWPORT_MARGIN = SCREEN_HEIGHT / 3
BOTTOM_VIEWPORT_MARGIN = SCREEN_HEIGHT / 3.5


class PlatformerView(arcade.View):
    def __init__(self) -> None:
        super().__init__()

        self.enemies_list = arcade.SpriteList()
        self.all_sprites = arcade.SpriteList()

        # lists of sprites
        self.coins = None
        self.background = None
        self.walls = None
        self.ladders = None
        self.goals = None
        self.enemies = None
        self.moving_platforms = None
        self.gutters = None

        self.game_map = None

        self.scene = None

        # one sprite for player
        self.player = None
        self.weapon = None
        self.weapon_shooting = False

        # player movement key press state
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False

        # physics engine
        self.physics_engine = None

        # score ?
        # self.score = 0

        # initial level
        self.level = 1

        # death counter
        self.death_counter = 0

        # how many seconds have passed
        self.elapsed_time = 0

        # Load up our sounds here
        # self.coin_sound = arcade.load_sound(
        #     str(ASSETS_PATH / "sounds" / "coin.wav")
        # )
        # self.jump_sound = arcade.load_sound(
        #     str(ASSETS_PATH / "sounds" / "jump.wav")
        # )
        # self.victory_sound = arcade.load_sound(
        #     str(ASSETS_PATH / "sounds" / "victory.wav")
        # )

    def setup(self):
        """Sets up the game for the current level"""
        arcade.set_background_color(arcade.color.SKY_BLUE)
        map_name = f"platform_level_{self.level:02}.tmx"
        # map_name = "platform_level_02.tmx"
        map_path = ASSETS_PATH / map_name

        # layer names which must match from the Tiled map
        wall_layer = "ground"
        coin_layer = "coins"
        goal_layer = "goal"
        background_layer = "background"
        ladders_layer = "ladders"
        moving_platforms_layer = "moving_platforms"
        gutters_layer = "gutters"

        # load map
        self.game_map = arcade.load_tilemap(map_path, MAP_SCALING)

        self.scene = arcade.Scene.from_tilemap(self.game_map)

        # load layers
        # returns SpriteList populated with Sprite objects representing tiles in the layer
        # any custom properties defined such as point_value for coins are stored with the Sprite
        # in a dictionary called .properties
        self.background = self.scene[background_layer]
        self.goals = self.scene[goal_layer]
        self.walls = self.scene[wall_layer]
        self.ladders = self.scene[ladders_layer]
        self.coins = self.scene[coin_layer]
        self.gutters = self.scene[gutters_layer]
        if self.level > 1:
            self.moving_platforms = self.scene[moving_platforms_layer]

            # so that player can stand on the moving platforms even though they are separate from the walls
            for sprite in self.moving_platforms:
                self.walls.append(sprite)

        # set background color
        background_color = arcade.color.FRESH_AIR
        if self.game_map.background_color:
            background_color = self.game_map.background_color
        arcade.set_background_color(background_color)

        # self.map_width = (self.game_map.map_size.width - 1) * self.game_map.tile_size.width
        self.map_width = (self.game_map.width - 1) * self.game_map.tile_width

        # create player sprite if not already set up
        if not self.player:
            self.player = self.create_player_sprite()

        # move player sprite back to beginning
        self.player.center_x = PLAYER_START_X
        self.player.center_y = PLAYER_START_Y
        self.player.change_x = 0
        self.player.change_y = 0

        # create weapon sprite if not already set up
        if not self.weapon:
            self.weapon = self.create_weapon_sprite()
            
        self.weapon_firing_direction = arcade.FACE_RIGHT
        
        # move player sprite back to beginning
        self.weapon.center_x = PLAYER_START_X
        self.weapon.center_y = PLAYER_START_Y
        self.weapon.change_x = 0
        self.weapon.change_y = 0

        # set up enemies
        self.enemies = self.create_enemy_sprites()

        # reset viewport
        self.view_left = 0
        self.view_bottom = 0

        # load physics engine for this map
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.player,
            platforms=self.walls,
            gravity_constant=GRAVITY,
            ladders=self.ladders,
        )

    def create_weapon_sprite(self) -> arcade.Sprite:
        texture_path = ASSETS_PATH / "images" / "bowling_sprites"

        weapon = arcade.Sprite(scale=0.15)
        weapon.textures = [arcade.load_texture(texture_path / "pin_1.png"), arcade.load_texture(texture_path / "pin_3.png")]
        weapon.center_x = PLAYER_START_X + WEAPON_OFFSET_X
        weapon.center_y = PLAYER_START_Y - WEAPON_OFFSET_Y
        weapon.state = arcade.FACE_RIGHT
        weapon.texture = weapon.textures[0]
        return weapon

    def create_player_sprite(self) -> arcade.AnimatedWalkingSprite:
        # access path where player image is stored
        texture_path = ASSETS_PATH / "images" / "player"

        # walking, climbing, and standing textures textures
        walking_paths = [texture_path / "running" /
                         f"frame-{x}.png" for x in range(1, 7)]
        standing_path = [texture_path / "Idle" /
                         f"frame-{x}.png" for x in (1, 2)]

        # load them all
        walking_right_textures = [arcade.load_texture(
            texture) for texture in walking_paths]
        walking_left_textures = [arcade.load_texture(texture, mirrored=True) for texture in
                                 walking_paths]  # mirrored very helpful

        walking_up_textures = [arcade.load_texture(
            texture) for texture in walking_paths]
        walking_down_textures = [arcade.load_texture(
            texture) for texture in walking_paths]

        standing_right_textures = [arcade.load_texture(
            texture) for texture in standing_path]
        standing_left_textures = [arcade.load_texture(
            texture, mirrored=True) for texture in standing_path]

        # create player sprite
        player = arcade.AnimatedWalkingSprite(scale=0.2)

        # initialize respective textures
        player.stand_left_textures = standing_left_textures
        player.stand_right_textures = standing_right_textures
        player.walk_left_textures = walking_left_textures
        player.walk_right_textures = walking_right_textures
        player.walk_up_textures = walking_up_textures
        player.walk_down_textures = walking_down_textures

        # set player defaults
        player.center_x = PLAYER_START_X
        player.center_y = PLAYER_START_Y
        player.state = arcade.FACE_RIGHT

        # set the initial textures
        player.texture = player.stand_right_textures[0]

        return player

    def update_player_speed(self):

        # Calculate speed based on the keys pressed
        self.player.change_x = 0

        if self.up_pressed and not self.down_pressed:
            self.player.change_y = PLAYER_MOVE_SPEED
        elif self.down_pressed and not self.up_pressed:
            self.player.change_y = -PLAYER_MOVE_SPEED
        if self.left_pressed and not self.right_pressed:
            self.player.change_x = -PLAYER_MOVE_SPEED
        elif self.right_pressed and not self.left_pressed:
            self.player.change_x = PLAYER_MOVE_SPEED

    def on_key_press(self, key: int, modifiers: int):
        """Called whenever a key is pressed. """

        if key in [arcade.key.UP, arcade.key.W]:
            if self.physics_engine.is_on_ladder():
                self.up_pressed = True
                self.update_player_speed()
        elif key in [arcade.key.DOWN, arcade.key.S]:
            if self.physics_engine.is_on_ladder():
                self.down_pressed = True
                self.update_player_speed()
        elif key in [arcade.key.LEFT, arcade.key.A]:
            self.left_pressed = True
            self.update_player_speed()
        elif key in [arcade.key.RIGHT, arcade.key.D]:
            self.right_pressed = True
            self.update_player_speed()

        # jumping movement with check
        elif key in [arcade.key.SPACE]:
            if self.physics_engine.can_jump():
                self.player.change_y = PLAYER_JUMP_SPEED
                # arcade.play_sound(self.jump_sound)

        # Attack
        elif key in [arcade.key.J]:
            if self.weapon_shooting:
                self.weapon.angle = 0
                self.weapon.center_x = self.player.center_x + (WEAPON_OFFSET_X * (1 if self.player.state == arcade.FACE_RIGHT else -1))
                self.weapon.center_y = self.player.center_y - WEAPON_OFFSET_Y
                self.weapon_shooting = False
            self.weapon_shooting = True

        elif key in [arcade.key.ESCAPE, arcade.key.P]:
            pause = PauseView(self)
            self.window.show_view(pause)

    def on_key_release(self, key: int, modifiers: int):
        """Called when the user releases a key. """

        if key in [arcade.key.UP, arcade.key.W]:
            self.up_pressed = False
            self.update_player_speed()
        elif key in [arcade.key.DOWN, arcade.key.S]:
            self.down_pressed = False
            self.update_player_speed()
        elif key in [arcade.key.LEFT, arcade.key.A]:
            self.left_pressed = False
            self.update_player_speed()
        elif key in [arcade.key.RIGHT, arcade.key.D]:
            self.right_pressed = False
            self.update_player_speed()

    def on_update(self, delta_time: float):
        """Updates the position of all game objectsd
        Moving player and enemy sprites
        detecting collisions with enemies and collectibles
        updating scores
        animating sprites

        Arguments:
            delta_time {float} -- How much time since the last call
        """
        # order here is important
        # update player animation
        self.player.update_animation(delta_time)
        self.weapon.update_animation(delta_time)

        if self.weapon_shooting:
            # Move weapon in the direction player is facing
            if self.weapon_firing_direction == arcade.FACE_RIGHT:
                self.weapon.center_x += WEAPON_SPEED
                self.weapon.turn_right()
            else:
                self.weapon.center_x -= WEAPON_SPEED
                self.weapon.turn_left()

            # Check if weapon has reached max distance
            if abs(self.weapon.center_x - self.player.center_x) >= WEAPON_DISTANCE:
                self.weapon.angle = 0
                self.weapon.center_x = self.player.center_x + (WEAPON_OFFSET_X * (1 if self.player.state == arcade.FACE_RIGHT else -1))
                self.weapon.center_y = self.player.center_y - WEAPON_OFFSET_Y
                self.weapon_shooting = False

        else:
            # Move weapon with the player
            if self.player.change_x != 0:
                if self.player.state == arcade.FACE_RIGHT and not self.weapon_shooting:
                    self.weapon.center_x = self.player.center_x + WEAPON_OFFSET_X
                    self.weapon.texture =  self.weapon.textures[0]
                    self.weapon_firing_direction = arcade.FACE_RIGHT
                elif self.player.state == arcade.FACE_LEFT and not self.weapon_shooting:
                    self.weapon.center_x = self.player.center_x - WEAPON_OFFSET_X
                    self.weapon.texture =  self.weapon.textures[1]
                    self.weapon_firing_direction = arcade.FACE_LEFT
            self.weapon.center_y = self.player.center_y - WEAPON_OFFSET_Y

        self.weapon.update()        

        # update enemies
        self.enemies.update_animation(delta_time)
        for enemy in self.enemies:
            enemy.center_x += enemy.change_x
            enemy.angle += enemy.rotation_speed
            walls_hit = arcade.check_for_collision_with_list(
                sprite=enemy, sprite_list=self.walls)
            if walls_hit:
                enemy.change_x *= -1
                enemy.rotation_speed *= -1

        # update player movement based on physics engine
        self.physics_engine.update()

        # restrict user movement so they can't walk off screen
        if self.player.left < 0:
            self.player.left = 0

        self.elapsed_time += delta_time

        # check if we've picked up a coin
        # coins_hit = arcade.check_for_collision_with_list(sprite=self.player, sprite_list=self.coins)

        # for coin in coins_hit:
        #     self.score += int(coin.properties["point_value"])
        #     # arcade.play_sound(self.coin_sound)
        #     coin.remove_from_sprite_lists()

        # enemy collision
        enemies_hit = arcade.check_for_collision_with_list(
            sprite=self.player, sprite_list=self.enemies
        )

        if enemies_hit:
            self.death_counter += 1
            self.setup()
            # title_view = TitleView()
            # window.show_view(title_view)
            
        # weapon enemies conllision
        for enemy in self.enemies:    
            weapon_hit = arcade.check_for_collision(self.weapon, enemy)
            if weapon_hit:
                self.weapon.angle = 0
                self.weapon.center_x = self.player.center_x + (WEAPON_OFFSET_X * (1 if self.player.state == arcade.FACE_RIGHT else -1))
                self.weapon.center_y = self.player.center_y - WEAPON_OFFSET_Y
                self.weapon_shooting = False
                enemy.set_health(enemy.get_health() - WEAPON_POWER)
                if enemy.get_health() <= 0: 
                    enemy.remove_from_sprite_lists()
            
        # weapon wall collision
        for wall in self.walls:
            hit = arcade.check_for_collision(self.weapon, wall)
            if hit:
                self.weapon.angle = 0
                self.weapon.center_x = self.player.center_x + (WEAPON_OFFSET_X * (1 if self.player.state == arcade.FACE_RIGHT else -1))
                self.weapon.center_y = self.player.center_y - WEAPON_OFFSET_Y
                self.weapon_shooting = False
            
        # now check if we're at goal
        goals_hit = arcade.check_for_collision_with_list(
            sprite=self.player, sprite_list=self.goals)
        if goals_hit:
            # self.victory_sound.play()
            self.level += 1
            if self.level == 5:
                arcade.set_viewport(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT)
                completion_view = CompletionView(
                    int(self.elapsed_time), self.death_counter)
                self.window.show_view(completion_view)
            else:
                self.setup()

        gutters_hit = arcade.check_for_collision_with_list(
            sprite=self.player, sprite_list=self.gutters)
        if gutters_hit:
            self.death_counter += 1
            self.setup()

        # set viewport, scrolling if necessary
        self.scroll_viewport()

    def on_draw(self):
        arcade.start_render()

        # Draw all the sprites
        self.background.draw()
        self.walls.draw()
        # self.coins.draw()
        self.goals.draw()
        self.ladders.draw()
        self.enemies.draw()
        self.weapon.draw()
        self.player.draw()
        self.gutters.draw()

        arcade.draw_text(
            f"Deaths: {self.death_counter}",
            start_x=self.view_left + 10,
            start_y=self.view_bottom + SCREEN_HEIGHT - 30,
            color=arcade.color.BLACK,
            font_size=20,
        )

        # Display timer
        arcade.draw_text(
            f"Time: {int(self.elapsed_time)}",
            start_x=self.view_left + 10,
            start_y=self.view_bottom + SCREEN_HEIGHT - 60,  # Adjusted position
            color=arcade.color.BLACK,
            font_size=20,
        )

        if self.level == 1:
            arcade.draw_text(
                "Bowling World!!",
                start_x=3000,
                start_y=800,
                width=40,
                color=(206, 96, 188),  # RGB color tuple
                font_size=80,
                align="center"
            )

        if self.level == 3:
            arcade.draw_text(
                "Use the bowling pin (J key) to attack the bowling balls!",
                start_x=50,
                start_y=800,
                width=300,
                color=(206, 96, 188),  # RGB color tuple
                font_size=40,
                align="center"
            )

    def scroll_viewport(self):
        # left boundary
        left_boundary = self.view_left + LEFT_VIEWPORT_MARGIN

        # are we left of this boundary? then scroll left
        if self.player.left < left_boundary:
            self.view_left -= left_boundary - self.player.left
            # but don't scroll past left edge of map
            if self.view_left < 0:
                self.view_left = 0

        # right boundary
        right_boundary = self.view_left + SCREEN_WIDTH - RIGHT_VIEWPORT_MARGIN

        # are we right of this boundary? then scroll right
        if self.player.right > right_boundary:
            self.view_left += self.player.right - right_boundary
            # dont scroll past right edge of map
            if self.view_left > self.map_width - SCREEN_WIDTH:
                self.view_left = self.map_width - SCREEN_WIDTH

        # top boundary scroll up
        top_boundary = self.view_bottom + SCREEN_HEIGHT - TOP_VIEWPORT_MARGIN
        if self.player.top > top_boundary:
            self.view_bottom += self.player.top - top_boundary

        # bottom boundary scroll down
        bottom_boundary = self.view_bottom + BOTTOM_VIEWPORT_MARGIN
        if self.player.bottom < bottom_boundary:
            self.view_bottom -= bottom_boundary - self.player.bottom

        # only scroll to integers otherwise weird pixels dont line up on screen
        self.view_bottom = int(self.view_bottom)
        self.view_left = int(self.view_left)

        # do scrolling
        arcade.set_viewport(
            left=self.view_left,
            right=SCREEN_WIDTH + self.view_left,
            bottom=self.view_bottom,
            top=SCREEN_HEIGHT + self.view_bottom
        )

    def create_enemy_sprites(self):
        enemies = arcade.SpriteList()

        if self.level == 2:
            enemies.append(Enemy(2000, 320, 0.8))
            enemies.append(Enemy(3000, 320, 0.8))

        if self.level == 3:
            enemies.append(Enemy2(500, 1385, 1.3))
            enemies.append(Enemy2(2000, 360, 1.3))
            enemies.append(Enemy2(2500, 1385, 1.3))

        if self.level == 4:
            enemies.append(Enemy3(2800, 420, 1.8))
            enemies.append(Enemy3(2000, 420, 1.8))

        return enemies


class TitleView(arcade.View):
    def __init__(self):
        super().__init__()

        # use title image path and load it
        title_image_path = ASSETS_PATH / "images" / "bowling_sprites" / "bowling-background.png"
        self.title_image = arcade.load_texture(title_image_path)

        # set display timer
        self.display_timer = 3.0

        # are we showing instructions?
        self.show_instructions = False

    def on_show(self):
        arcade.set_viewport(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT)

    def on_update(self, delta_time: float):
        self.display_timer -= delta_time
        if self.display_timer < 0:
            # toggle showing instructions
            self.show_instructions = not self.show_instructions
            # reset timer so instructions flash slowly
            self.display_timer = 1.0

    def on_draw(self):
        arcade.start_render()

        arcade.draw_texture_rectangle(
            center_x=SCREEN_WIDTH / 2,
            center_y=SCREEN_HEIGHT / 2,
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            texture=self.title_image,
        )

        arcade.draw_text(
            "The Revenge of the Bowling Pins",
            start_x=100,
            start_y=220,
            color=arcade.color.WHITE_SMOKE,
            font_size=50,
            bold=True
        )

        arcade.draw_text(
            "CS122 Andrew Vu Jooyul Yoon",
            start_x=1350,
            start_y=80,
            color=arcade.color.WHITE_SMOKE,
            font_size=20,
            multiline=True,
            width=150
        )
            
        # should we show instructions?
        if self.show_instructions:
            arcade.draw_text(
                "Enter to Start  |  Press I for Instructions",
                start_x=100,
                start_y=120,
                color=arcade.color.WHITE_SMOKE,
                font_size=30
            )

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.RETURN:
            game_view = PlatformerView()
            game_view.setup()
            self.window.show_view(game_view)
        elif key == arcade.key.I:
            instructions_view = InstructionsView()
            self.window.show_view(instructions_view)


class InstructionsView(arcade.View):
    def __init__(self):
        super().__init__()

        # instructions image and load it
        instructions_image_path = (
            ASSETS_PATH / "images" / "instructions_image.png"
        )
        self.instructions_image = arcade.load_texture(instructions_image_path)

    def on_draw(self):
        arcade.start_render()

        arcade.draw_texture_rectangle(
            center_x=SCREEN_WIDTH / 2,
            center_y=SCREEN_HEIGHT / 2,
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            texture=self.instructions_image,
        )

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.RETURN:
            game_view = PlatformerView()
            game_view.setup()
            self.window.show_view(game_view)

        elif key == arcade.key.ESCAPE:
            title_view = TitleView()
            self.window.show_view(title_view)


# could technically do this for the instructions as well
class PauseView(arcade.View):
    def __init__(self, game_view: arcade.View):
        super().__init__()
        self.game_view = game_view
        self.fill_color = arcade.make_transparent_color(
            arcade.color.WHITE, transparency=150
        )

    def on_draw(self):
        """draw underlying screen, blurred, then paused text"""
        # draw underlying view
        self.game_view.on_draw()

        # now create filled rect that covers current viewport
        # we get viewport size from game view
        arcade.draw_lrtb_rectangle_filled(
            left=self.game_view.view_left,
            right=self.game_view.view_left + SCREEN_WIDTH,
            top=self.game_view.view_bottom + SCREEN_HEIGHT,
            bottom=self.game_view.view_bottom,
            color=self.fill_color,
        )

        # now show pause text
        arcade.draw_text(
            "PAUSED - ESC/P TO CONTINUE",
            start_x=self.game_view.view_left + 180,
            start_y=self.game_view.view_bottom + 300,
            color=arcade.color.INDIGO,
            font_size=40,
        )

    def on_key_press(self, key: int, modifiers: int):
        if key in [arcade.key.ESCAPE, arcade.key.P]:
            # since you saved the game view, you can reactivate the game where it left off
            # rather than creating a new PlatformerView
            self.window.show_view(self.game_view)


class CompletionView(arcade.View):
    def __init__(self, completion_time: int, death_count: int):
        super().__init__()
        self.completion_time = completion_time
        self.death_count = death_count

    def on_draw(self):
        arcade.start_render()

        arcade.draw_text(
            f"Congratulations! You beat the game in {self.completion_time} seconds "
            f"with {self.death_count} deaths.",
            start_x=1600,
            start_y=500,
            color=arcade.color.BLACK,
            font_size=36,
            width=800
        )

        arcade.draw_text(
            f"Thanks for playing! Press R to restart.",
            start_x=1900,
            start_y=400,
            color=arcade.color.BLACK,
            font_size=36,
            width=800
        )

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.R:
            title_view = TitleView()
            self.window.show_view(title_view)


# blue bowling ball
class Enemy(arcade.AnimatedWalkingSprite):
    """enemy sprite with basic walking movement"""

    def __init__(self, pos_x: int, pos_y: int, scale: float):
        super().__init__(center_x=pos_x, center_y=pos_y, scale=scale)
        
        # set health
        self.health = ENEMY_HEALTH_1
        
        # enemy image storage location
        texture_path = ASSETS_PATH / "images" / "enemies"

        # set up appropriate textures
        walking_texture_path = [
            texture_path / "cyan_bb.png",
        ]
        standing_texture_path = texture_path / "cyan_bb.png"

        # load all textures
        self.walk_left_textures = [
            arcade.load_texture(texture) for texture in walking_texture_path
        ]

        self.walk_right_textures = [
            arcade.load_texture(texture, mirrored=True) for texture in walking_texture_path
        ]

        self.stand_left_textures = [
            arcade.load_texture(standing_texture_path, mirrored=True)
        ]

        self.stand_right_textures = [
            arcade.load_texture(standing_texture_path)
        ]

        # set enemy defaults
        self.state = arcade.FACE_LEFT
        self.change_x -= (PLAYER_MOVE_SPEED // 2)

        # set initial texture
        self.texture = self.stand_left_textures[0]

        # set rotation speed for bowling ball
        self.rotation_speed = 5
    
    def get_health(self):
        return self.health

    def set_health(self, health):
        self.health = health


# yellow bowling ball
class Enemy2(arcade.AnimatedWalkingSprite):
    """enemy sprite with basic walking movement"""

    def __init__(self, pos_x: int, pos_y: int, scale: float):
        super().__init__(center_x=pos_x, center_y=pos_y, scale=scale)
        
        # set health
        self.health = ENEMY_HEALTH_2
        
        # enemy image storage location
        texture_path = ASSETS_PATH / "images" / "enemies"

        # set up appropriate textures
        walking_texture_path = [
            texture_path / "yellow_bb.png",
        ]
        standing_texture_path = texture_path / "yellow_bb.png"

        # load all textures
        self.walk_left_textures = [
            arcade.load_texture(texture) for texture in walking_texture_path
        ]

        self.walk_right_textures = [
            arcade.load_texture(texture, mirrored=True) for texture in walking_texture_path
        ]

        self.stand_left_textures = [
            arcade.load_texture(standing_texture_path, mirrored=True)
        ]

        self.stand_right_textures = [
            arcade.load_texture(standing_texture_path)
        ]

        # set enemy defaults
        self.state = arcade.FACE_LEFT
        self.change_x -= (PLAYER_MOVE_SPEED // 2)

        # set initial texture
        self.texture = self.stand_left_textures[0]

        # set rotation speed for bowling ball
        self.rotation_speed = 5
    
    def get_health(self):
        return self.health

    def set_health(self, health):
        self.health = health


# magenta (king) bowling ball
class Enemy3(arcade.AnimatedWalkingSprite):
    """enemy sprite with basic walking movement"""

    def __init__(self, pos_x: int, pos_y: int, scale: float):
        super().__init__(center_x=pos_x, center_y=pos_y, scale=scale)
        
        # set health
        self.health = ENEMY_HEALTH_3
        
        # enemy image storage location
        texture_path = ASSETS_PATH / "images" / "enemies"

        # set up appropriate textures
        walking_texture_path = [
            texture_path / "magenta_crown_bb.png",
        ]
        standing_texture_path = texture_path / "magenta_crown_bb.png"

        # load all textures
        self.walk_left_textures = [
            arcade.load_texture(texture) for texture in walking_texture_path
        ]

        self.walk_right_textures = [
            arcade.load_texture(texture, mirrored=True) for texture in walking_texture_path
        ]

        self.stand_left_textures = [
            arcade.load_texture(standing_texture_path, mirrored=True)
        ]

        self.stand_right_textures = [
            arcade.load_texture(standing_texture_path)
        ]

        # set enemy defaults
        self.state = arcade.FACE_LEFT
        self.change_x -= (PLAYER_MOVE_SPEED // 2)

        # set initial texture
        self.texture = self.stand_left_textures[0]

        # set rotation speed for bowling ball
        self.rotation_speed = 5
    
    def get_health(self):
        return self.health

    def set_health(self, health):
        self.health = health


if __name__ == "__main__":
    window = arcade.Window(
        width=SCREEN_WIDTH, height=SCREEN_HEIGHT, title=SCREEN_TITLE)
    # platform_view = PlatformerView()
    # platform_view.setup()
    title_screen = TitleView()
    window.show_view(title_screen)  # shows the title view on the window
    arcade.run()
