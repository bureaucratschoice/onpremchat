import os
import random

def get_random_word_string(n):
    with open('/app/helpers/dic.txt', 'r') as file:
        words = file.readlines()
    return "-".join(random.sample(words,n))



