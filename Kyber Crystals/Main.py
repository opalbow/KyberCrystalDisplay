# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# Import Statements
import tkinter as tk
from threading import Thread
import time
import datetime
import random
import logging
import traceback
import os
import pandas as pd
from sqlalchemy import create_engine
import math

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# Raspberry Pi Specific Import Statements
if os.name != 'nt':
    import board
    import neopixel


def _from_rgb(rgb):
    """ Routine to translate a rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb


def colour_baselines(colour, colours):
    """ Routine to extract colour values from dictionaries
    """
    r = colours[colour]['red']
    g = colours[colour]['green']
    b = colours[colour]['blue']
    w = colours[colour]['white']
    pixel_r = colours[colour]['glow red']
    pixel_g = colours[colour]['glow green']
    pixel_b = colours[colour]['glow blue']
    pixel_w = colours[colour]['glow white']

    return r, g, b, w, pixel_r, pixel_g, pixel_b, pixel_w


def value_check(colour):
    """ Routine to ensure colour values are within the 0-255 range
    """
    if colour > 255:
        colour = 255
    elif colour < 0:
        colour = 0
    return colour


class Popup(tk.Toplevel):
    def __init__(self, master, text, char):
        tk.Toplevel.__init__(self, master)

        self.config(bg='black')
        self.title(char)

        lbl = tk.Label(self,
                       text=text,
                       bg='black',
                       fg='white',
                       font=('Arial', 25),
                       wraplength=750)
        lbl.pack()

        btn = tk.Button(self, text="OK", command=self.destroy, bg='black', fg='white')
        btn.pack()

        self.transient(master)  # set to be on top of the main window
        self.grab_set()  # hijack all commands from the master (clicks on the main window are ignored)
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        w = int((w-self.winfo_reqwidth())/2)
        h = int((h-self.winfo_reqheight())/2)
        self.geometry("+%d+%s" % (w, h))


class Crystal:
    """ Class to hold all data relating to individual crystals
    """
    def __init__(self, parent_frame, colour, name_, parent, pos, pixel, series_, row_, column_, colours_, descr):
        """ Routine to initialise Class
        """
# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup class variables
        colour = str.lower(colour)
        self.colour = colour
        self.red = 0
        self.green = 0
        self.blue = 0
        self.white = 0
        self.text_red = 255
        self.text_green = 255
        self.text_blue = 255
        self.pos = pos
        self.pixel = pixel
        self.row = row_
        self.column = column_
        self.descr = descr

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup initial crystal colours
        r, g, b, w, \
        self.pixel_red, self.pixel_green, self.pixel_blue, self.pixel_white = colour_baselines(colour, colours_)

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Split character name into rows of up to 13 characters + series number
        if len(name_) >= 13:
            split_name = name_.split()
            temp_display_name = ""
            display_name = ""
            for word in split_name:
                if len(temp_display_name)+len(word) > 13:
                    display_name += temp_display_name + chr(13)
                    temp_display_name = word
                else:
                    temp_display_name += " " + word
            display_name += temp_display_name
        else:
            display_name = name_
        text = display_name + chr(13) + "Series: " + str(series_)

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup command variables & create character button
        command_text = name_+str(pos)
        self.button = tk.Button(master=parent_frame,
                                text=text,
                                command=lambda name=command_text: parent.button_press(name, self.descr))


class MainWindow(tk.Tk):
    """ Class for main program & GUI window
    """
    def __init__(self, *args, **kwargs):
        """ Routine to initialise main program class
        """
        tk.Tk.__init__(self, *args, **kwargs)

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup GUI Window
        w, h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry("%dx%d+0+0" % (w, h))
        self.config(bg='black')
        self.wm_attributes('-fullscreen', 'true')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.frame = tk.Frame(self, bg='black')
        self.frame.grid(row=0, column=0, sticky="news")

        self.grid = tk.Frame(self.frame, bg='black')
        self.grid.grid(sticky="news", column=0, row=7, columnspan=2)

        self.frame.rowconfigure(7, weight=1)
        self.frame.columnconfigure(0, weight=1)

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Database connection & querrying
        engine = create_engine('sqlite:///Crystals.db')
        query = "Select * FROM Crystals Order By Pos ASC"
        crystals = pd.read_sql(query, engine)

        query = "Select * FROM Config"
        config_df = pd.read_sql(query, engine)

        query = "Select * FROM Colours"
        colours_df = pd.read_sql(query, engine)

        query = "Select * FROM Timers"
        timers_df = pd.read_sql(query, engine)

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup variables for Neo Pixel Control
        self.num_pixels = int(crystals['Pixel'].max() + 1)
        if os.name != 'nt':
            pins = {10: board.D10,
                    12: board.D12,
                    18: board.D18,
                    21: board.D21}
            selected_pin = int(config_df[config_df['Name'] == 'GPIO Pin']['Value'])
            print(selected_pin)
            pixel_pin = pins[selected_pin]

            pixel_brightness = float(config_df[config_df['Name'] == 'Brightness']['Value'])
            print(pixel_brightness)

            ORDER = neopixel.GRBW

            self.pixels = neopixel.NeoPixel(
                pixel_pin, self.num_pixels, brightness=pixel_brightness, auto_write=True, pixel_order=ORDER
            )
            self.pixels[0] = (0, 255, 0)
            time.sleep(1)
            self.pixels[0] = (0, 0, 0)

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup dictionary tree for colours - runs quicker than querying DataFrame each time
        self.colours = {}

        for index, df_row in colours_df.iterrows():
            self.colours[df_row.Name] = {'red': df_row.Red,
                                         'green': df_row.Green,
                                         'blue': df_row.Blue,
                                         'white': df_row.White,
                                         'glow red': df_row.Glow_Red,
                                         'glow green': df_row.Glow_Green,
                                         'glow blue': df_row.Glow_Blue,
                                         'glow white': df_row.Glow_White}

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup dictionary timers - runs quicker than querying DataFrame each time
        self.timers = {}

        for index, df_row in timers_df.iterrows():
            self.timers[df_row.Name] = df_row.Value

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup list of enabled sequences
        self.sequences = []
        if int(config_df[config_df['Name'] == 'Left Wave Enabled']['Value']):
            self.sequences.append("left wave")
        if int(config_df[config_df['Name'] == 'Top Left Wave Enabled']['Value']):
            self.sequences.append("top left wave")
        if int(config_df[config_df['Name'] == 'Top Wave Enabled']['Value']):
            self.sequences.append("top wave")
        if int(config_df[config_df['Name'] == 'Top Right Wave Enabled']['Value']):
            self.sequences.append("top right wave")
        if int(config_df[config_df['Name'] == 'Right Wave Enabled']['Value']):
            self.sequences.append("right wave")
        if int(config_df[config_df['Name'] == 'Bottom Right Wave Enabled']['Value']):
            self.sequences.append("bottom right wave")
        if int(config_df[config_df['Name'] == 'Bottom Wave Enabled']['Value']):
            self.sequences.append("bottom wave")
        if int(config_df[config_df['Name'] == 'Bottom Left Wave Enabled']['Value']):
            self.sequences.append("bottom left wave")
        if int(config_df[config_df['Name'] == 'Forward Chain Enabled']['Value']):
            self.sequences.append("forward chain")
        if int(config_df[config_df['Name'] == 'Backward Chain Enabled']['Value']):
            self.sequences.append("backward chain")
        if int(config_df[config_df['Name'] == 'Raindrop Wave Enabled']['Value']):
            self.sequences.append("raindrop wave")
        if int(config_df[config_df['Name'] == 'Random Crystal Enabled']['Value']):
            self.sequences.append("random crystal")

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup crystal varaibles, create Crystal class item for each crystasl entry
        self.max_cols = int(config_df[config_df['Name'] == 'Max Buttons']['Value'] - 1)
        self.crystals = {}
        row = 0
        col = 0

        for index, df_row in crystals.iterrows():
            self.full_row = 0
            name = df_row.Character
            series = df_row.Series
            pos = df_row.Pos
            pixel = df_row.Pixel
            key = name + str(pos)
            descr = df_row.Description
            new_crystal = Crystal(self.frame,
                                  df_row.Colour,
                                  name,
                                  self,
                                  pos,
                                  pixel,
                                  series,
                                  row,
                                  col,
                                  self.colours,
                                  descr)
            new_crystal.button.grid(row=row, column=col, padx=5, pady=5, sticky='news')
            col += 1
            if col > self.max_cols:
                col = 0
                row += 1
                self.full_row = 1
            self.crystals[key] = new_crystal
            self.crystals[key].button.config(bg='black')
            self.crystals[key].button.config(fg='white')
        self.frame.columnconfigure(tuple(range(self.max_cols+1)), weight=1)
        self.frame.rowconfigure(tuple(range(row+1)), weight=1)
        self.max_rows = row

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup of other control variables
        self.pulses = int(config_df[config_df['Name'] == 'Random Crystal Pulses']['Value'] + 1)
        self.kill = 0
        self.block = 0
        self.button = 0
        self.sequence = 0
        self.target_time = datetime.datetime.now()

    def button_press(self, item, text):
        """ Routine for when crystal button is pressed
        """
# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Enable control varaibles to prevent sequences from running, determine character & move mouse away from button
        self.kill = 1
        self.block = 1
        self.button = 1
        char = item
        time.sleep(0.1)
        self.kill = 0
        if len(text) > 0:
            Popup(self, text, char)


# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Start thread to change button & pixel colours
        pulse_timer = self.timers['button press pulses']
        thread = Thread(target=self.threader, args=(char, 1, 4, pulse_timer, ))
        thread.start()

    def mainloop(self):
        """ Routine for main GUI loop
        """
# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Main loop to refresh GUI, determine sequences & update button/ neo pixel colours
        while True:
            # Loop through all characters
            for name in self.crystals.keys():
                # Read in character colour values (button, text & neo pixel)
                red = int(self.crystals[name].red)
                green = int(self.crystals[name].green)
                blue = int(self.crystals[name].blue)
                white = int(self.crystals[name].white)

                pixel_red = int(self.crystals[name].pixel_red)
                pixel_green = int(self.crystals[name].pixel_green)
                pixel_blue = int(self.crystals[name].pixel_blue)
                pixel_white = int(self.crystals[name].pixel_white)
                
                red = value_check(red)
                green = value_check(green)
                blue = value_check(blue)
                white = value_check(white)

                pixel_red = value_check(pixel_red)
                pixel_green = value_check(pixel_green)
                pixel_blue = value_check(pixel_blue)
                pixel_white = value_check(pixel_white)

                # Try statement to update all colours (button, text and pixels)
                try:
                    if white > 0:
                        self.crystals[name].button.configure(bg=_from_rgb((white,
                                                                           white,
                                                                           white)),
                                                             activebackground=_from_rgb((white,
                                                                                         white,
                                                                                         white))
                                                             )
                    else:
                        self.crystals[name].button.configure(bg=_from_rgb((red,
                                                                           green,
                                                                           blue)),
                                                             activebackground=_from_rgb((red,
                                                                                         green,
                                                                                         blue))

                                                             )

                    self.crystals[name].button.configure(fg=_from_rgb((int(self.crystals[name].text_red),
                                                                       int(self.crystals[name].text_green),
                                                                       int(self.crystals[name].text_blue))),
                                                         activeforeground=_from_rgb((int(self.crystals[name].text_red),
                                                                                     int(self.crystals[name].text_green),
                                                                                     int(self.crystals[name].text_blue)))
                                                         )

                    if self.num_pixels - 1 >= self.crystals[name].pixel >= 0 and \
                            os.name != 'nt':
                        self.pixels[self.crystals[name].pixel] = (pixel_red, pixel_green, pixel_blue, pixel_white)

                # Open exception clause to prevent program from crashing - occasional error for colours
                except Exception as e:
                    logging.error(traceback.format_exc())

# ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
            # Check if random delay timer has lapsed and sequence not running/ button not pressed
            if datetime.datetime.now() > self.target_time \
                    and not self.block \
                    and not self.button \
                    and len(self.sequences) > 0:

                # Generate random number to determine sequence to run - run generated sequences
                seq = random.randint(0, len(self.sequences) - 1)

                # Check if sequence selected is the wave sequence starting in middle of left side
                if self.sequences[seq] == "left wave":
                    thread = Thread(target=self.left_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in top left corner
                elif self.sequences[seq] == "top left wave":
                    thread = Thread(target=self.top_left_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in middle of top side
                elif self.sequences[seq] == "top wave":
                    thread = Thread(target=self.top_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in top right corner
                elif self.sequences[seq] == "top right wave":
                    thread = Thread(target=self.top_right_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in middle of right side
                elif self.sequences[seq] == "right wave":
                    thread = Thread(target=self.right_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in bottom right corner
                elif self.sequences[seq] == "bottom right wave":
                    thread = Thread(target=self.bottom_right_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in middle of bottom side
                elif self.sequences[seq] == "bottom wave":
                    thread = Thread(target=self.bottom_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the wave sequence starting in bottom left corner
                elif self.sequences[seq] == "bottom left wave":
                    thread = Thread(target=self.bottom_left_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the chain sequence starting with first neo pixel
                elif self.sequences[seq] == "forward chain":
                    thread = Thread(target=self.chain_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the chain sequence starting with the last neo pixel
                elif self.sequences[seq] == "backward chain":
                    thread = Thread(target=self.reverse_chain_wave)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is the rain drop effect sequence
                elif self.sequences[seq] == "raindrop wave":
                    thread = Thread(target=self.rain_drop_seq)
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, self.timers['between sequences'])

                # Check if sequence selected is random crystal to pulsate
                elif self.sequences[seq] == "random crystal":
                    self.sequence = 1
                    char = (list(self.crystals.keys())[random.randint(0, len(self.crystals.keys())) - 1])
                    thread = Thread(target=self.threader, args=(char, 1, self.pulses, self.timers['button press pulses']))
                    thread.start()
                    self.target_time = datetime.datetime.now() + datetime.timedelta(0, random.randint(1, 10))
                    self.sequence = 0

            # Update screen
            self.update()

    def threader(self, char, blocking, pulse_limit, pulse_timer=0.001):
        """ Routine for calculation thread. Calculating colours for running crytals. Loops until pulse_limit is met
        char: TEXT - Character name for crystal to be pulsed
        blocking: BOOLEAN - To enable blocking whilst running
        pulse_limit: INT - number of times to fully iluminate and return to base level lighting (pulses)
        pulse_timer: FLOAT Default = 0.001 - Timer between pulse steps
        """
        addition = 1
        pulses = 0
        colour = "red"
        try:
            if self.crystals[char].pixel > -1:
                while pulses < pulse_limit and self.kill == 0:
                    if char != 1:
                        colour = self.crystals[char].colour

                        r, g, b, w, pixel_r, pixel_g, pixel_b, pixel_w = colour_baselines(colour, self.colours)

                        self.crystals[char].red += ((r / 255) * addition)
                        self.crystals[char].green += ((g / 255) * addition)
                        self.crystals[char].blue += ((b / 255) * addition)
                        self.crystals[char].white += ((w / 255) * addition)

                        self.crystals[char].text_red = 255 - self.crystals[char].red
                        self.crystals[char].text_green = 255 - self.crystals[char].green
                        self.crystals[char].text_blue = 255 - self.crystals[char].blue

                        if self.crystals[char].red > 253 \
                                or self.crystals[char].green > 253 \
                                or self.crystals[char].blue > 253 \
                                or self.crystals[char].white > 253:
                            addition = -1

                        elif self.crystals[char].red <= 1 \
                                and self.crystals[char].green <= 1 \
                                and self.crystals[char].blue <= 1 \
                                and self.crystals[char].white <=1:
                            addition = 1
                            pulses += 1

                        if self.crystals[char].red < pixel_r:
                            self.crystals[char].pixel_red = pixel_r
                        else:
                            self.crystals[char].pixel_red = self.crystals[char].red

                        if self.crystals[char].blue < pixel_b:
                            self.crystals[char].pixel_blue = pixel_b
                        else:
                            self.crystals[char].pixel_blue = self.crystals[char].blue

                        if self.crystals[char].green < pixel_g:
                            self.crystals[char].pixel_green = pixel_g
                        else:
                            self.crystals[char].pixel_green = self.crystals[char].green

                        if self.crystals[char].white < pixel_w:
                            self.crystals[char].pixel_white = pixel_w
                        else:
                            self.crystals[char].pixel_white = self.crystals[char].white

                        time.sleep(pulse_timer)
        except Exception as e:
            logging.error(traceback.format_exc())

        self.crystals[char].red = 0
        self.crystals[char].green = 0
        self.crystals[char].blue = 0
        self.crystals[char].white = 0
        self.crystals[char].text_red = 255
        self.crystals[char].text_green = 255
        self.crystals[char].text_blue = 255

        r, g, b, w, \
        self.crystals[char].pixel_red, self.crystals[char].pixel_green, self.crystals[char].pixel_blue, \
        self.crystals[char].pixel_white = colour_baselines(colour, self.colours)

        if blocking and self.kill == 0:
            self.block = 0
            self.button = 0

    def left_wave(self):
        """Routine to create a pulsing wave starting in the left
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_rows/2)
                stage = row-stage
                stage = float(stage**2)
                stage = stage**0.5
                stage = int(stage + column)

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)
            self.run_wave(stages,
                          timer=self.timers['left wave stages'],
                          pulse_timer=self.timers['left wave pulses'])

    def right_wave(self):
        """Routine to create a pulsing wave starting in the right
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_rows/2)
                stage = row-stage
                stage = float(stage**2)
                stage = stage**0.5
                stage = int(stage + self.max_cols-column)

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['right wave stages'],
                          pulse_timer=self.timers['right wave pulses'])

    def top_wave(self):
        """Routine to create a pulsing wave starting in the top centre
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_cols/2)
                stage = column-stage
                stage = float(stage**2)
                stage = stage**0.5
                stage = int(stage + row)

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['top wave stages'],
                          pulse_timer=self.timers['top wave pulses'])

    def bottom_wave(self):
        """Routine to create a pulsing wave starting in the top centre
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_cols/2)
                stage = column-stage
                stage = float(stage**2)
                stage = stage**0.5
                stage = int(stage + self.max_rows-row)

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['bottom wave stages'],
                          pulse_timer=self.timers['bottom wave pulses'])

    def top_left_wave(self):
        """Routine to create a pulsing wave starting in the top left
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                if row > column:
                    stage = row
                else:
                    stage = column

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['top left wave stages'],
                          pulse_timer=self.timers['top left wave pulses'])

    def top_right_wave(self):
        """Routine to create a pulsing wave starting in the top right
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                if row > (self.max_cols-column-1):
                    stage = row
                else:
                    stage = self.max_cols-column

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['top right wave stages'],
                          pulse_timer=self.timers['top right wave pulses'])

    def bottom_left_wave(self):
        """Routine to create a pulsing wave starting in the bottom left
        """
        if not self.sequence:
            self.sequence = 1

            if self.full_row:
                max_rows = self.max_rows
            else:
                max_rows = self.max_rows-1

            stages = []
            for char in self.crystals.keys():
                if self.crystals[char].pixel > -1:
                    row = self.crystals[char].row
                    column = self.crystals[char].column
                    if (max_rows-row) > column:
                        stage = (max_rows-row)
                    else:
                        stage = column

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['bottom left wave stages'],
                          pulse_timer=self.timers['bottom left wave pulses'])

    def bottom_right_wave(self):
        """Routine to create a pulsing wave starting in the bottom right
        """
        if not self.sequence:
            self.sequence = 1

            if self.full_row:
                max_rows = self.max_rows
            else:
                max_rows = self.max_rows-1

            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                if (max_rows-row) < (self.max_cols-column):
                    stage = (self.max_cols-column)
                else:
                    stage = (max_rows-row)

                while len(stages) < stage+1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            self.run_wave(stages,
                          timer=self.timers['bottom right wave stages'],
                          pulse_timer=self.timers['bottom right wave pulses'])

    def rain_drop_seq(self):
        """Routine to create a pulsing wave starting in the top left
        """
        if not self.sequence:
            self.sequence = 1
            start_point = random.randint(0, len(self.crystals))
            name = ""
            for char in self.crystals.keys():
                if self.crystals[char].pos == start_point:
                    name = char
            if name != "":
                while self.crystals[name].pixel < 0:
                    start_point = random.randint(0, len(self.crystals))
                    for char in self.crystals.keys():
                        if self.crystals[char].pos == start_point:
                            name = char

                start_row = math.floor((start_point / (self.max_cols + 1)))
                start_col = int(((start_point / (self.max_cols + 1)) - start_row)*(self.max_cols + 1))
                stages = [[start_point]]

                added = 1
                wave = 1

                while added:
                    wave_list = []
                    column_1 = start_col + wave
                    column_2 = start_col - wave
                    rows = []
                    added = 0

                    for x in range(wave+1):
                        rows.append(start_row+x)
                        rows.append(start_row-x)

                    for item in rows:
                        if column_1 <= self.max_cols:
                            if self.max_rows-1 >= item >= 0:
                                pos = (item*(self.max_cols+1))+column_1
                                wave_list.append(pos)
                            pos = (start_row * (self.max_cols + 1)) + column_1
                            wave_list.append(pos)
                            added = 1
                        if column_2 >= 0:
                            if self.max_rows >= item >= 0:
                                pos = (item*(self.max_cols+1))+column_2
                                wave_list.append(pos)
                            pos = (start_row * (self.max_cols + 1)) + column_2
                            wave_list.append(pos)
                            added = 1
                    columns = []
                    row_1 = start_row + wave
                    row_2 = start_row - wave
                    for x in range(wave):
                        columns.append(start_col + x)
                        columns.append(start_col - x)
                    for item in columns:
                        if row_1 <= self.max_rows:
                            if self.max_cols >= item >= 0:
                                pos = (row_1 * (self.max_cols + 1)) + item
                                wave_list.append(pos)
                            pos = (row_1 * (self.max_cols + 1)) + start_col
                            wave_list.append(pos)
                            added = 1

                        if row_2 >= 0:
                            if self.max_cols >= item >= 0:
                                pos = (row_2 * (self.max_cols + 1)) + item
                                wave_list.append(pos)
                            pos = (row_2 * (self.max_cols + 1)) + start_col
                            wave_list.append(pos)
                            added = 1
                    stages.append(wave_list)
                    wave += 1
                self.run_wave(stages,
                              timer=self.timers['raindrop wave stages'],
                              pulse_timer=self.timers['raindrop wave pulses'])

    def chain_wave(self):
        """ Routine to create a chain wave following neo pixel sequence starting a first pixel
        """
        if not self.sequence:
            self.sequence = 1
            self.kill = 1
            self.block = 1
            time.sleep(0.1)
            self.kill = 0

            timer = self.timers['forward chain stages']
            pulse_timer = self.timers['forward chain pulses']

            for neo in range(0, self.num_pixels):
                for name in self.crystals.keys():
                    if self.crystals[name].pixel == neo and not self.button:
                        thread = Thread(target=self.threader, args=(name, 0, 2,pulse_timer,))
                        thread.start()
                time.sleep(timer)
            time.sleep(10)
        self.block = 0
        self.sequence = 0

    def reverse_chain_wave(self):
        """ Routine to create a chain wave following neo pixel sequence starting a last pixel
        """
        if not self.sequence:
            self.sequence = 1
            self.kill = 1
            self.block = 1
            time.sleep(0.1)
            self.kill = 0

            timer = self.timers['backward chain stages']
            pulse_timer = self.timers['backward chain pulses']

            for neo in range(0, self.num_pixels+1):
                for name in self.crystals.keys():
                    if self.crystals[name].pixel == self.num_pixels-neo and not self.button:
                        thread = Thread(target=self.threader, args=(name, 0, 2, pulse_timer,))
                        thread.start()
                time.sleep(timer)
            time.sleep(10)
        self.block = 0
        self.sequence = 0

    def run_wave(self, stages, timer=1, pulse_timer=0.01):
        """Routine to run wave pattern and calculate button colours
        """
        self.kill = 1
        self.block = 1
        time.sleep(0.1)
        self.kill = 0
        for stage in stages:
            if self.button:
                break
            for name in self.crystals.keys():
                if self.button:
                    break
                if self.crystals[name].pos in stage:
                    thread = Thread(target=self.threader, args=(name, 0, 2, pulse_timer))
                    thread.start()
            time.sleep(timer)
        time.sleep(10)
        self.block = 0
        self.sequence = 0


if __name__ == '__main__':
    root = MainWindow()
    root.mainloop()
    screen.moveTo(10, 10)