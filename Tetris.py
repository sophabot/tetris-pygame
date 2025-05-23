import random
import pygame
import threading
import time
import os
import json  # Add this as it's needed for JSON parsing


import vosk


import speech_recognition as sr

"""
10 x 20 grid
play_height = 2 * play_width

tetriminos:
    0 - S - green
    1 - Z - red
    2 - I - cyan
    3 - O - yellow
    4 - J - blue
    5 - L - orange
    6 - T - purple
"""

pygame.font.init()

# global variables

col = 10  # 10 columns
row = 20  # 20 rows
s_width = 800  # window width
s_height = 750  # window height
play_width = 300  # play window width; 300/10 = 30 width per block
play_height = 600  # play window height; 600/20 = 20 height per block
block_size = 30  # size of block

top_left_x = (s_width - play_width) // 2
top_left_y = s_height - play_height - 50

filepath = './highscore.txt'
fontpath = './arcade.ttf'
fontpath_mario = './mario.ttf'

# shapes formats

S = [['.....',
      '.....',
      '..00.',
      '.00..',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '...0.',
      '.....']]

Z = [['.....',
      '.....',
      '.00..',
      '..00.',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '.0...',
      '.....']]

I = [['.....',
      '..0..',
      '..0..',
      '..0..',
      '..0..'],
     ['.....',
      '0000.',
      '.....',
      '.....',
      '.....']]

O = [['.....',
      '.....',
      '.00..',
      '.00..',
      '.....']]

J = [['.....',
      '.0...',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..00.',
      '..0..',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '...0.',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '.00..',
      '.....']]

L = [['.....',
      '...0.',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '..00.',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '.0...',
      '.....'],
     ['.....',
      '.00..',
      '..0..',
      '..0..',
      '.....']]

T = [['.....',
      '..0..',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '..0..',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '..0..',
      '.....']]

# index represents the shape
shapes = [S, Z, I, O, J, L, T]
shape_colors = [(0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 0), (255, 165, 0), (0, 0, 255), (128, 0, 128)]


# class to represent each of the pieces


class Piece(object):
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.color = shape_colors[shapes.index(shape)]  # choose color from the shape_color list
        self.rotation = 0  # chooses the rotation according to index


# initialise the grid
def create_grid(locked_pos={}):
    grid = [[(0, 0, 0) for x in range(col)] for y in range(row)]  # grid represented rgb tuples

    # locked_positions dictionary
    # (x,y):(r,g,b)
    for y in range(row):
        for x in range(col):
            if (x, y) in locked_pos:
                color = locked_pos[
                    (x, y)]  # get the value color (r,g,b) from the locked_positions dictionary using key (x,y)
                grid[y][x] = color  # set grid position to color

    return grid


def convert_shape_format(piece):
    positions = []
    shape_format = piece.shape[piece.rotation % len(piece.shape)]  # get the desired rotated shape from piece

    '''
    e.g.
       ['.....',
        '.....',
        '..00.',
        '.00..',
        '.....']
    '''
    for i, line in enumerate(shape_format):  # i gives index; line gives string
        row = list(line)  # makes a list of char from string
        for j, column in enumerate(row):  # j gives index of char; column gives char
            if column == '0':
                positions.append((piece.x + j, piece.y + i))

    for i, pos in enumerate(positions):
        positions[i] = (pos[0] - 2, pos[1] - 4)  # offset according to the input given with dot and zero

    return positions


# checks if current position of piece in grid is valid
def valid_space(piece, grid):
    # makes a 2D list of all the possible (x,y)
    accepted_pos = [[(x, y) for x in range(col) if grid[y][x] == (0, 0, 0)] for y in range(row)]
    # removes sub lists and puts (x,y) in one list; easier to search
    accepted_pos = [x for item in accepted_pos for x in item]

    formatted_shape = convert_shape_format(piece)

    for pos in formatted_shape:
        if pos not in accepted_pos:
            if pos[1] >= 0:
                return False
    return True


# check if piece is out of board
def check_lost(positions):
    for pos in positions:
        x, y = pos
        if y < 1:
            return True
    return False


# chooses a shape randomly from shapes list
def get_shape():
    return Piece(5, 0, random.choice(shapes))


# had an error w/ this font stuff, so added a new font: 
def draw_text_middle(text, size, color, surface):
    try:
        if fontpath is None or not pygame.font.get_init():
            # make sure font module initialized
            pygame.font.init()
            font = pygame.font.SysFont('arial', size)
        else:
            # custom font
            try:
                font = pygame.font.Font(fontpath, size)
            except (pygame.error, FileNotFoundError):
                # fallback to system font if custom font fails
                pygame.font.init()
                font = pygame.font.SysFont('arial', size)
                
        label = font.render(text, 1, color)
        surface.blit(label, (top_left_x + play_width/2 - (label.get_width()/2), 
                            top_left_y + play_height/2 - (label.get_height()/2)))
                            
    except Exception as e:
        print(f"Error rendering text: {e}")
        pygame.font.init()


# draws the lines of the grid for the game
def draw_grid(surface):
    r = g = b = 0
    grid_color = (r, g, b)

    for i in range(row):
        # draw grey horizontal lines
        pygame.draw.line(surface, grid_color, (top_left_x, top_left_y + i * block_size),
                         (top_left_x + play_width, top_left_y + i * block_size))
        for j in range(col):
            # draw grey vertical lines
            pygame.draw.line(surface, grid_color, (top_left_x + j * block_size, top_left_y),
                             (top_left_x + j * block_size, top_left_y + play_height))


# clear a row when it is filled
def clear_rows(grid, locked):
    # need to check if row is clear then shift every other row above down one
    increment = 0
    for i in range(len(grid) - 1, -1, -1):      # start checking the grid backwards
        grid_row = grid[i]                      # get the last row
        if (0, 0, 0) not in grid_row:           # if there are no empty spaces (i.e. black blocks)
            increment += 1
            # add positions to remove from locked
            index = i                           # row index will be constant
            for j in range(len(grid_row)):
                try:
                    del locked[(j, i)]          # delete every locked element in the bottom row
                except ValueError:
                    continue

    # shift every row one step down
    # delete filled bottom row
    # add another empty row on the top
    # move down one step
    if increment > 0:
        # sort the locked list according to y value in (x,y) and then reverse
        # reversed because otherwise the ones on the top will overwrite the lower ones
        for key in sorted(list(locked), key=lambda a: a[1])[::-1]:
            x, y = key
            if y < index:                       # if the y value is above the removed index
                new_key = (x, y + increment)    # shift position to down
                locked[new_key] = locked.pop(key)

    return increment


# draws the upcoming piece
def draw_next_shape(piece, surface):
    font = pygame.font.Font(fontpath, 30)
    label = font.render('Next shape', 1, (255, 255, 255))

    start_x = top_left_x + play_width + 50
    start_y = top_left_y + (play_height / 2 - 100)

    shape_format = piece.shape[piece.rotation % len(piece.shape)]

    for i, line in enumerate(shape_format):
        row = list(line)
        for j, column in enumerate(row):
            if column == '0':
                pygame.draw.rect(surface, piece.color, (start_x + j*block_size, start_y + i*block_size, block_size, block_size), 0)

    surface.blit(label, (start_x, start_y - 30))

    # pygame.display.update()


# draws the content of the window
def draw_window(surface, grid, score=0, last_score=0):
    surface.fill((0, 0, 0))  # fill the surface with black

    pygame.font.init()  # initialise font
    font = pygame.font.Font(fontpath_mario, 65)    
    label = font.render('TETRIS', 1, (255, 255, 255))  # initialise 'Tetris' text with white

    surface.blit(label, ((top_left_x + play_width / 2) - (label.get_width() / 2), 30))  # put surface on the center of the window

    # current score
    font = pygame.font.Font(fontpath, 30)  # Set size to 30
    label = font.render('SCORE: ' + str(score), 1, (255, 255, 255))  # Define text and color    

    start_x = top_left_x + play_width + 50
    start_y = top_left_y + (play_height / 2 - 100)

    surface.blit(label, (start_x, start_y + 200))

    # last score
    label_hi = font.render('HIGHSCORE   ' + str(last_score), 1, (255, 255, 255))

    start_x_hi = top_left_x - 240
    start_y_hi = top_left_y + 200

    surface.blit(label_hi, (start_x_hi + 20, start_y_hi + 200))

    # draw content of the grid
    for i in range(row):
        for j in range(col):
            # pygame.draw.rect()
            # draw a rectangle shape
            # rect(Surface, color, Rect, width=0) -> Rect
            pygame.draw.rect(surface, grid[i][j],
                             (top_left_x + j * block_size, top_left_y + i * block_size, block_size, block_size), 0)

    # draw vertical and horizontal grid lines
    draw_grid(surface)

    # draw rectangular border around play area
    border_color = (255, 255, 255)
    pygame.draw.rect(surface, border_color, (top_left_x, top_left_y, play_width, play_height), 4)

    # pygame.display.update()


# update the score txt file with high score
def update_score(new_score):
    score = get_max_score()

    with open(filepath, 'w') as file:
        if new_score > score:
            file.write(str(new_score))
        else:
            file.write(str(score))


# get the high score from the file
def get_max_score():
    with open(filepath, 'r') as file:
        lines = file.readlines()        # reads all the lines and puts in a list
        score = int(lines[0].strip())   # remove \n

    return score


# handle speech recognition and spoken commands
def listen_for_commands(command_queue):
    print("Starting speech recognition")
    try:
        print("Vosk speech recognition enabled")
        try:
            # Try different model paths or download if needed
            model_path = "model"
            if not os.path.exists(model_path):
                print("Downloading Vosk model...")
                import urllib.request
                import zipfile
                    
                # Download small English model
                url = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
                zip_path = "vosk-model.zip"
                urllib.request.urlretrieve(url, zip_path)
                    
                # Extract and rename
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall("./")
                os.rename("vosk-model-small-en-us-0.15", "model")
                os.remove(zip_path)
                print("Model downloaded and extracted")
                    
            model = vosk.Model(model_path)
            # fast response for recog
            recognizer = vosk.KaldiRecognizer(model, 16000)
            
            vosk.SetLogLevel(-1)  # Disable non-critical logs
                
            import pyaudio
            p = pyaudio.PyAudio()
            # smaller buffer sizes for more responsive recognition
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=2000)
            stream.start_stream()
            
            # avoid duplicate commands
            last_command = None
            last_command_time = 0
            
            while True:
                try:
                    # read smaller chunks for quicker response
                    data = stream.read(2000, exception_on_overflow=False)
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").lower()
                        
                        # process if we have actual text
                        if text:
                            print(f"Recognized: '{text}'")
                            
                            # avoid dupes
                            current_time = time.time()
                            
                            if ("left" in text or text == "l") and (last_command != "left" or current_time - last_command_time > 0.3):
                                command_queue.append("left")
                                last_command = "left"
                                last_command_time = current_time
                            elif ("right" in text or text == "r") and (last_command != "right" or current_time - last_command_time > 0.3):
                                command_queue.append("right")
                                last_command = "right"
                                last_command_time = current_time
                            elif ("down" in text or text == "d") and (last_command != "down" or current_time - last_command_time > 0.3):
                                command_queue.append("hard_drop") 
                                last_command = "down"
                                last_command_time = current_time
                            elif ("up" in text or text == "u" or "rotate" in text) and (last_command != "rotate" or current_time - last_command_time > 0.3):
                                command_queue.append("rotate")
                                last_command = "rotate"
                                last_command_time = current_time
                            elif ("start" in text or text == "s") and (last_command != "start" or current_time - last_command_time > 0.3):
                                command_queue.append("start")
                                last_command = "start"
                                last_command_time = current_time
                            elif ("quit" in text or text == "q") and (last_command != "quit" or current_time - last_command_time > 0.3):
                                command_queue.append("quit")
                                last_command = "quit"
                                last_command_time = current_time
                except IOError:
                    pass
                
                # prevent cpu overlaod
                time.sleep(0.01)
                
        except Exception as e:
            print(f"Vosk error: {e}")
            
    except ImportError as e:
        print(f"DEBUG - Import error: {e}")
        print("pip install SpeechRecognition and PyAudio")


def hard_drop(piece, grid):
    current_y = piece.y
    while valid_space(piece, grid):
        piece.y += 1
    
    piece.y -= 1
    return piece.y > current_y 


def main(window, command_queue=None, existing_speech_thread=None):
    locked_positions = {}
    create_grid(locked_positions)

    change_piece = False
    run = True
    current_piece = get_shape()
    next_piece = get_shape()
    clock = pygame.time.Clock()
    fall_time = 0
    fall_speed = 0.8# fall speed of the piece
    level_time = 0
    score = 0
    last_score = get_max_score()

    # Use existing command queue if provided, otherwise create a new one
    if command_queue is None:
        command_queue = []

    # Start speech recognition thread ONLY if we don't already have one
    if existing_speech_thread is None:
        try:
            threading.Thread(target=listen_for_commands, args=(command_queue,), daemon=True).start()
        except Exception as e:
            print(f"Could not start speech recognition: {e}")
            print("Game will continue without voice controls")

    while run:
        # need to constantly make new grid as locked positions always change
        grid = create_grid(locked_positions)

        # helps run the same on every computer
        # add time since last tick() to fall_time
        fall_time += clock.get_rawtime()  # returns in milliseconds
        level_time += clock.get_rawtime()

        clock.tick()  # updates clock

        if level_time/1000 > 5:    # make the difficulty harder every 5 seconds
            level_time = 0
            if fall_speed > 0.15:   # until fall speed is 0.15
                fall_speed -= 0.005

        if fall_time / 1000 > fall_speed:
            fall_time = 0
            current_piece.y += 1
            if not valid_space(current_piece, grid) and current_piece.y > 0:
                current_piece.y -= 1
                # since only checking for down - either reached bottom or hit another piece
                # need to lock the piece position
                # need to generate new piece
                change_piece = True

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.display.quit()
                quit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    current_piece.x -= 1  # move x position left
                    if not valid_space(current_piece, grid):
                        current_piece.x += 1

                elif event.key == pygame.K_RIGHT:
                    current_piece.x += 1  # move x position right
                    if not valid_space(current_piece, grid):
                        current_piece.x -= 1

                elif event.key == pygame.K_DOWN:
                    # move shape all the way down
                    while valid_space(current_piece, grid):
                        current_piece.y += 1
                    current_piece.y -= 1  
                    change_piece = True  # lock the piece immediately after hard drop

                elif event.key == pygame.K_UP:
                    # rotate shape
                    current_piece.rotation = current_piece.rotation + 1 % len(current_piece.shape)
                    if not valid_space(current_piece, grid):
                        current_piece.rotation = current_piece.rotation - 1 % len(current_piece.shape)

        # process speech commands if available
        commands_to_process = []
        while command_queue:
            command = command_queue.pop(0)
            commands_to_process.append(command)

        # Now execute all unique commands efficiently
        if "left" in commands_to_process:
            current_piece.x -= 1
            if not valid_space(current_piece, grid):
                current_piece.x += 1

        if "right" in commands_to_process:
            current_piece.x += 1
            if not valid_space(current_piece, grid):
                current_piece.x -= 1

        if "down" in commands_to_process or "hard_drop" in commands_to_process:
            # move shape all the way down
            while valid_space(current_piece, grid):
                current_piece.y += 1
            current_piece.y -= 1  # Move back up one step - we went too far
            change_piece = True  # Lock the piece immediately after hard drop

        if "rotate" in commands_to_process:
            current_piece.rotation = current_piece.rotation + 1 % len(current_piece.shape)
            if not valid_space(current_piece, grid):
                current_piece.rotation = current_piece.rotation - 1 % len(current_piece.shape)

        if "quit" in commands_to_process:
            run = False

        piece_pos = convert_shape_format(current_piece)

        # draw the piece on the grid by giving color in the piece locations
        for i in range(len(piece_pos)):
            x, y = piece_pos[i]
            if y >= 0:
                grid[y][x] = current_piece.color

        if change_piece:  # if the piece is locked
            for pos in piece_pos:
                p = (pos[0], pos[1])
                locked_positions[p] = current_piece.color       # add the key and value in the dictionary
            current_piece = next_piece
            next_piece = get_shape()
            change_piece = False
            score += clear_rows(grid, locked_positions) * 10    # increment score by 10 for every row cleared
            update_score(score)

            if last_score < score:
                last_score = score

        draw_window(window, grid, score, last_score)
        draw_next_shape(next_piece, window)
        pygame.display.update()

        if check_lost(locked_positions):
            run = False

    draw_text_middle('You Lost', 40, (255, 255, 255), window)
    pygame.display.update()
    pygame.time.delay(2000)  # wait for 2 seconds
    pygame.quit()


def main_menu(window):
    # Make sure pygame is fully initialized before doing anything
    pygame.init()
    pygame.font.init()
    
    run = True
    command_queue = []
    speech_thread = None
    
    # speech recognition thread for menu, optional
    try:
        speech_thread = threading.Thread(target=listen_for_commands, args=(command_queue,), daemon=True)
        speech_thread.start()
        voice_enabled = True
    except Exception as e:
        print(f"Could not start speech recognition: {e}")
        print("Continue without voice controls")
        voice_enabled = False
    
    while run:
        window.fill((0, 0, 0))  # Clear screen with black background
        
        # Don't show say text if you can't use voice commands
        if voice_enabled:
            draw_text_middle('Press any key or say START to begin', 50, (255, 255, 255), window)
        else:
            draw_text_middle('Press any key to begin', 50, (255, 255, 255), window)
            
        pygame.display.update()
        
        # voice commands in menu if available
        if command_queue:
            command = command_queue.pop(0)
            if command == "start":
                # Pass the existing command queue to main to avoid creating a new thread
                main(window, command_queue, speech_thread)
            elif command == "quit":
                run = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                # Pass the existing command queue to main to avoid creating a new thread
                main(window, command_queue, speech_thread)
                
        # delay to prevent high CPU usage
        pygame.time.delay(100)

    pygame.quit()


if __name__ == '__main__':
    # Initialize pygame first
    pygame.init()
    pygame.font.init()
    
    # Then create the display window
    win = pygame.display.set_mode((s_width, s_height))
    pygame.display.set_caption('Tetris')

    try:
        # Start the game
        main_menu(win)
    except Exception as e:
        print(f"Game error: {e}")
    finally:
        # Make sure pygame quits properly
        pygame.quit()
