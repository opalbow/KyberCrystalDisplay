The code for the screen & NeoPixel control will not work with Rasberry Pi 5's. This is due to a change in how the GPIO pins are controlled. This is out of my control and a limitation on the NeoPixel python library.

Please do not rename any of the files or items within the database. This will break the program. Inside the database file you can adjust the coloumns with values. I will provide a seperate file detailing how to update the database to customise how your program runs.

For refernce all code has been tested on Python version = 3.7.4 & 3.9.2

Prior to running the code you will need to install a series of python libraries. Open a terminal and please use the following commands;

	sudo pip3 install rpi_ws281x adafruit-circuitpython-neopixel
	sudo python3 -m pip install --force-reinstall adafruit-blinka

	sudo pip3 uninstall pandas
	sudo pip3 install pandas== 1.3.5
	sudo pip3 uninstall sqlalchemy
	sudo pip3 install sqlalchemy== 1.4.52

You may have to install other python libraries. The best method to find out what you need to install is to place the program file & data base file into a folder on the r-pi (say home folder). Then use the following commands in the terminal. Please change the first line to be the file path for where you have saved the python code & data base;

cd /pi/home 
sudo python Main.py

either the program will start and you will see the GUI load up correctly, or you will get an error message in the terminal window. If you get an error message in the terminal sayng no module with name xyz then that library will need to be installed with a sudo pip3 install *module name* command.
