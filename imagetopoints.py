from math import ceil, floor
from tkinter import Tk, StringVar, Frame, Button, Spinbox, Text, END
from tkinter import filedialog, messagebox
from traceback import print_exc
from threading import Thread, Event
from typing import Any
from PIL import Image
import numpy as np


COLOR = "#36393f"
BRAILLE = (
    "⠀⢀⡀⣀⠠⢠⡠⣠⠄⢄⡄⣄⠤⢤⡤⣤⠐⢐⡐⣐⠰⢰⡰⣰⠔⢔⡔⣔⠴⢴⡴⣴⠂⢂⡂⣂⠢⢢⡢⣢⠆⢆⡆⣆⠦⢦⡦⣦⠒"
    "⢒⡒⣒⠲⢲⡲⣲⠖⢖⡖⣖⠶⢶⡶⣶⠈⢈⡈⣈⠨⢨⡨⣨⠌⢌⡌⣌⠬⢬⡬⣬⠘⢘⡘⣘⠸⢸⡸⣸⠜⢜⡜⣜⠼⢼⡼⣼⠊⢊"
    "⡊⣊⠪⢪⡪⣪⠎⢎⡎⣎⠮⢮⡮⣮⠚⢚⡚⣚⠺⢺⡺⣺⠞⢞⡞⣞⠾⢾⡾⣾⠁⢁⡁⣁⠡⢡⡡⣡⠅⢅⡅⣅⠥⢥⡥⣥⠑⢑⡑"
    "⣑⠱⢱⡱⣱⠕⢕⡕⣕⠵⢵⡵⣵⠃⢃⡃⣃⠣⢣⡣⣣⠇⢇⡇⣇⠧⢧⡧⣧⠓⢓⡓⣓⠳⢳⡳⣳⠗⢗⡗⣗⠷⢷⡷⣷⠉⢉⡉⣉"
    "⠩⢩⡩⣩⠍⢍⡍⣍⠭⢭⡭⣭⠙⢙⡙⣙⠹⢹⡹⣹⠝⢝⡝⣝⠽⢽⡽⣽⠋⢋⡋⣋⠫⢫⡫⣫⠏⢏⡏⣏⠯⢯⡯⣯⠛⢛⡛⣛⠻"
    "⢻⡻⣻⠟⢟⡟⣟⠿⢿⡿⣿"
)


class App(Tk):

    def __init__(self) -> None:
        Tk.__init__(self)

        self.image = Image.new("L", (0, 0), (0))
        self.event = Event()
        self.seuil = StringVar(value="100")
        self.max_char = StringVar(value="2000")
        self.geometry("800x600")
        self.resizable(width=True, height=True)
        self.title("ImageToPoints")
        self.configure(bg=COLOR)
        self.minsize(width=300, height=400)
        self.frame_control = Frame(self, bg=COLOR, height=20, pady=0)
        self.frame_control.pack(side="top", fill="x", ipadx=0)
        self.scale_max_char = Spinbox(self.frame_control, from_=100, to=10000,
                                      increment=100, width=6,
                                      textvariable=self.max_char)
        self.scale_max_char.pack(side="left", fill="both")
        self.scale_seuil = Spinbox(self.frame_control, from_=0, to=256,
                                   increment=1, width=6,
                                   textvariable=self.seuil)
        self.scale_seuil.pack(side="left", fill="both")
        self.button_negative = Button(self.frame_control, text="Négatif",
                                      command=self.swap_negative, width=8,
                                      pady=0)
        self.button_negative.pack(side="left", fill="x")
        self.button_load = Button(self.frame_control, text="Charger",
                                  command=self.load, width=8, pady=0)
        self.button_load.pack(side="left", fill="x")
        self.button_copy = Button(self.frame_control, text="Copier",
                                  command=self.copy_into_clipboard, width=8,
                                  pady=0)
        self.button_copy.pack(side="left", fill="x", expand=True)
        self.text_area = Text(bg=COLOR, pady=0, padx=0, wrap='none',
                              state='disabled', fg="white", relief="flat",
                              font=("Courier", 10, "normal"))
        self.text_area.pack(side="top", fill="both", expand=True, ipadx=0)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.seuil.trace("w", self.update)
        self.max_char.trace("w", self.update)
        self.drawing = False
        self.negative = False
        self.mainloop()

    @property
    def text(self):
        """Get text in text area."""
        return self.text_area.get("1.0", END)

    @text.setter
    def text(self, content: str) -> None:
        """Set text in text area."""
        self.text_area.config(state='normal')
        self.text_area.delete("1.0", END)
        self.text_area.insert('1.0', content)

    def close(self) -> None:
        """Safe close."""
        self.stop_draw()
        self.after(250, lambda: self.destroy())

    def swap_negative(self) -> None:
        """Swap white pixels to black pixel and inversely."""
        self.negative = not self.negative
        self.update()

    def copy_into_clipboard(self) -> None:
        """Copy text into clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self.text)

    def draw(self) -> None:
        """Convert image to text and put it in text area."""
        # get parameters from settings
        try:
            seuil = int(self.seuil.get())
            char_max = int(self.max_char.get())
        except ValueError:
            return
        if 0 in self.image.size or char_max < 100 or char_max > 100_000:
            return

        self.drawing = True
        img = self.image
        bin_value = 0 if self.negative else 1

        # resize image to a size corresponding to the number of characters
        x_img, y_img = img.size
        char_total = (ceil((x_img + 3) / 4) * ceil((y_img + 1) / 2))
        ratio = (char_max / char_total) ** 0.5
        x_len = floor(x_img * ratio)
        y_len = floor(y_img * ratio)
        img_resize = img.resize((x_len - x_len % 2, y_len - y_len % 4))

        # convert image
        width_image_resized, height_image_resized = img_resize.size
        array_gray = np.array(img_resize)
        array = np.where(array_gray >= seuil, bin_value, 0 if bin_value else 1)
        width, height = width_image_resized // 4, height_image_resized // 2

        text = ""
        for x in range(width):
            for y in range(height):

                pixels = array[x * 4:x * 4 + 4, y * 2:y * 2 + 2]
                pixels_flatten = pixels.flatten()[::-1]
                index = sum(b << n for n, b in enumerate(pixels_flatten))
                text += BRAILLE[index]

            text += "\n"
            if not self.drawing:
                return

        # correction for braile wrong monospace
        lines = []
        for line in text.split("\n"):
            temp_line = []
            space_count = 0
            for c in line:
                if c == "⠀":
                    if space_count == 3:
                        space_count = 0
                        temp_line.append("⠀")
                    else:
                        space_count += 1
                temp_line.append(c)
            lines.append("".join(temp_line).rstrip("⠀"))
            if not self.drawing:
                return

        self.text = "\n".join(lines)
        self.drawing = False

    def update(self, *args: Any) -> None:
        """Update draw."""
        self.stop_draw()
        self._thread = Thread(target=self.draw)
        self._thread.start()

    def stop_draw(self) -> None:
        """Stop drawing as quickly as possible."""
        if hasattr(self, "_thread") and self._thread.is_alive():
            self.drawing = False
            self._thread.join()

    def load(self) -> None:
        """Ask path of image and load it."""
        path = filedialog.askopenfilename(title="Open an image",
                                          filetypes=[('All Files', '.*')])
        if path:
            try:
                self.image = Image.open(path).convert("L")
                self.update()
            except Exception as err:
                print_exc()
                messagebox.showerror("An error has occurred", str(err))


if __name__ == "__main__":
    App()
