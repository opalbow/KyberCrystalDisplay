import board
import neopixel
import time

pixel_pin = board.D12

# The number of NeoPixels
num_pixels = 32

# The order of the pixel colors - RGB or GRB. Some NeoPixels have red and green reversed!
# For RGBW NeoPixels, simply change the ORDER to RGBW or GRBW.
ORDER = neopixel.GRBW

pixels = neopixel.NeoPixel(
    pixel_pin, num_pixels, brightness=0.2, auto_write=True, pixel_order=ORDER
)
while 1:
    for pixel in range(num_pixels):
        pixels[pixel] = (255, 0, 0, 0)
        time.sleep(0.5)
        pixels[pixel] = (0, 255, 0, 0)
        time.sleep(0.5)
        pixels[pixel] = (0, 0, 255, 0)
        time.sleep(0.5)
        pixels[pixel] = (0, 0, 0, 255)
        time.sleep(0.5)
        pixels[pixel] = (0, 0, 0, 0)
