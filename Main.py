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
    """
    Routine to translate a rgb tuple of int to a tkinter friendly color code
    :param rgb: LIST - values for RGB
    :return: Formatted RGB values
    """
    return "#%02x%02x%02x" % rgb


def colour_baselines(colour, colours):
    """
    Routine to extract colour values from dictionaries
    :param colour: STRING - Colour to be extracted
    :param colours: DICT - Dictionary of colour values
    :return:
        r - INT - max red value
        g - INT - max green value
        b - INT - max blue value
        w - INT - max white value
        pixel_r - INT - base red value for neopixel (idle illumination)
        pixel_g - INT - base green value for neopixel (idle illumination)
        pixel_b - INT - base blue value for neopixel (idle illumination)
        pixel_w - INT - base white value for neopixel (idle illumination)
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
    """
    Routine to ensure colour values are within the 0-255 range
    :param colour: INT - colour value prior to updating button/crystal
    :return: colour - INT - value within range to be used as RGB value
    """
    if colour > 255:
        colour = 255
    elif colour < 0:
        colour = 0
    return colour


class Popup(tk.Toplevel):
    """
    Class for pop up window to display text from crystal slips
    """

    def __init__(self, master, text, char):
        """
        Routine for initialising the popup window
        :param master: OBJ - Parent window (main window) for pop up to sit in front of
        :param text: STRING - Text to be displayed
        :param char: STRING - Name of the selected character/crystal
        """
        tk.Toplevel.__init__(self, master)

        self.config(bg='black')
        self.title(char)
        self.master = master

        lbl = tk.Label(self,
                       text=text,
                       bg='black',
                       fg='white',
                       font=('Arial', 25),
                       wraplength=750)
        lbl.pack()

        btn = tk.Button(self,
                        text="OK",
                        command=self.__button_press__,
                        bg='black',
                        fg='white',
                        width=10,
                        height=2)
        btn.pack()

        self.transient(master)  # set to be on top of the main window
        self.grab_set()  # hijack all commands from the master (clicks on the main window are ignored)
        x = 10
        y = 10
        self.geometry(f"+{x}+{y}")

        self.overrideredirect(True)
        self.lift()

    def __button_press__(self):
        """
        Routine for close button - closes pop up window
        :return: None
        """
        self.master.focus_force()
        self.destroy()


class Crystal:
    """ Class to hold all data relating to individual crystals
    """

    def __init__(self, parent_frame, colour, name_, parent, pos_, pixel_,
                 series_, row_, column_, colours_, descr_, cracked_, cracked_colour_=""):
        """
        Routine to initialise new crystal class instance

        :param parent_frame: OBJ - Parent frame from main window (for button to be packed onto)
        :param colour: STRING - Crystal colour
        :param name_: STRING - Character name for the crystal
        :param parent: OBJ - Parent class for linking button press action
        :param pos_: INT - Button position number (ordering, starting top left going left>right, top>bottom)
        :param pixel_: INT - Pixel position number in chain
        :param series_: INT - Kyber Crystal release series
        :param row_: INT - Row button sits in on display
        :param column_: INT - Column button sits in on display
        :param colours_: DICT - Dictionary of colour values
        :param descr_: STRING - Crystal description text, to be displayed in popup window on button press
        :param cracked_: BOOLEAN - Crystal is a cracked crystal or not
        :param cracked_colour_: STRING - Inner core colour for the cracked crystals
        """
        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup class variables
        self.colour = str.lower(colour)
        self.red = 0
        self.green = 0
        self.blue = 0
        self.white = 0
        self.text_red = 255
        self.text_green = 255
        self.text_blue = 255
        self.pos = pos_
        self.pixel = pixel_
        self.row = row_
        self.column = column_
        self.descr = descr_
        self.cracked = cracked_
        self.cracked_colour = str.lower(cracked_colour_)

        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup initial crystal colours
        r, g, b, w, self.pixel_red, self.pixel_green, self.pixel_blue, self.pixel_white = colour_baselines(self.colour,
                                                                                                           colours_)

        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Split character name into rows of up to 13 characters + series number
        if len(name_) >= 13:
            split_name = name_.split()
            temp_display_name = ""
            display_name = ""
            for word in split_name:
                if len(temp_display_name) + len(word) > 13:
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
        command_text = name_ + str(pos_)
        self.button = tk.Button(master=parent_frame,
                                text=text,
                                relief=tk.FLAT,
                                command=lambda name=command_text: parent.__button_press__(name, self.descr))


class MainWindow(tk.Tk):
    """
    Class for main program & GUI window
    """

    def __init__(self, *args, **kwargs):
        """
        Routine to initialise main program class
        :param args:
        :param kwargs:
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
        # Database connection & querying
        engine = create_engine('sqlite:///Crystals.db')
        query = "Select * FROM Crystals Order By Pos ASC"
        crystals = pd.read_sql(query, engine)

        query = "Select Name, Value FROM Config"
        config_df = pd.read_sql(query, engine)

        query = "Select * FROM Colours"
        colours_df = pd.read_sql(query, engine)

        query = "Select Name, Value FROM Timers"
        self.timers = pd.read_sql(query, engine)

        query = "Select ID, Name, Enable, Routine FROM Sequences WHERE Enable=1"
        self.sequences = pd.read_sql(query, engine)

        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup variables for Neo Pixel Control
        self.num_pixels = int(crystals['Pixel'].max() + 1)
        if os.name != 'nt':
            pins = {10: board.D10,
                    12: board.D12,
                    18: board.D18,
                    21: board.D21}
            selected_pin = int(config_df[config_df['Name'] == 'GPIO Pin']['Value'])
            pixel_pin = pins[selected_pin]

            pixel_brightness = float(config_df[config_df['Name'] == 'Brightness']['Value'])

            order = neopixel.GRBW

            self.pixels = neopixel.NeoPixel(
                pixel_pin, self.num_pixels, brightness=pixel_brightness, auto_write=False, pixel_order=order
            )
            self.pixels[0] = (0, 255, 0)
            self.pixels.write()
            time.sleep(1)
            self.pixels[0] = (0, 0, 0)
            self.pixels.write()

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
        # Setup timer variables
        self.min_between_timer = \
            self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'min between sequences'].item()
        self.max_between_timer = \
            self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'max between sequences'].item()

        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup crystal variables, create Crystal class item for each crystal's entry
        self.max_cols = int(config_df[config_df['Name'] == 'Max Buttons']['Value'] - 1)
        self.crystals = {}
        self.cracked_list = []
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
            cracked = df_row.Cracked
            cracked_colour = df_row.Cracked_Colour
            if cracked_colour is None:
                cracked_colour = ""
            new_crystal = Crystal(parent_frame=self.frame, colour=df_row.Colour, name_=name, parent=self, pos_=pos,
                                  pixel_=pixel, series_=series, row_=row, column_=col, colours_=self.colours,
                                  descr_=descr, cracked_=cracked, cracked_colour_=cracked_colour)
            new_crystal.button.grid(row=row, column=col, padx=5, pady=5, sticky='news')
            col += 1
            if col > self.max_cols:
                col = 0
                row += 1
                self.full_row = 1
            self.crystals[key] = new_crystal
            self.crystals[key].button.config(bg='black')
            self.crystals[key].button.config(fg='white')
            if cracked:
                self.cracked_list.append(key)
        self.frame.columnconfigure(tuple(range(self.max_cols + 1)), weight=1)
        self.frame.rowconfigure(tuple(range(row + 1)), weight=1)
        self.max_rows = row

        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Setup of other control variables
        self.pulses = int(config_df[config_df['Name'] == 'Random Crystal Pulses']['Value'] + 1)
        self.kill = 0
        self.block = 0
        self.button = 0
        self.sequence = 0
        self.target_time = datetime.datetime.now()
        self.illuminate = int(config_df[config_df['Name'] == 'Illuminate buttons']['Value'])

    def __button_press__(self, item, text):
        """
        Routine for when crystal button is pressed
        :param item: INT - Character Index Value
        :param text: STRING - Description Text of crystal (from DB)
        :return: None
        """
        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
        # Enable control variables to prevent sequences from running, determine character
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
        pulse_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'button press pulses'].item()
        thread = Thread(target=self.__wave_threads__, args=(char, 1, 4, pulse_timer,))
        thread.start()

    def mainloop_(self):
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
                    if self.illuminate or self.button:
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
                                                                                         int(self.crystals[
                                                                                                 name].text_green),
                                                                                         int(self.crystals[
                                                                                                 name].text_blue)))
                                                             )

                    if self.num_pixels - 1 >= self.crystals[name].pixel >= 0 and \
                            os.name != 'nt':
                        self.pixels[self.crystals[name].pixel] = (pixel_red, pixel_green, pixel_blue, pixel_white)

                # Open exception clause to prevent program from crashing - occasional error for colours
                except Exception as e:
                    print(e)
                    logging.error(traceback.format_exc())

            # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
            # Check if random delay timer has lapsed and sequence not running/ button not pressed
            if datetime.datetime.now() > self.target_time \
                    and not self.block \
                    and not self.button \
                    and len(self.sequences) > 0:

                # Generate random number to determine sequence to run - run generated sequences
                no_sequences = len(self.sequences.index)-1
                random_seq_no = random.randint(0, no_sequences)
                seq_name = self.sequences.iloc[random_seq_no]['Routine']

                try:
                    sequence = getattr(self, seq_name)
                except AttributeError:
                    raise NotImplementedError

                thread = Thread(target=sequence)
                thread.start()

            # Update screen
            self.update()
            if os.name != 'nt':
                self.pixels.write()

    def __wave_threads__(self, char=0, blocking=0, pulse_limit=1, pulse_timer=0.001):
        """
        Routine for calculation thread. Calculating colours for running crystals. Loops until pulse_limit is met
        :param char: TEXT - Character name for crystal to be pulsed
        :param blocking: BOOLEAN - To enable blocking whilst running
        :param pulse_limit: INT - number of times to fully illuminate and return to base level lighting (pulses)
        :param pulse_timer: FLOAT Default = 0.001 - Timer between pulse steps
        :return: None
        """

        addition = 1
        pulses = 0
        colour = "red"
        pulse_limit += 1
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

                        if self.crystals[char].white > 0:
                            self.crystals[char].text_red = 255 - self.crystals[char].white
                            self.crystals[char].text_green = 255 - self.crystals[char].white
                            self.crystals[char].text_blue = 255 - self.crystals[char].white

                        if self.crystals[char].red > 253 \
                                or self.crystals[char].green > 253 \
                                or self.crystals[char].blue > 253 \
                                or self.crystals[char].white > 253:
                            addition = -1

                        elif self.crystals[char].red <= 1 \
                                and self.crystals[char].green <= 1 \
                                and self.crystals[char].blue <= 1 \
                                and self.crystals[char].white <= 1:
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
            print(e)
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

    def __cracked_wave_threads__(self, char=0, blocking=0, cracked_colour='red', stages=1, stage=1):
        """
        Routine for calculation thread. Calculating colours for running crystals. Run conditions for cracked corruption
        :param char: TEXT - Character name for crystal to be pulsed
        :param blocking: BOOLEAN - To enable blocking whilst running
        :param cracked_colour: INT - number of times to fully illuminate and return to base level lighting (pulses)
        :param stages: FLOAT Default = 0.001 - Timer between pulse steps
        :param stage: Int - Current stage number in running sequence
        :return: None
        """

        pulses = 0

        og_colour = self.crystals[char].colour

        colour = og_colour

        try:
            if self.crystals[char].pixel > -1:
                while pulses < 2 and self.kill == 0:

                    if char != 1:

                        if colour == og_colour:
                            colour = cracked_colour
                        else:
                            colour = og_colour

                        r, g, b, w, pixel_r, pixel_g, pixel_b, pixel_w = colour_baselines(colour, self.colours)

                        self.crystals[char].red = r
                        self.crystals[char].green = g
                        self.crystals[char].blue = b
                        self.crystals[char].white = w

                        self.crystals[char].text_red = 255 - self.crystals[char].red
                        self.crystals[char].text_green = 255 - self.crystals[char].green
                        self.crystals[char].text_blue = 255 - self.crystals[char].blue
                        if self.crystals[char].white > 0:
                            self.crystals[char].text_red = 255 - self.crystals[char].white
                            self.crystals[char].text_green = 255 - self.crystals[char].white
                            self.crystals[char].text_blue = 255 - self.crystals[char].white

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

                        stage_timer = self.timers['Value'].to_numpy()[
                            self.timers['Name'].to_numpy() == 'cracked stages'].item()
                        time.sleep(
                            stage_timer*((stages-stage)+1)
                        )
                    pulses += 1
        except Exception as e:
            print(e)
            logging.error(traceback.format_exc())
        stage_timer = self.timers['Value'].to_numpy()[
            self.timers['Name'].to_numpy() == 'cracked stages'].item()

        time.sleep(
            stage_timer* stage
        )

        self.crystals[char].red = 0
        self.crystals[char].green = 0
        self.crystals[char].blue = 0
        self.crystals[char].white = 0
        self.crystals[char].text_red = 255
        self.crystals[char].text_green = 255
        self.crystals[char].text_blue = 255

        colour = self.crystals[char].colour

        r, g, b, w, \
            self.crystals[char].pixel_red, self.crystals[char].pixel_green, self.crystals[char].pixel_blue, \
            self.crystals[char].pixel_white = colour_baselines(colour, self.colours)

        if blocking and self.kill == 0:
            self.block = 0
            self.button = 0

    def __left_wave__(self):
        """
        Routine to create a pulsing wave starting in the left
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_rows / 2)
                stage = row - stage
                stage = float(stage ** 2)
                stage = stage ** 0.5
                stage = int(stage + column)

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'left wave stages'].item()
            pulses_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'left wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __right_wave__(self):
        """
        Routine to create a pulsing wave starting in the right
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_rows / 2)
                stage = row - stage
                stage = float(stage ** 2)
                stage = stage ** 0.5
                stage = int(stage + self.max_cols - column)

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'right wave stages'].item()
            pulses_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'right wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __top_wave__(self):
        """
        Routine to create a pulsing wave starting in the top centre
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_cols / 2)
                stage = column - stage
                stage = float(stage ** 2)
                stage = stage ** 0.5
                stage = int(stage + row)

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'top wave stages'].item()
            pulses_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'top wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __bottom_wave__(self):
        """
        Routine to create a pulsing wave starting in the bottom centre
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                stage = math.floor(self.max_cols / 2)
                stage = column - stage
                stage = float(stage ** 2)
                stage = stage ** 0.5
                stage = int(stage + self.max_rows - row)

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'bottom wave stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'bottom wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __top_left_wave__(self):
        """
        Routine to create a pulsing wave starting in the top left
        :return: None
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

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'top left wave stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'top left wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __top_right_wave__(self):
        """
        Routine to create a pulsing wave starting in the top right
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                if row > (self.max_cols - column - 1):
                    stage = row
                else:
                    stage = self.max_cols - column

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'top right wave stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'top right wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __bottom_left_wave__(self):
        """
        Routine to create a pulsing wave starting in the bottom left
        :return: None
        """
        if not self.sequence:
            self.sequence = 1

            if self.full_row:
                max_rows = self.max_rows
            else:
                max_rows = self.max_rows - 1

            stages = []
            stage = 0
            for char in self.crystals.keys():
                if self.crystals[char].pixel > -1:
                    row = self.crystals[char].row
                    column = self.crystals[char].column
                    if (max_rows - row) > column:
                        stage = (max_rows - row)
                    else:
                        stage = column

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'bottom left wave stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'bottom left wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __bottom_right_wave__(self):
        """
        Routine to create a pulsing wave starting in the bottom right
        :return: None
        """
        if not self.sequence:
            self.sequence = 1

            if self.full_row:
                max_rows = self.max_rows
            else:
                max_rows = self.max_rows - 1

            stages = []
            for char in self.crystals.keys():
                row = self.crystals[char].row
                column = self.crystals[char].column
                if (max_rows - row) < (self.max_cols - column):
                    stage = (self.max_cols - column)
                else:
                    stage = (max_rows - row)

                while len(stages) < stage + 1:
                    stages.append([])
                if not self.crystals[char].pos in stages[stage] and \
                        self.crystals[char].pixel > -1:
                    stages[stage].append(self.crystals[char].pos)

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'bottom right wave stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'bottom right wave pulses'].item()
            self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, stage_timer)

    def __rain_drop_seq__(self):
        """
        Routine to create a pulsing wave starting at a random crystal and radiating out like a rain drop
        :return: None
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
                start_col = int(((start_point / (self.max_cols + 1)) - start_row) * (self.max_cols + 1))
                stages = [[start_point]]

                added = 1
                wave = 1

                while added:
                    wave_list = []
                    column_1 = start_col + wave
                    column_2 = start_col - wave
                    rows = []
                    added = 0

                    for x in range(wave + 1):
                        rows.append(start_row + x)
                        rows.append(start_row - x)

                    for item in rows:
                        if column_1 <= self.max_cols:
                            if self.max_rows - 1 >= item >= 0:
                                pos = (item * (self.max_cols + 1)) + column_1
                                wave_list.append(pos)
                            pos = (start_row * (self.max_cols + 1)) + column_1
                            wave_list.append(pos)
                            added = 1
                        if column_2 >= 0:
                            if self.max_rows >= item >= 0:
                                pos = (item * (self.max_cols + 1)) + column_2
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
                stage_timer = self.timers['Value'].to_numpy()[
                    self.timers['Name'].to_numpy() == 'raindrop wave stages'].item()
                pulses_timer = self.timers['Value'].to_numpy()[
                    self.timers['Name'].to_numpy() == 'raindrop wave pulses'].item()
                self.__run_wave__(stages, timer=stage_timer, pulse_timer=pulses_timer)

                self.target_time = datetime.datetime.now() + \
                                   datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                        self.max_between_timer)) + \
                                   datetime.timedelta(0, stage_timer)

    def __cracked_seq__(self):
        """
        Routine to create a wave of corruption starting from random cracked crystal
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            start_point = random.randint(0, len(self.cracked_list)-1)
            name = self.cracked_list[start_point]
            cracked_colour = self.crystals[name].cracked_colour

            if name != "":
                start_point = self.crystals[name].pos
                start_row = math.floor((start_point / (self.max_cols + 1)))
                start_col = int(((start_point / (self.max_cols + 1)) - start_row) * (self.max_cols + 1))
                stages = [[start_point]]

                added = 1
                wave = 1

                while added:
                    wave_list = []
                    column_1 = start_col + wave
                    column_2 = start_col - wave
                    rows = []
                    added = 0

                    for x in range(wave + 1):
                        rows.append(start_row + x)
                        rows.append(start_row - x)

                    for item in rows:
                        if column_1 <= self.max_cols:
                            if self.max_rows - 1 >= item >= 0:
                                pos = (item * (self.max_cols + 1)) + column_1
                                wave_list.append(pos)
                            pos = (start_row * (self.max_cols + 1)) + column_1
                            wave_list.append(pos)
                            added = 1
                        if column_2 >= 0:
                            if self.max_rows >= item >= 0:
                                pos = (item * (self.max_cols + 1)) + column_2
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

                stage_timer = self.timers['Value'].to_numpy()[
                    self.timers['Name'].to_numpy() == 'cracked stages'].item()
                self.__run_wave__(stages, timer=stage_timer, pulse_timer=0.00001, cracked=1,
                                  cracked_colour=cracked_colour)
                self.target_time = datetime.datetime.now() + \
                                   datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                        self.max_between_timer)) + \
                                   datetime.timedelta(0, stage_timer)

    def __chain_wave__(self):
        """
        Routine to create a chain wave following neo pixel sequence starting a first pixel
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            self.kill = 1
            self.block = 1
            time.sleep(0.1)
            self.kill = 0

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'forward chain stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'forward chain pulses'].item()

            for neo in range(0, self.num_pixels):
                for name in self.crystals.keys():
                    if self.crystals[name].pixel == neo and not self.button:
                        thread = Thread(target=self.__wave_threads__, args=(name, 0, 1, pulses_timer,))
                        thread.start()
                time.sleep(stage_timer)

            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, pulses_timer * (510 + 127.5))

        self.block = 0
        self.sequence = 0

    def __reverse_chain_wave__(self):
        """
        Routine to create a chain wave following neo pixel sequence starting a last pixel
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            self.kill = 1
            self.block = 1
            time.sleep(0.1)
            self.kill = 0

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'backward chain stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'backward chain pulses'].item()

            for neo in range(0, self.num_pixels + 1):
                for name in self.crystals.keys():
                    if self.crystals[name].pixel == self.num_pixels - neo and not self.button:
                        thread = Thread(target=self.__wave_threads__, args=(name, 0, 1, pulses_timer,))
                        thread.start()
                time.sleep(stage_timer)
            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, pulses_timer * (510 + 127.5))
        self.block = 0
        self.sequence = 0

    def __centre_chain_wave__(self):
        """
        Routine to create a chain wave following neo pixel sequence starting a middle pixel
        :return: None
        """
        if not self.sequence:
            self.sequence = 1
            self.kill = 1
            self.block = 1
            time.sleep(0.1)
            self.kill = 0

            stage_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'centre chain stages'].item()
            pulses_timer = \
                self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'centre chain pulses'].item()

            start = 1

            lower_pixel = int(self.num_pixels / 2)
            upper_pixel = int(self.num_pixels / 2)
            while lower_pixel > -1 and upper_pixel <= self.num_pixels:
                for name in self.crystals.keys():
                    if start and self.crystals[name].pixel == lower_pixel and not self.button:
                        thread = Thread(target=self.__wave_threads__, args=(name, 0, 1, pulses_timer,))
                        thread.start()
                        start = 0
                    else:
                        if self.crystals[name].pixel == lower_pixel and not self.button:
                            thread = Thread(target=self.__wave_threads__, args=(name, 0, 1, pulses_timer,))
                            thread.start()
                        if self.crystals[name].pixel == upper_pixel and not self.button:
                            thread = Thread(target=self.__wave_threads__, args=(name, 0, 1, pulses_timer,))
                            thread.start()
                lower_pixel -= 1
                upper_pixel += 1

                time.sleep(stage_timer)
            self.target_time = datetime.datetime.now() + \
                               datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                    self.max_between_timer)) + \
                               datetime.timedelta(0, pulses_timer * (510 + 127.5))
        self.block = 0
        self.sequence = 0

    def __random_crystal__(self):
        """
        Routine to pulsate all crystals in a random order
        :return: None
        """
        stages = []
        while len(stages) < self.num_pixels:
            rand_crystal = random.randint(0, self.num_pixels)
            if not [item for item in stages if rand_crystal in item]:
                stages.append([rand_crystal])

        pulses_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'button press pulses'].item()
        stage_timer = self.timers['Value'].to_numpy()[self.timers['Name'].to_numpy() == 'random stages'].item()

        thread = Thread(target=self.__run_wave__, args=(stages,
                                                        stage_timer,
                                                        pulses_timer,
                                                        self.pulses))
        thread.start()

        stage_timer = ((pulses_timer * (510 + 127.5)) * (self.pulses + 1)) + (stage_timer * len(stages))
        self.target_time = datetime.datetime.now() + \
                           datetime.timedelta(0, random.randint(self.min_between_timer,
                                                                self.max_between_timer)) + \
                           datetime.timedelta(0, stage_timer)

    def __run_wave__(self, stages, timer=1, pulse_timer=0.01, pulses=1, cracked=0, cracked_colour=""):
        """
        Routine to run wave pattern and start calculation threads for each crystal
        :param stages: INT - number of stages in the wave pattern
        :param timer: FLOAT - time to wait between running each stage
        :param pulse_timer: FLOAT - time to wait between each calculation step for colours
        :param pulses: INT - number of times for the crystals to pulsate to max brightness
        :param cracked: BOOLEAN - running cracked wave sequence or not
        :param cracked_colour: STRING - Cracked crystal colour (the colour to run calculations for when cracked pattern)
        :return: None
        """
        self.kill = 1
        self.block = 1
        time.sleep(0.1)
        self.kill = 0

        total_stages = len(stages)-1
        stage_no = 0

        for stage in stages:
            if self.button:
                break
            for name in self.crystals.keys():
                if self.button:
                    break
                if self.crystals[name].pos in stage:
                    if cracked:
                        thread = Thread(target=self.__cracked_wave_threads__,
                                        args=(name, 0, cracked_colour, total_stages, stage_no))
                        thread.start()
                    else:
                        thread = Thread(target=self.__wave_threads__, args=(name, 0, pulses, pulse_timer))
                        thread.start()
            time.sleep(timer)
            stage_no += 1
        time.sleep(10)
        self.block = 0
        self.sequence = 0


if __name__ == '__main__':
    root = MainWindow()
    root.mainloop_()
