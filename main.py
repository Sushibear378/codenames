import random
import tkinter as tk

woerter = [
    "kirk", "clanker", "edit", "slop", "AIslop",
    "claude", "charlie", "kirkenses", "panem", "chicken",
    "wings", "what", "naur", "fryrice", "roger",
    "whoop", "belt", "boba", "noodle", "food",
    "water", "yess", "flat", "cooked", "fried"
]

random.shuffle(woerter)

root = tk.Tk()
root.title("grid")

for i in range(5):
    for j in range(5):
        wort = woerter[i * 5 + j]
        label = tk.Label(root, text=wort, width=12, height=3, borderwidth=2, relief="groove")
        label.grid(row=i, column=j, padx=2, pady=2)

root.mainloop()