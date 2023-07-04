from Levenshtein import jaro
from rake_nltk import Rake

def is_binary_file(filename):
    textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
    with open(filename, 'rb') as f:
        is_binary_string = bool(f.read(1024).translate(None, textchars))
    return is_binary_string

def get_keywords(filename):
    rake = Rake()
    with open(filename) as f:
        rake.extract_keywords_from_text(f.read())
        return rake.get_ranked_phrases()
    
