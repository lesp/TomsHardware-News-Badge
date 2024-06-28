from picographics import PicoGraphics, DISPLAY_INKY_PACK as DISPLAY  # 7.3"
import network
import secrets
import uasyncio
from urllib import urequest
import gc
import qrcode
import time

# WI-Fi Setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(secrets.SSID, secrets.PASSWORD)
time.sleep(5)
print(wlan.isconnected())
URL = "https://www.tomshardware.com/feeds/all"
# Length of time between updates in Seconds.
# Frequent updates will reduce battery life!
UPDATE_INTERVAL = 60 * 5

graphics = PicoGraphics(DISPLAY)
WIDTH, HEIGHT = graphics.get_bounds()
graphics.set_font("bitmap6")
code = qrcode.QRCode()

def status_handler(mode, status, ip):
    print(mode, status, ip)


def read_until(stream, char):
    result = b""
    while True:
        c = stream.read(1)
        if c == char:
            return result
        result += c


def discard_until(stream, c):
    while stream.read(1) != c:
        pass


def parse_xml_stream(s, accept_tags, group_by, max_items=3):
    tag = []
    text = b""
    count = 0
    current = {}
    while True:
        char = s.read(1)
        if len(char) == 0:
            break

        if char == b"<":
            next_char = s.read(1)

            # Discard stuff like <?xml vers...
            if next_char == b"?":
                discard_until(s, b">")
                continue

            # Detect <![CDATA
            elif next_char == b"!":
                s.read(1)  # Discard [
                discard_until(s, b"[")  # Discard CDATA[
                text = read_until(s, b"]")
                discard_until(s, b">")  # Discard ]>
                gc.collect()

            elif next_char == b"/":
                current_tag = read_until(s, b">")
                top_tag = tag[-1]

                # Populate our result dict
                if top_tag in accept_tags:
                    current[top_tag.decode("utf-8")] = text.decode("utf-8")

                # If we've found a group of items, yield the dict
                elif top_tag == group_by:
                    yield current
                    current = {}
                    count += 1
                    if count == max_items:
                        return
                tag.pop()
                text = b""
                gc.collect()
                continue

            else:
                current_tag = read_until(s, b">")
                tag += [next_char + current_tag.split(b" ")[0]]
                text = b""
                gc.collect()

        else:
            text += char


def measure_qr_code(size, code):
    w, h = code.get_size()
    module_size = int(size / w)
    return module_size * w, module_size


def draw_qr_code(ox, oy, size, code):
    size, module_size = measure_qr_code(size, code)
    graphics.set_pen(14)
    graphics.rectangle(ox, oy, size, size)
    graphics.set_pen(0)
    for x in range(size):
        for y in range(size):
            if code.get_module(x, y):
                graphics.rectangle(ox + x * module_size, oy + y * module_size, module_size, module_size)


def get_rss():
    try:
        stream = urequest.urlopen(URL)
        output = list(parse_xml_stream(stream, [b"title", b"description", b"link", b"pubDate"], b"item"))
        return output

    except OSError as e:
        print(e)
        return False


#rtc.enable_timer_interrupt(True)

while True:
    # Gets Feed Data
    feed = get_rss()

    # Clear the screen
    graphics.set_pen(15)
    graphics.clear()
    graphics.set_pen(0)

    # Title
    graphics.text("Tom's Hardware News:", 50, 0, 300, 2)

    # Display the latest article
    if feed:
        headline = feed[0]["title"]
        print(headline)
        if "—" in headline:
            print("Found em dash")
            headline = headline.replace("—","-",1)
            print(headline)
        else:
            print("Not found")
        graphics.set_pen(0)
        graphics.text(headline, 5, 20, WIDTH - 110, 2)
        code.set_text(feed[0]["link"])
        draw_qr_code(WIDTH - 110, 25, 100, code)

    else:
        graphics.set_pen(0)
        graphics.text("Error: Unable to get feed :(", 10, 40, WIDTH - 150, 4)

    graphics.update()

    # Time to have a little nap until the next update
    time.sleep(UPDATE_INTERVAL)