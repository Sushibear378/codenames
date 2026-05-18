# assign_words.py
import random
from words import woerter  # words should be a list of at least 25 words

def assign_colors_to_words():
    if len(woerter) < 25:
        raise ValueError("words.py must contain at least 25 words in a list named 'words'.")

    selected_words = random.sample(woerter, 25)
    colors = ['red'] * 8 + ['blue'] * 8 + ['white'] * 8 + ['black']
    random.shuffle(colors)

    assignments = dict(zip(selected_words, colors))
    return assignments

# Example usage:
if __name__ == "__main__":
    assignments = assign_colors_to_words()
    for word, color in assignments.items():
        print(f"{word}: {color}")