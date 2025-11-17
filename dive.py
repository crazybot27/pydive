import pygame as pg
from pygame.math import Vector2
import random
import math
import pickle

DISPLAY_SIZE = (1080, 720)
DISPLAY_WIDTH, DISPLAY_HEIGHT = DISPLAY_SIZE
fps = 60

# keybinds, change these if you want
KEYBINDS = {"up": {pg.K_w, pg.K_UP}, 
            "left": {pg.K_a, pg.K_LEFT}, 
            "down": {pg.K_s, pg.K_DOWN}, 
            "right": {pg.K_d, pg.K_RIGHT},
            "restart": {pg.K_y},
            }

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

BG_COL = pg.Color(127, 127, 127)
FG_COL = pg.Color(91, 91, 91)
EMPTY_TILE_COL = pg.Color(63, 63, 63)
BLACK = pg.Color(0, 0, 0)
WHITE = pg.Color(255, 255, 255)

PATH = '\\'.join(__file__.split(sep='\\')[:-1])+'\\'

# thx alex
PRIMES = [7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 
    53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 
    131, 137, 139, 149, 151, 157, 163, 167, 173, 179, 181, 191, 193, 197,
    199, 211, 223, 227, 229, 233, 239, 241, 251, 257, 263, 269, 271, 277,
    281, 283, 293, 307, 311, 313, 317, 331, 337, 347, 349, 353, 359, 367]

GAMEMODE_DESCRIPTIONS = ["pydive (in development)", "classic dive", "permanent seeds", "2, 3, 5, 7 only"]
RESET_QUIPS = ["reset profile", "are you sure?", "you'll lose everything.", "there's no going back."] + [f"click {i} time{"s" if i!=1 else ""} to reset" for i in range(5, 0, -1)]

class Board:
    
    def __init__(self, width, height, mode=1):

        # basic variables
        self.width = width
        self.height = height
        self.mode = mode
        self.game_over = False

        self.tiles = [[None for i in range(self.height)] for j in range(self.width)]

        # "fake" tiles for animation
        # each anim_tile is a tuple containing
        # (start pos, start tile, end pos, end tile)
        self.anim_tiles = []

        # seeds
        # you already know what seeds are
        self.seeds = []
        self.all_seeds = []

        # "fake" seeds for animation
        # (seed, start index, end index)
        self.anim_seeds = []

        self.score = 0
        self.anim_score = 0

        # savescum prevention
        self.tainted = False

    def setup(self):
        if self.mode == 0:
            self.seeds = [2]
        elif self.mode == 1:
            self.seeds = [2]
        elif self.mode == 2:
            self.seeds = [2]
        elif self.mode == 3:
            self.seeds = [2,3,5,7]
        self.all_seeds = [x for x in self.seeds]
        self.spawn_tiles(2)

    # check if a new tile unlocks any seeds
    # returns the new seed, or None if there is no new seed
    def check_for_new_seed(self, new_tile):

        # nope, not dealing with you.
        if new_tile == 0 or new_tile == None:
            return None
        
        # set of potential new seeds
        potentials = {abs(new_tile)}
        smallest = abs(new_tile)

        while len(potentials) > 0:

            # take a potential seed
            test = potentials.pop()

            # divide it by each of the existing seeds
            for seed in self.seeds:
                if test % seed == 0:

                    # if the result is 1, no new seed
                    if test == seed or test == -seed:
                        return None
                    
                    # otherwise, add it to the set
                    potentials.add(test//seed)

            # keep track of the smallest seed
            if smallest > test:
                smallest = test
        
        return smallest
    
    def remove_seeds(self):

        removed_seeds = []
        for seed in self.seeds:
            remove = True
            for i in range(self.width):
                for j in range(self.height):
                    if self.tiles[i][j] == None or self.tiles[i][j] == "rock":
                        continue
                    if self.tiles[i][j] % seed == 0:
                        remove = False
            if remove:
                # Score for removing a seed
                self.score += seed
                removed_seeds.append(seed)
        
        self.seeds = [i for i in self.seeds if i not in removed_seeds]

    # check whether 
    def check_for_game_over(self):

        # if any tiles are empty, game is not over
        for i in range(self.width):
            for j in range(self.height):
                if self.tiles[i][j] == None:
                    return
                
        # if any two adjacent tiles are mergeable, game is not over
        for i in range(self.width):
            for j in range(self.height-1):
                if check_merge(self.tiles[i][j], self.tiles[i][j+1]) != None:
                    return
        for i in range(self.width-1):
            for j in range(self.height):
                if check_merge(self.tiles[i][j], self.tiles[i+1][j]) != None:
                    return
        
        self.game_over = True
    
    # spawn tiles in empty tiles
    def spawn_tiles(self, count):

        if len(self.seeds) == 0:
            return

        # find all empty tiles
        possible_positions = []

        for i in range(self.width):
            for j in range(self.height):

                if self.tiles[i][j] == None:
                    possible_positions.append((i, j))
        
        if len(possible_positions) == 0:
            return
        
        # add tiles randomly from the list of seeds
        for n in range(min(len(possible_positions), count)): 

            position = random.choice(possible_positions)
            tile = random.choice(self.seeds)

            self.anim_tiles.append((position, None, position, tile))
            self.tiles[position[0]][position[1]] = tile

            possible_positions.remove(position)

    # slide all tiles in a single direction, merging where possible
    # returns list of all newly merged tiles
    def slide_and_merge_tiles(self, dx, dy):
        
        # loop in the opposite direction of movement
        if dx > 0:
            irange = range(self.width-1, -1, -1)
        else:
            irange = range(self.width)

        if dy > 0:
            jrange = range(self.height-1, -1, -1)
        else:
            jrange = range(self.height)

        merged_tiles = []
        new_tiles = []
        move_worked = False
        for i in irange:
            for j in jrange:

                # don't care about empty tiles
                if self.tiles[i][j] == None:
                    continue

                if self.tiles[i][j] == "rock":
                    self.anim_tiles.append(((i, j), self.tiles[i][j], (i, j), self.tiles[i][j]))
                    continue

                # check tiles in the direction of motion until we either hit the wall or another tile
                x = i
                y = j
                while x+dx >= 0 and x+dx <= self.width-1 and y+dy >= 0 and y+dy <= self.height-1 and self.tiles[x+dx][y+dy] == None:
                    x += dx
                    y += dy
                
                # if we aren't on the edge, that means we were stopped by a tile
                # but we can't merge with a tile that already merged, so that's just as good as an edge
                if x+dx >= 0 and x+dx <= self.width-1 and y+dy >= 0 and y+dy <= self.height-1 and not (x+dx, y+dy) in merged_tiles: 
                    
                    # check if the tiles are mergeable
                    new_tile = check_merge(self.tiles[i][j], self.tiles[x+dx][y+dy])

                    if new_tile != None:
                        
                        # merged tiles can't merge again
                        merged_tiles.append((x+dx, y+dy))
                        new_tiles.append(new_tile)

                        # add score
                        self.score += min(self.tiles[x+dx][y+dy], self.tiles[i][j])
                        
                        # add merge animation
                        self.anim_tiles.append(((i, j), self.tiles[i][j], (x+dx, y+dy), new_tile))

                        # merge tiles
                        self.tiles[x+dx][y+dy] = new_tile
                        self.tiles[i][j] = None

                        move_worked = True
                        continue
                
                # check if the tile moved
                if x != i or y != j:
                    # move the tile
                    self.tiles[x][y] = self.tiles[i][j]
                    self.tiles[i][j] = None
                    move_worked = True

                # add animation
                self.anim_tiles.append(((i, j), self.tiles[x][y], (x, y), self.tiles[x][y]))

        return new_tiles if move_worked else None
    
    # perform one full move of the game
    # returns whether or not the move was successful
    def move(self, direction):

        if self.game_over:
            return False
        
        self.anim_tiles = []
        self.anim_score = self.score

        if direction == "right":
            new_tiles = self.slide_and_merge_tiles(1, 0)
        elif direction == "down":
            new_tiles = self.slide_and_merge_tiles(0, 1)
        elif direction == "left":
            new_tiles = self.slide_and_merge_tiles(-1, 0)
        elif direction == "up":
            new_tiles = self.slide_and_merge_tiles(0, -1)
        else:
            return False
        
        if new_tiles == None:
            return False
        
        # do seed math
        if self.mode == 0 or self.mode == 1 or self.mode == 2:

            self.anim_seeds = []
            old_seeds = [x for x in self.seeds]

            # find and add new seeds
            new_seeds = list(set([self.check_for_new_seed(i) for i in new_tiles]))
            if None in new_seeds:
                new_seeds.remove(None)
            new_seeds.sort()
            self.seeds += new_seeds

            # remove old seeds
            if self.mode == 0 or self.mode == 1:

                self.remove_seeds()

            # seed animation
            for i, seed in enumerate(old_seeds):
                if seed in self.seeds:
                    self.anim_seeds.append((seed, i, self.seeds.index(seed)))
                else:
                    self.anim_seeds.append((seed, i, None))
            
            for i, seed in enumerate(self.seeds):
                if seed not in self.all_seeds:
                    self.all_seeds.append(seed)
                if seed not in old_seeds:
                    self.anim_seeds.append((seed, None, i))
        
        else:

            self.anim_seeds = [(seed, i, i) for i, seed in enumerate(self.seeds)]

        # spawn a new tile
        self.spawn_tiles(1)

        self.check_for_game_over()
        if self.game_over:
            self.all_seeds.sort()
        
        return True
    
    def display_seed_list(self, seed_size, border, columns, scroll, anim_timer):

        if anim_timer < 1.0:
            rows = math.ceil(max(len([1 for x in self.anim_seeds if x[1] != None]),len([1 for x in self.anim_seeds if x[2] != None]))/float(columns))
        elif self.game_over:
            rows = math.ceil(len(self.all_seeds)/float(columns))
        else:
            rows = math.ceil(len(self.seeds)/float(columns))

        s = pg.Surface((get_grid_width(seed_size, border, columns), 
                        get_grid_width(seed_size, border, rows+1)), pg.SRCALPHA)
        
        s.fill(FG_COL)
        center_text(s, big_font, "seeds:", BLACK, s.get_width()*0.5, seed_size*0.5+border_size)

        if anim_timer < 0.5:
            for seed in self.anim_seeds:
                if seed[1] == None:
                    continue
                pos = [get_grid_width(seed_size, border, seed[1]%columns), 
                       get_grid_width(seed_size, border, seed[1]//columns+1)]
                t = draw_tile(seed[0], seed_size)
                s.blit(t, pos)
        elif anim_timer < 1.0:
            for seed in self.anim_seeds:
                if seed[1] == None:
                    scale_factor = anim_timer*2-1
                    pos = [get_grid_width(seed_size, border, seed[2]%columns), 
                           get_grid_width(seed_size, border, seed[2]//columns+1)]
                elif seed[2] == None:
                    scale_factor = 2-anim_timer*2
                    pos = [get_grid_width(seed_size, border, seed[1]%columns), 
                           get_grid_width(seed_size, border, seed[1]//columns+1)]
                else:
                    scale_factor = 1.0
                    pos = [pg.math.lerp(get_grid_width(seed_size, border, seed[1]%columns), 
                                        get_grid_width(seed_size, border, seed[2]%columns),
                                        anim_timer*2-1), 
                           pg.math.lerp(get_grid_width(seed_size, border, seed[1]//columns+1),
                                         get_grid_width(seed_size, border, seed[2]//columns+1),
                                         anim_timer*2-1)]
                
                t = draw_tile(seed[0], seed_size)
                if scale_factor != 1:
                    pos[0] -= seed_size*(scale_factor-1)*0.5
                    pos[1] -= seed_size*(scale_factor-1)*0.5
                    t = pg.transform.scale(t, (seed_size*scale_factor, seed_size*scale_factor))
                
                s.blit(t, pos)

        elif self.game_over:

            for i, j in enumerate(self.all_seeds):
                pos = [get_grid_width(seed_size, border, i%columns), 
                       get_grid_width(seed_size, border, i//columns+1)]
                t = draw_tile(j, seed_size)
                if j not in self.seeds:
                    t.set_alpha(64)
                s.blit(t, pos)

        else:
            for i, j in enumerate(self.seeds):
                pos = [get_grid_width(seed_size, border, i%columns), 
                       get_grid_width(seed_size, border, i//columns+1)]
                t = draw_tile(j, seed_size)
                s.blit(t, pos)
        
        return s
    
    def display(self, tile_size, border, anim_timer):

        s = pg.Surface((get_grid_width(tile_size, border, self.width), 
                        get_grid_width(tile_size, border, self.height)), pg.SRCALPHA)

        s.fill(FG_COL)

        # draw empty grid
        for i in range(self.width):
            for j in range(self.height):
                pg.draw.rect(s, EMPTY_TILE_COL, (get_grid_width(tile_size, border, i), get_grid_width(tile_size, border, j), tile_size, tile_size))

        if self.tainted:
            for i in range(self.width+1):
                for j in range(self.height+1):
                    pg.draw.circle(s, BLACK, (get_grid_width(tile_size, border, i)-border_size*0.5, get_grid_width(tile_size, border, j)-border_size*0.5), border_size*0.5)

        
        # first half of animation
        if anim_timer < 0.5:

            for tile in self.anim_tiles:
                if tile[1] == None:
                    continue
                # draw moving tiles
                pos = [get_grid_width(tile_size, border, pg.math.lerp(tile[0][0],tile[2][0],anim_timer*2)), 
                       get_grid_width(tile_size, border, pg.math.lerp(tile[0][1],tile[2][1],anim_timer*2))]
                t = draw_tile(tile[1], tile_size)
                s.blit(t, pos)

        # second half of animation
        elif anim_timer < 1.0:
            for tile in self.anim_tiles:
                if tile[1] == None:
                    scale_factor = anim_timer*2-1
                elif tile[1] != tile[3]:
                    scale_factor = -3.2*(anim_timer-1)*(anim_timer-0.5)+1
                else:
                    scale_factor = 1.0
                pos = [get_grid_width(tile_size, border, tile[2][0]), 
                       get_grid_width(tile_size, border, tile[2][1])]
                t = draw_tile(tile[3], tile_size)
                if scale_factor != 1:
                    pos[0] -= tile_size*(scale_factor-1)*0.5
                    pos[1] -= tile_size*(scale_factor-1)*0.5
                    t = pg.transform.scale(t, (tile_size*scale_factor, tile_size*scale_factor))
                s.blit(t, pos)
        else:
            # draw tiles normally
            for i in range(self.width):
                for j in range(self.height):
                    if self.tiles[i][j] == None:
                        continue
                    pos = [get_grid_width(tile_size, border, i), 
                           get_grid_width(tile_size, border, j)]
                    t = draw_tile(self.tiles[i][j], tile_size) 
                    s.blit(t, pos)

            if self.game_over:
                game_over_text = huge_font.render("game over.", 1, WHITE)
                s.blit(game_over_text, ((s.get_width()-game_over_text.get_width())*0.5,(s.get_height()-game_over_text.get_height())*0.5))
        
        return s

class Particle:

    particles = []

    def __init__(self, pos, vel, size, col, life):
        self.pos = Vector2(pos)
        self.vel = Vector2(vel) 
        self.size = size
        self.col = col
        self.life = float(life)
        self.max_life = self.life

        self.particles.append(self)

    def update(self, tdelta):

        self.pos += self.vel*(tdelta*0.001)
        self.life -= tdelta*0.001

    def display(self, surf):
        real_size = (self.life/self.max_life)*self.size
        pg.draw.circle(surf, self.col, self.pos, real_size)

class Button:

    def __init__(self, pos, text="", img=None, hover_img=None):

        self.pos = pg.Rect(pos)
        self.text = text
        if img == None:
            self.img = pg.transform.scale(button_off_sprite, self.pos.size)
        else:
            self.img = pg.transform.scale(img, self.pos.size)
        if hover_img == None:
            self.hover_img = pg.transform.scale(button_on_sprite, self.pos.size)
        else:
            self.hover_img = pg.transform.scale(hover_img, self.pos.size)

    def display(self, surf, mouse_pos):

        if self.pos.collidepoint(mouse_pos):
            sprite = self.hover_img
        else:
            sprite = self.img

        surf.blit(sprite, self.pos.topleft)
        if self.text != "":
            t = big_font.render(self.text, 1, BLACK)
            surf.blit(t, (self.pos.centerx-t.get_width()*0.5, self.pos.centery-t.get_height()*0.5))

    def collide(self, mouse_pos):

        return self.pos.collidepoint(mouse_pos)

# class to save progress
class Profile:

    def __init__(self, name):

        self.name = name

        self.board = None
        self.saved_boards = [None for i in range(5)]

        self.default_settings = {}
        self.settings = {}
        self.stats = {}

        self.init_data()

        self.restart_game()

    # prevent crashing when loading an old profile
    def init_data(self):

        if "width" not in self.default_settings:
            self.default_settings["width"] = 4
        if "height" not in self.default_settings:
            self.default_settings["height"] = 4
        if "mode" not in self.default_settings:
            self.default_settings["mode"] = 1

        if "width" not in self.settings:
            self.settings["width"] = 4
        if "height" not in self.settings:
            self.settings["height"] = 4
        if "mode" not in self.settings:
            self.settings["mode"] = 1
        if "animspeed" not in self.settings:
            self.settings["animspeed"] = 250
        if "particles" not in self.settings:
            self.settings["particles"] = True

        if "highscore" not in self.stats:
            self.stats["highscore"] = 0
        if "history" not in self.stats:
            self.stats["history"] = []
        if "svalbard" not in self.stats:
            self.stats["svalbard"] = {}

    def has_default_settings(self):
        for i in self.default_settings:
            if self.default_settings[i] != self.settings[i]:
                return False
        return True
    
    # add the current board's stats to our stats and clear the board
    def update_stats(self):

        # don't record if board was tainted
        if self.board == None or self.board.tainted or self.board.score == 0:
            return
        
        self.stats["history"].append(self.board.score)

        # update highscore
        if self.board.score > self.stats["highscore"]:
            self.stats["highscore"] = self.board.score

        # get it because svalbard has the seed vault
        for i in self.board.all_seeds:
            if i not in self.stats["svalbard"]:
                self.stats["svalbard"][i] = 1
            else:
                self.stats["svalbard"][i] += 1
        self.board = None

    def restart_game(self):

        self.update_stats()

        self.board = Board(self.settings["width"], self.settings["height"], self.settings["mode"])
        self.board.tainted = not self.has_default_settings()
        self.board.setup()

    # pickle and save our progress
    def save_to_file(self):

        with open(PATH+f"profiles/{self.name}.dive", "wb") as file:
            pickle.dump(self, file)

    # save board to our saved boards
    def save_board(self, slot):

        if self.board == None:
            return
        
        # "taint" saved boards so we can't save scum for stats
        tainted = self.board.tainted
        self.board.tainted = True
        self.saved_boards[slot] = pickle.dumps(self.board)
        self.board.tainted = tainted

    # load board from our saved boards
    def load_board(self, slot):

        if self.saved_boards[slot] == None:
            return None
        
        self.update_stats()

        self.board = pickle.loads(self.saved_boards[slot])
        return self.board
    
    def get_board(self):

        return self.board

    # unpickle and return a list of the saved boards
    def get_saved_boards(self):

        return [None if self.saved_boards[i] == None else pickle.loads(self.saved_boards[i]) for i in range(5)]

# get the width of a grid with a border
def get_grid_width(tile_width, border_width, tiles):
    return tile_width*tiles+border_width*(tiles+1)

# get the colour of a tile
# returns a colour
def get_tile_col(tile):

    # how did you even get a 0 tile?
    if tile == 0 or isinstance(tile, str):
        return WHITE
    
    r = 0
    g = 0
    b = 0

    # make tile redder for each 2,
    while tile % 2 == 0:
        tile //= 2
        r = 102+r*0.6
    
    # greener for each 3,
    while tile % 3 == 0:
        tile //= 3
        g = 102+g*0.6

    # and bluer for each 5.
    while tile % 5 == 0:
        tile //= 5
        b = 102+b*0.6

    return pg.Color(int(r), int(g), int(b))

# get the sprite of a tile
# returns a surface with the sprite
def get_tile_sprite(tile):

    # zero tile has precomputed sprite to save processing power
    if tile == 0:
        return zero_sprite
    
    s = pg.Surface((212, 212), pg.SRCALPHA)

    # strings, e.g. rocks
    if isinstance(tile, str):
        return s
    
    for i, j in enumerate(PRIMES):
        while tile % j == 0:
            s.blit(prime_sprites[i], (0, 0))
            tile //= j
        if tile == 1:
            break
    return s

# draw a tile.
# returns a surface with the tile
def draw_tile(tile, size):
    if tile == None:
        return
    
    # pick a font size to fit the tile
    if len(str(tile)) < size*0.04:
        font = huge_font
        shadow_size = 2
    elif len(str(tile)) < size*0.07:
        font = big_font
        shadow_size = 2
    elif len(str(tile)) < size*0.1:
        font = lil_font
        shadow_size = 1
    elif len(str(tile)) < size*0.15:
        font = mini_font
        shadow_size = 1
    else:
        font = micro_font
        shadow_size = 1
    
    s = pg.Surface((size, size))
    tile_col = get_tile_col(tile)
    s.fill(tile_col)
    tile_sprite = get_tile_sprite(tile)
    s.blit(pg.transform.scale(tile_sprite, (size, size)), (0, 0))
    #if tile_col.r > 180 and tile_col.g > 180 and tile_col.b > 180:
    
    # shadow
    
    if isinstance(tile, str) or tile >= 0:
        text = font.render(str(tile), 1, WHITE)
        text_shadow = font.render(str(tile), 1, BLACK)
    else:
        # negative tiles get inverted text
        text = font.render(str(tile), 1, BLACK)
        text_shadow = font.render(str(tile), 1, WHITE)

    text_pos = ((size-text.get_width())//2, (size-text.get_height())//2)
    s.blit(text_shadow, (text_pos[0]-shadow_size, text_pos[1]))
    s.blit(text_shadow, (text_pos[0]-shadow_size, text_pos[1]-shadow_size))
    s.blit(text_shadow, (text_pos[0], text_pos[1]-shadow_size))
    s.blit(text_shadow, (text_pos[0]+shadow_size, text_pos[1]-shadow_size))
    s.blit(text_shadow, (text_pos[0]+shadow_size, text_pos[1]))
    s.blit(text_shadow, (text_pos[0]+shadow_size, text_pos[1]+shadow_size))
    s.blit(text_shadow, (text_pos[0], text_pos[1]+shadow_size))
    s.blit(text_shadow, (text_pos[0]-shadow_size, text_pos[1]+shadow_size))
    s.blit(text, text_pos)

    return s

# check if two tiles are mergeable
def check_merge(tile1, tile2):
    if tile1 == None or tile2 == None or tile1 == "rock" or tile2 == "rock":
        return None
    # two tiles are mergeable if one is a factor of the other
    # or one of them is 0 i guess
    if tile1 == 0 or tile2 == 0 or tile1 % tile2 == 0 or tile2 % tile1 == 0:
        return tile1 + tile2
    return None

def update_particles(tdelta):

    for p in Particle.particles:
        p.update(tdelta)

    Particle.particles = [p for p in Particle.particles if p.life > 0]

def display_particles(surf):

    for p in Particle.particles:
        p.display(surf)

def scatter_particles(pos, size, col, life, count, spread_min, spread_max):
    for i in range(count):
        vel = Vector2(random.uniform(spread_min, spread_max), 0).rotate(i*360.0/count)
        Particle(pos, vel, size, col, life)

def configure_ui(board):
    global board_pos, seed_pos, score_pos, tile_size, border_size, seed_columns, seed_size, svalbard_columns, svalbard_rows, svalbard_size, svalbard_pos, button_size, arrow_size, buttons

    border_size = int(min(8, DISPLAY_WIDTH/80, DISPLAY_HEIGHT/60))
    tile_size = (min(DISPLAY_WIDTH*0.5, DISPLAY_HEIGHT*0.75)-border_size*(max(board.width, board.height)+1))/max(board.width, board.height)
    seed_columns = 4
    seed_size = (DISPLAY_WIDTH/4-border_size*(seed_columns+3))/seed_columns

    button_size = DISPLAY_HEIGHT/8-border_size
    arrow_size = min((DISPLAY_HEIGHT-get_grid_width(tile_size, border_size, max(board.width, board.height))-border_size*3)*0.5, button_size)

    svalbard_columns = int(max((DISPLAY_WIDTH-button_size*2)//(80+border_size), 1))
    svalbard_rows = int(max((DISPLAY_HEIGHT-button_size*3)//(80+border_size), 1))
    svalbard_size = (DISPLAY_WIDTH-button_size*2-border_size*(svalbard_columns+1))/svalbard_columns
    svalbard_pos = (button_size, button_size)

    board_pos = pg.Rect((DISPLAY_WIDTH-get_grid_width(tile_size, border_size, max(board.width, board.height)))*0.5, 
                        border_size, 
                        get_grid_width(tile_size, border_size, max(board.width, board.height)), 
                        get_grid_width(tile_size, border_size, max(board.width, board.height)))
    
    seed_pos =  pg.Rect(board_pos.left-get_grid_width(seed_size, border_size, seed_columns)-border_size, 
                        border_size, 
                        get_grid_width(seed_size, border_size, seed_columns), 
                        get_grid_width(seed_size, border_size, 10))
  
    score_pos = pg.Rect(DISPLAY_WIDTH*0.75+border_size*2, 
                        border_size, 
                        button_size,
                        button_size)
    
    buttons = {"": {
        "right": Button((board_pos.centerx+arrow_size*0.5, 
                        board_pos.bottom+border_size+arrow_size, arrow_size, arrow_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "down": Button((board_pos.centerx-arrow_size*0.5, 
                        board_pos.bottom+border_size+arrow_size, arrow_size, arrow_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 270),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 270)),
        "left": Button((board_pos.centerx-arrow_size*1.5, 
                        board_pos.bottom+border_size+arrow_size, arrow_size, arrow_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "up": Button((board_pos.centerx-arrow_size*0.5, 
                        board_pos.bottom+border_size, arrow_size, arrow_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 90),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 90)),
        "settings": Button((DISPLAY_WIDTH*0.75+border_size, 
                        get_grid_width(button_size, border_size, 1), min(DISPLAY_WIDTH*0.25-border_size*2, button_size*3), button_size),
                        text="settings"),
        "restart": Button((DISPLAY_WIDTH*0.75+border_size, 
                        get_grid_width(button_size, border_size, 2), min(DISPLAY_WIDTH*0.25-border_size*2, button_size*3), button_size),
                        text="restart ([Y])"),  
        "save": Button((DISPLAY_WIDTH*0.75+border_size, 
                        get_grid_width(button_size, border_size, 3), min(DISPLAY_WIDTH*0.25-border_size*2, button_size*3), button_size),
                        text="save/load"),
        "stats": Button((DISPLAY_WIDTH*0.75+border_size, 
                        get_grid_width(button_size, border_size, 4), min(DISPLAY_WIDTH*0.25-border_size*2, button_size*3), button_size),
                        text="stats"),
        "profile": Button((DISPLAY_WIDTH*0.75+border_size, 
                        get_grid_width(button_size, border_size, 5), min(DISPLAY_WIDTH*0.25-border_size*2, button_size*3), button_size),
                        text="profile"),
    }, "settings": {
        "settings_left1": Button((0, button_size, button_size, button_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "settings_right1": Button((DISPLAY_WIDTH-button_size, button_size, button_size, button_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "settings_left2": Button((0, button_size*2, button_size, button_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "settings_right2": Button((DISPLAY_WIDTH-button_size, button_size*2, button_size, button_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "settings_left3": Button((0, button_size*3, button_size, button_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "settings_right3": Button((DISPLAY_WIDTH-button_size, button_size*3, button_size, button_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "settings_left4": Button((0, button_size*4, button_size, button_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "settings_right4": Button((DISPLAY_WIDTH-button_size, button_size*4, button_size, button_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "settings_left5": Button((0, button_size*5, button_size, button_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "settings_right5": Button((DISPLAY_WIDTH-button_size, button_size*5, button_size, button_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "back": Button((button_size, DISPLAY_HEIGHT-button_size, DISPLAY_WIDTH-button_size*2, button_size),
                        text="back"),
        "settings_next_page": Button((button_size, DISPLAY_HEIGHT-button_size*2, DISPLAY_WIDTH-button_size*2, button_size)),
    }, "save": {
        "back": Button((button_size, DISPLAY_HEIGHT-button_size, DISPLAY_WIDTH-button_size*2, button_size),
                        text="back"),
        "save_game": Button((button_size, DISPLAY_HEIGHT-button_size*2, DISPLAY_WIDTH*0.5-button_size, button_size)),
        "load_game": Button((DISPLAY_WIDTH*0.5, DISPLAY_HEIGHT-button_size*2, DISPLAY_WIDTH*0.5-button_size, button_size),
                        text="load"),
    }, "stats": {
        "svalbard": Button((DISPLAY_WIDTH-button_size*2, (button_size+border_size)*3, button_size*2, button_size),
                        text="svalbard"),
        "back": Button((button_size, DISPLAY_HEIGHT-button_size, DISPLAY_WIDTH-button_size*2, button_size),
                        text="back"),
    }, "profile": {
        "back": Button((button_size, DISPLAY_HEIGHT-button_size, DISPLAY_WIDTH-button_size*2, button_size),
                        text="back"),
        "reset": Button((DISPLAY_WIDTH*0.5, DISPLAY_HEIGHT-button_size*2, DISPLAY_WIDTH*0.5-button_size, button_size),
                        text="reset"),
    }, "svalbard": {
        "svalbard_left": Button((0, button_size, button_size, button_size),
                        img=pg.transform.rotate(button_arrow_off_sprite, 180),
                        hover_img=pg.transform.rotate(button_arrow_on_sprite, 180)),
        "svalbard_right": Button((DISPLAY_WIDTH-button_size, button_size, button_size, button_size),
                        img=button_arrow_off_sprite,
                        hover_img=button_arrow_on_sprite),
        "back": Button((button_size, DISPLAY_HEIGHT-button_size, DISPLAY_WIDTH-button_size*2, button_size),
                        text="back"),
    },
    }

    for i in range(5):
        buttons["save"][f"slot_{i+1}"] = Button((DISPLAY_WIDTH*0.2*i, 
                                             button_size,
                                             DISPLAY_WIDTH*0.2, 
                                             button_size*2))
        
def center_text(surf, font, text, col, x, y): # this was getting *so* annoying
    t = font.render(text, 1, col)
    surf.blit(t, (x-t.get_width()*0.5, y-t.get_height()*0.5))

def load_profile(profile_name):

    try:
        with open(PATH+f"profiles/{profile_name}.dive", "rb") as file:
            profile = pickle.load(file)
        return profile
    except:
        return None
    
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

pg.init()
main_dis = pg.display.set_mode(DISPLAY_SIZE, flags=pg.RESIZABLE)
pg.display.set_caption("pydive")
clock = pg.time.Clock()

prime_sprites = [pg.image.load(PATH+f"sprites/tile_{x}.png").convert_alpha() for x in PRIMES]
zero_sprite = pg.image.load(PATH+"sprites/zero.png").convert_alpha()
button_off_sprite = pg.image.load(PATH+"sprites/button_off.png").convert_alpha()
button_on_sprite = pg.image.load(PATH+"sprites/button_on.png").convert_alpha()
button_arrow_off_sprite = pg.image.load(PATH+"sprites/button_arrow_off.png").convert_alpha()
button_arrow_on_sprite = pg.image.load(PATH+"sprites/button_arrow_on.png").convert_alpha()

# pygame please let me change font size in a better way than this
huge_font = pg.font.Font(PATH+"Lato-Regular.ttf", 36)
big_font = pg.font.Font(PATH+"Lato-Regular.ttf", 24)
lil_font = pg.font.Font(PATH+"Lato-Regular.ttf", 18)
mini_font = pg.font.Font(PATH+"Lato-Regular.ttf", 12)
micro_font = pg.font.Font(PATH+"Lato-Regular.ttf", 8)

profile = load_profile("default")
if profile == None:
    profile = Profile("default")
profile.init_data()
board = profile.get_board()
configure_ui(board)

last_move = 0
anim_stage = 0
page = 0
just_moved = True

menu = ""

game_running = True
while game_running:
    
    for event in pg.event.get():
        if event.type == pg.QUIT:
            profile.save_to_file()
            game_running = False
        elif event.type == pg.KEYDOWN:
            if menu == "":
                if event.key in KEYBINDS["right"]:
                    just_moved = board.move("right")
                elif event.key in KEYBINDS["down"]:
                    just_moved = board.move("down")
                elif event.key in KEYBINDS["left"]:
                    just_moved = board.move("left")
                elif event.key in KEYBINDS["up"]:
                    just_moved = board.move("up")
                elif event.key in KEYBINDS["restart"]:
                    profile.restart_game()
                    board = profile.get_board()
                    configure_ui(board)
                    just_moved = True
        elif event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            
            active_buttons = buttons[menu]
            for b in active_buttons:
                if active_buttons[b].collide(pg.mouse.get_pos()):

                    if b in ["right", "down", "left", "up"]:
                        just_moved = board.move(b)

                    elif b == "restart":
                        profile.restart_game()
                        board = profile.get_board()
                        configure_ui(board)
                        just_moved = True
                        
                    elif b == "settings":
                        menu = "settings"
                        page = 1
                        buttons["settings"]["settings_next_page"].text = f"page {page}"

                    elif b == "save":
                        menu = "save"
                        buttons["save"]["save_game"].text = "save"
                        save_files = profile.get_saved_boards()
                        selected_slot = None

                    elif b == "stats":
                        menu = "stats"    
                    
                    elif b == "svalbard":
                        menu = "svalbard"
                        page = 1     

                    elif b == "profile":
                        menu = "profile"
                        reset_count = 0
                        buttons["profile"]["reset"].text = RESET_QUIPS[reset_count]

                    elif b == "back":
                        menu = ""

                    elif b == "settings_next_page":
                        page += 1
                        if page > 2:
                            page = 1
                        buttons["settings"]["settings_next_page"].text = f"page {page}"
                    
                    elif b == "svalbard_left":

                        # move to the previous page that actually has something on it
                        achieved = profile.stats["svalbard"].keys()
                        valid_page = False
                        while page > 1 and not valid_page:
                            valid_page = False
                            page -= 1
                            for i in range(svalbard_columns*svalbard_rows):
                                if (page-1)*svalbard_columns*svalbard_rows+i in achieved:
                                    valid_page = True
                                    break
                    elif b == "svalbard_right":

                        # move to the next page that actually has something on it
                        achieved = profile.stats["svalbard"].keys()
                        if len(achieved) == 0:
                            highest_page = 1
                        else:
                            highest_page = max(achieved)//(svalbard_columns*svalbard_rows)+1
                        valid_page = False
                        while page < highest_page and not valid_page:
                            valid_page = False
                            page += 1
                            for i in range(svalbard_columns*svalbard_rows):
                                if (page-1)*svalbard_columns*svalbard_rows+i in achieved:
                                    valid_page = True
                                    break

                    if page == 1:
                        if b == "settings_left1":
                            if profile.settings["mode"] > 0:
                                profile.settings["mode"] -= 1
                        elif b == "settings_right1":
                            if profile.settings["mode"] < 3:
                                profile.settings["mode"] += 1
                        elif b == "settings_left2":
                            if profile.settings["width"] > 1:
                                profile.settings["width"] -= 1
                        elif b == "settings_right2":
                            if profile.settings["width"] < 10:
                                profile.settings["width"] += 1
                        elif b == "settings_left3":
                            if profile.settings["height"] > 1:
                                profile.settings["height"] -= 1
                        elif b == "settings_right3":
                            if profile.settings["height"] < 10:
                                profile.settings["height"] += 1

                    elif page == 2:
                            
                        if b == "settings_left1":
                            if profile.settings["animspeed"] > 0:
                                profile.settings["animspeed"] -= 50
                        elif b == "settings_right1":
                            if profile.settings["animspeed"] < 1000:
                                profile.settings["animspeed"] += 50
                        elif b == "settings_left2":
                            profile.settings["particles"] = False
                        elif b == "settings_right2":
                            profile.settings["particles"] = True

                    if b.startswith("slot"):

                        #select the slot
                        selected_slot = int(b[-1])-1

                        if save_files[selected_slot] == None:
                            buttons["save"]["save_game"].text = "save"
                        else:
                            buttons["save"]["save_game"].text = "overwrite"

                    elif b == "save_game":

                        # save board to the slot
                        if selected_slot != None:

                            profile.save_board(selected_slot)
                            menu = ""

                    elif b == "load_game":

                        if selected_slot != None:

                            loaded_board = profile.load_board(selected_slot)

                            if loaded_board != None:
                                board = loaded_board
                                configure_ui(board)
                                just_moved = True
                                menu = ""

                    if b == "reset":
                        reset_count += 1
                        if reset_count >= len(RESET_QUIPS):
                            profile = Profile("default")
                            board = profile.get_board()
                            configure_ui(board)
                            menu = ""
                            just_moved = True
                        else:
                            buttons["profile"]["reset"].text = RESET_QUIPS[reset_count]

            # end of awful button code 
        elif event.type == pg.VIDEORESIZE:
            DISPLAY_SIZE = (main_dis.get_width(), main_dis.get_height())
            DISPLAY_WIDTH, DISPLAY_HEIGHT = DISPLAY_SIZE
            configure_ui(board)

        #elif event.type == pg.MOUSEMOTION:
        #    DISPLAY_SIZE = pg.mouse.get_pos()
        #    DISPLAY_WIDTH, DISPLAY_HEIGHT = DISPLAY_SIZE
        #    configure_ui(board)
    
    if just_moved:
        last_move = pg.time.get_ticks()
        anim_stage = 0
        just_moved = False

    tdelta = clock.tick()
    update_particles(tdelta)
    
    if profile.settings["animspeed"] > 0:
        anim_timer = (pg.time.get_ticks()-last_move)/float(profile.settings["animspeed"])
    else:
        anim_timer = 1.0

    if anim_stage == 0 and anim_timer > 0.5:
        anim_stage = 1
        if profile.settings["particles"]:
            for i in board.anim_tiles:
                if i[1] != i[3] and i[1] != None:
                    scatter_particles((get_grid_width(tile_size, border_size, i[2][0])+tile_size*0.5+board_pos.x, 
                                    get_grid_width(tile_size, border_size, i[2][1])+tile_size*0.5+board_pos.y), 
                                    15, get_tile_col(i[3]), 0.8, 12, 300, 300)
            for i in board.anim_seeds:
                if i[2] == None:
                    scatter_particles((get_grid_width(seed_size, border_size, i[1]%seed_columns)+seed_size*0.5+seed_pos.x, 
                                    get_grid_width(seed_size, border_size, i[1]//seed_columns+1)+seed_size*0.5+seed_pos.y), 
                                    15, get_tile_col(i[0]), 0.4, 12, 150, 150)

    main_dis.fill(BG_COL)

    for b in buttons[menu].values():
        b.display(main_dis, pg.mouse.get_pos())

    
    if menu == "": # main game
        board_surf = board.display(tile_size, border_size, anim_timer)
        main_dis.blit(board_surf, board_pos.topleft)

        seed_list_surf = board.display_seed_list(seed_size, border_size, seed_columns, 1, anim_timer)
        main_dis.blit(seed_list_surf, seed_pos.topleft)

        if anim_timer < 0.5:
            score_surf = draw_tile(board.anim_score, button_size)
        else:
            score_surf = draw_tile(board.score, button_size)
        
        main_dis.blit(score_surf, score_pos.topleft)
        center_text(main_dis, lil_font, "score", WHITE, score_pos.centerx, score_pos.top+border_size)

        if anim_timer < 0.5:
            high_score_surf = draw_tile(max(board.anim_score, profile.stats["highscore"]), button_size)
        else:
            high_score_surf = draw_tile(max(board.score, profile.stats["highscore"]), button_size)
        main_dis.blit(high_score_surf, (score_pos.right+border_size, score_pos.top))
        center_text(main_dis, lil_font, "best", WHITE, score_pos.centerx+score_pos.width+border_size, score_pos.top+border_size)

        display_particles(main_dis)

    elif menu == "settings": # settings menu

        if page == 1:
            center_text(main_dis, huge_font, "game settings (apply to new games only)", BLACK, DISPLAY_WIDTH*0.5, button_size*0.5)
            
            center_text(main_dis, huge_font, f"gamemode: {GAMEMODE_DESCRIPTIONS[profile.settings["mode"]]}", BLACK, DISPLAY_WIDTH*0.5, button_size*1.5)
            center_text(main_dis, huge_font, f"width: {profile.settings["width"]}", BLACK, DISPLAY_WIDTH*0.5, button_size*2.5)
            center_text(main_dis, huge_font, f"height: {profile.settings["height"]}", BLACK, DISPLAY_WIDTH*0.5, button_size*3.5)

            if not profile.has_default_settings():
                center_text(main_dis, huge_font, f"note: stats disabled", BLACK, DISPLAY_WIDTH*0.5, DISPLAY_HEIGHT-button_size*2.5)

        elif page == 2:
            center_text(main_dis, huge_font, "visual settings", BLACK, DISPLAY_WIDTH*0.5, button_size*0.5)
            
            center_text(main_dis, huge_font, f"anim speed: {profile.settings["animspeed"]}ms", BLACK, DISPLAY_WIDTH*0.5, button_size*1.5)
            center_text(main_dis, huge_font, f"particles: {"on" if profile.settings["particles"] else "off"}", BLACK, DISPLAY_WIDTH*0.5, button_size*2.5)

    elif menu == "save": # save/load menu
        center_text(main_dis, huge_font, "save/load", BLACK, DISPLAY_WIDTH*0.5, button_size*0.5)

        for i in range(5):
            if selected_slot == i:
                main_dis.blit(pg.transform.scale(get_tile_sprite(11), (DISPLAY_WIDTH*0.2, button_size*2)), (DISPLAY_WIDTH*0.2*i, button_size))
            if save_files[i] == None:
                center_text(main_dis, huge_font, "empty", BLACK, DISPLAY_WIDTH*0.2*(i+0.5), button_size*2)
            else:
                s = draw_tile(save_files[i].score, button_size)
                main_dis.blit(s, (DISPLAY_WIDTH*0.2*(i+0.5)-s.get_width()*0.5, button_size*2-s.get_height()*0.5))
                center_text(main_dis, lil_font, GAMEMODE_DESCRIPTIONS[save_files[i].mode], BLACK, DISPLAY_WIDTH*0.2*(i+0.5), button_size*2.7)
        center_text(main_dis, huge_font, f"note: loaded games have stats disabled", BLACK, DISPLAY_WIDTH*0.5, DISPLAY_HEIGHT-button_size*2.5)
    
    elif menu == "stats":
        center_text(main_dis, huge_font, "stats", BLACK, DISPLAY_WIDTH*0.5, button_size*0.5)

        stat_labels = [("games played:", len(profile.stats["history"])),
                       ("high score:", profile.stats["highscore"]),
                       ("unique seeds discovered:", len(profile.stats["svalbard"].keys())),
                       ("highest seed discovered:", 0 if len(profile.stats["svalbard"]) == 0 else max(profile.stats["svalbard"].keys()))]
        for i, j in enumerate(stat_labels):
            text = huge_font.render(j[0], 1, BLACK)
            main_dis.blit(text, (button_size*2+border_size, (button_size+border_size)*(1.5+i)-text.get_height()*0.5))
            main_dis.blit(draw_tile((j[1]), button_size), (button_size*2+text.get_width()+border_size*2, (button_size+border_size)*(1+i)))
        #center_text(main_dis, huge_font, f"games played: {len(profile.stats["history"])}", BLACK, DISPLAY_WIDTH*0.25, button_size*1.5)
    
    elif menu == "svalbard":
        center_text(main_dis, huge_font, f"svalbard (page {page})", BLACK, DISPLAY_WIDTH*0.5, button_size*0.5)

        start_index = (page-1)*svalbard_columns*svalbard_rows
        achieved = profile.stats["svalbard"].keys()
        for i in range(svalbard_rows):
            for j in range(svalbard_columns):
                svalbard_tile = start_index+i*svalbard_columns+j
                if svalbard_tile < 2:
                    continue
                t = draw_tile(svalbard_tile, svalbard_size)
                if svalbard_tile not in achieved:
                    t.set_alpha(63)

                pos = (get_grid_width(svalbard_size, border_size, j)+svalbard_pos[0], get_grid_width(svalbard_size, border_size, i)+svalbard_pos[1])
                main_dis.blit(t, pos)
                if pg.Rect(pos, (svalbard_size, svalbard_size)).collidepoint(pg.mouse.get_pos()):
                    times = 0 if svalbard_tile not in achieved else profile.stats["svalbard"][svalbard_tile]
                    center_text(main_dis, huge_font, f"unlocked this seed in {times} game{"" if times == 1 else "s"}", BLACK, DISPLAY_WIDTH*0.5, DISPLAY_HEIGHT-button_size*1.5)


    elif menu == "profile":
        center_text(main_dis, huge_font, "profile", BLACK, DISPLAY_WIDTH*0.5, button_size*0.5)

    pg.display.flip()

pg.quit()