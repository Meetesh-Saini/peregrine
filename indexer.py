import os
from sys import platform
import pickle
from typing import Dict, Union
from rake_nltk import Rake


class State(object):
    __slots__ = ("free_slots", "lastid")

    def __init__(self, free_slots: set = set(), lastid: int = -1) -> None:
        # set of all ids which are not in use by any file
        # Id is set to be free when any file is deleted
        self.free_slots = free_slots
        # Last assigned id
        self.lastid = lastid

    def get_nextid(self):
        self.lastid += 1
        return self.lastid
    
    def __str__(self) -> str:
        return f"State(\n  free_slots: {self.free_slots},\n  lastid: {self.lastid}\n)"


class Metadata(object):
    __slots__ = ("keywords", "user_keywords", "path", "u_meta")

    def __init__(self, keywords: set, user_keywords : set, path: str, u_meta : Union[os.stat_result, None]) -> None:
        self.keywords = keywords
        self.user_keywords = user_keywords
        # full path of the file relative to peregrine home
        self.path = path
        # unique metadata
        # inode and device id for linux
        self.u_meta = u_meta

    def __str__(self) -> str:
        return f"Metadata(\n  keywords: {self.keywords},\n user_keywords: {self.user_keywords},\n  path: {self.path},\n  u_meta: {self.u_meta}\n)"


class IndexTable(object):
    __slots__ = ("state", "files", "name", "keywords", "path", "uid")

    def __init__(
        self,
        state: State = State(),
        files: Dict[int, Metadata] = {},
        name: Dict[str, set] = {},
        keywords: Dict[str, set] = {},
        path: Dict[str, int] = {},
        uid: Dict[os.stat_result, int] = {},
    ) -> None:
        # metadata stored by peregrine for its usage
        self.state = state

        # file metadata with mapping id->Metadata
        # where id is unique id assigned by peregrine
        # mapping type: int -> Metadata
        self.files = files

        # mapping of file name->ids which have same name
        # mapping type: str -> set(int)
        self.name = name

        # mapping of keywords->ids which are related to that keyword
        # mapping type: str -> set(int)
        self.keywords = keywords

        # full path from peregrine home -> id
        # mapping type: str -> int
        self.path = path

        # mapping from system unique identifier -> peregrine id
        # mapping type: os.stat_result -> int
        self.uid = uid

    def __str__(self) -> str:
        files_str = "\n  ".join([f"{k}: {str(v)}" for k,v in self.files.items()])
        return f"IndexTable(\n  state: {str(self.state)},\n  files: {{\n  {files_str}\n  }},\n  name: {self.name},\n  keywords: {self.keywords},\n  path: {self.path},\n  uid: {self.uid}\n)"



class Indexer:
    """
    To index files and directories present in the peregrine home.
    """

    index_table = IndexTable()

    CURRENT_DIRECTORY = ""
    HOME_DIRECTORY = ""
    # *nix system, assumes file system which *nix system is using supports inodes
    NIX = True

    def __init__(self, home_directory) -> None:
        self.HOME_DIRECTORY = os.path.abspath(os.path.expanduser(home_directory))
        self.CURRENT_DIRECTORY = self.HOME_DIRECTORY
        if platform == "linux" or platform == "linux2" or platform == "darwin":
            self.NIX = True
        else:
            self.NIX = False

    def get_unique_metadata(self, file):
        """
        Returns unique metadata for file or directory
        Returns inode, id of device and number of links for linux
        """
        if self.NIX:
            return os.stat(file)
        else:
            return None

    def is_binary_file(self, filename):
        """
        Checks if file is a binary file
        """
        textchars = bytearray(
            {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F}
        )
        with open(filename, "rb") as f:
            is_binary_string = bool(f.read(1024).translate(None, textchars))
        return is_binary_string

    def get_keywords(self, filename):
        """
        Extracts keyword phrases from text file using RAKE
        """
        rake = Rake()
        with open(filename) as f:
            rake.extract_keywords_from_text(f.read())
            return rake.get_ranked_phrases()

    def index_file(self, filename):
        """
        Index the file and add entry to IndexTable
        """

        full_filepath = os.path.join(self.CURRENT_DIRECTORY, filename)
        filepath = os.path.relpath(full_filepath, self.HOME_DIRECTORY)
        tracked_file = filepath in self.index_table.path

        unique_id = None
        if tracked_file:
            unique_id = self.index_table.path[filepath]
            old_keywords = self.index_table.files[unique_id].keywords
        
            cur_stat = self.get_unique_metadata(full_filepath)
            stat = self.index_table.files[unique_id].u_meta
            if cur_stat.st_ino == stat.st_ino and cur_stat.st_mtime == stat.st_mtime:
                return

        # extract keywords from file if it is text file
        keywords = set()
        if not self.is_binary_file(full_filepath):
            try:
                keywords = set(" ".join(self.get_keywords(full_filepath)).split())
            except:
                pass

        #
        if not tracked_file:
            # check if any free slot for unique id is there
            free_slots = self.index_table.state.free_slots
            if bool(free_slots):
                unique_id = free_slots.pop()
            else:
                # get next unique id for file entry
                unique_id = self.index_table.state.get_nextid()

            old_keywords = set()

            self.index_table.files[unique_id] = Metadata(keywords, set(), filepath, self.get_unique_metadata(full_filepath))

        keywords.update(self.index_table.files[unique_id].user_keywords)
        self.index_table.files[unique_id].keywords = keywords
        for i in old_keywords - keywords:  # in old keywords but not in new keywords
            if i not in self.index_table.keywords:
                self.index_table.keywords[i] = set()
            self.index_table.keywords[i].discard(unique_id)
        for i in keywords - old_keywords:  # in new keywords but not in old keywords
            if i not in self.index_table.keywords:
                self.index_table.keywords[i] = set()
            self.index_table.keywords[i].update((unique_id,))
        
        if filename in self.index_table.name:
            self.index_table.name[filename].update((unique_id,))
        else:
            self.index_table.name[filename] = {unique_id,}
        
        self.index_table.path[filepath] = unique_id

        # Required to store u_meta to id mapping, to detect renaming and deletion of files.
        self.index_table.uid[self.index_table.files[unique_id].u_meta] = unique_id

    def index_directory(self, dirname=""):
        full_dirpath = os.path.join(self.CURRENT_DIRECTORY, dirname)
        temp_current_dir = self.CURRENT_DIRECTORY

        self.CURRENT_DIRECTORY = full_dirpath
        for entry in os.listdir(full_dirpath):
            full_entry_path = os.path.join(full_dirpath, entry)
            if os.path.isdir(full_entry_path):
                self.index_directory(entry)
            elif os.path.isfile(full_entry_path):
                self.index_file(entry)
        
        self.CURRENT_DIRECTORY = temp_current_dir


    def dump(self, file):
        pickle.dump(self.index_table, file)
    
    def load(self, file):
        self.index_table = pickle.load(file)