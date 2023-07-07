import datetime
import os
from indexer import IndexTable
from Levenshtein import jaro
from error import *
from typing import Tuple, Set, List, Union, Literal

errorhandler = ErrorHandler()


class Search:
    FUZZY_THRESHOLD = 0.80

    def __init__(self, index_table: IndexTable) -> None:
        self.index_table = index_table

    def search_by_keyword(self, keyword: str, fuzzy: bool = False) -> Set[int]:
        """
        Searches the index table based on keyword and it's possible spelling 
        mistakes when `fuzzy` is `True`.
        """
        if not fuzzy:
            files = self.index_table.keywords[keyword]
        else:
            files = set()
            for i in self.index_table.keywords:
                if jaro(i, keyword) >= self.FUZZY_THRESHOLD:
                    files.update(self.index_table.keywords[i])
        return files

    def search_by_name(
        self, name: str, fuzzy: bool = False
    ) -> Union[List[int], Set[int]]:
        """
        Searches the index table for files with a name. By default, it searches
        for an exact name. If `fuzzy` is set to `True`, it prioritizes possible spelling
        mistakes in the name and includes files that have the possible substring
        of the name.
        """
        if not fuzzy:
            files = self.index_table.name[name]
        else:
            files = set()
            substring_check_set = set()
            for i in self.index_table.name:
                if jaro(i, name) >= self.FUZZY_THRESHOLD:
                    files.update(self.index_table.name[i])
                if name in i:
                    substring_check_set.update(self.index_table.name[i])
            substring_check_set.difference_update(files)
            files = list(files)
            files.extend(substring_check_set)
        return files

    def search_by_time(
        self, high: int, low: int, operation: Literal["before", "after", "on"], search_files: Set[int] = None
    ) -> Set[int]:
        """
        Searches files based on the file's modified time and compares to 
        `(low, high)` time constraint on `operation` which is `before`, `after` 
        or `on`. If `search_files` is provided then searches in only those files.
        """
        operation = operation.strip().lower()
        files = set()
        if search_files is None:
            search_files = self.index_table.uid
        for i in search_files:
            if search_files is not None:
                i = self.index_table.files[i].u_meta
            if operation == "before":
                if i.st_mtime <= high:
                    files.update(self.index_table.uid[i])
            elif operation == "after":
                if i.st_mtime >= low:
                    files.update(self.index_table.uid[i])
            elif operation == "on":
                if high >= i.st_mtime >= low:
                    files.update(self.index_table.uid[i])
            else:
                raise ValueError("incorrect operation value")
        return files

    def search_by_multiple_keywords(
        self,
        keywords: List[str],
        date_in_yyyymmdd: str = None,
        time_in_hhmmss: str = None,
        operation: Literal["before", "after", "on"] = None,
    ) -> List[int]:
        """
        Search multiple keywords with fuzzy search and applies time constraint if provided.

        Returns:
            list of file ids in sorted order based on how likely they are close to query
        """
        files = []
        # set of files in to return
        files_set = set()

        # temporary set of files to store result of each intermediate search
        not_fuzzy_sets = []

        # get (low, high) limits of date and time
        epoch_limits = self._get_epoch_limits(date_in_yyyymmdd, time_in_hhmmss)
        is_time_constraint = epoch_limits[0] is not None

        # Assuming larger words are more likely to be on top
        keywords.sort(key=len)
        # Searching without fuzzy search, assuming all spellings are correct
        for i in keywords:
            not_fuzzy_sets.append(self.search_by_keyword(i))

        # Add files which occured in result of every keyword
        files_set = set.intersection(*not_fuzzy_sets)

        if is_time_constraint:
            files_set = self.search_by_time(
                epoch_limits[1], epoch_limits[0], operation, files_set
            )

        # pushing the set of files with correct spelling on top
        files.extend(files_set)

        fuzzy_sets = []
        # Searching with fuzzy search
        for i in keywords:
            fuzzy_sets.append(self.search_by_keyword(i, fuzzy=True))

        # Add files which occured in result of every fuzzy keyword search
        fuzzy_set = set.intersection(*fuzzy_sets)
        fuzzy_set.difference_update(files_set)
        if is_time_constraint:
            fuzzy_set = self.search_by_time(
                epoch_limits[1], epoch_limits[0], operation, fuzzy_set
            )
        files_set.update(fuzzy_set)
        files.extend(fuzzy_set)

        # Add files which occured in result of any keyword
        non_fuzzy_set = set.union(*not_fuzzy_sets)
        non_fuzzy_set.difference_update(files_set)
        if is_time_constraint:
            non_fuzzy_set = self.search_by_time(
                epoch_limits[1], epoch_limits[0], operation, non_fuzzy_set
            )
        files_set.update(non_fuzzy_set)
        files.extend(non_fuzzy_set)

        # Add files which occured in result of any fuzzy keyword search
        fuzzy_set = set.union(*fuzzy_sets)
        fuzzy_set.difference_update(files_set)
        if is_time_constraint:
            fuzzy_set = self.search_by_time(
                epoch_limits[1], epoch_limits[0], operation, fuzzy_set
            )
        files_set.update(fuzzy_set)
        files.extend(fuzzy_set)

        return files

    def print_files(self, files):
        for i in files:
            print(self.index_table.files[i].path)

    def _get_epoch_limits(
        self, date_in_yyyymmdd: str = None, time_in_hhmmss: str = None
    ) -> Tuple[int, int]:
        high = low = None
        second = minutes = hour = 0
        current_date = datetime.date.today()
        year = current_date.year
        month = current_date.month
        day = current_date.day

        if date_in_yyyymmdd is not None:
            try:
                year = int(date_in_yyyymmdd[0:4])
                month = (
                    int(date_in_yyyymmdd[4:6]) if len(date_in_yyyymmdd) >= 5 else None
                )
                day = int(date_in_yyyymmdd[6:8]) if len(date_in_yyyymmdd) == 8 else None
                if month is not None and day is not None:
                    high_date_object = datetime.datetime(year, month, day, 23, 59, 59)
                    low_date_object = datetime.datetime(year, month, day, 0, 0, 0)
                if month is None:
                    high_date_object = datetime.datetime(year, 12, 31, hour, 59, 59)
                    low_date_object = datetime.datetime(year, 1, 1, hour, 0, 0)
                elif day is None:
                    last_day = self._get_last_day_of_month(year, month)
                    high_date_object = datetime.datetime(
                        year, month, last_day, hour, minutes, 59
                    )
                    low_date_object = datetime.datetime(
                        year, month, 1, hour, minutes, 0
                    )
                high = int(high_date_object.timestamp())
                low = int(low_date_object.timestamp())
            except:
                errorhandler.log(INVALID_DATE)

        if time_in_hhmmss is not None:
            try:
                hour = int(time_in_hhmmss[0:2])
                minutes = int(time_in_hhmmss[2:4]) if len(time_in_hhmmss) >= 4 else None
                second = int(time_in_hhmmss[4:6]) if len(time_in_hhmmss) == 6 else None
                if minutes is not None and second is not None:
                    high_date_object = datetime.datetime(
                        year, month, day, hour, minutes, second
                    )
                    low_date_object = datetime.datetime(
                        year, month, day, hour, minutes, second
                    )
                if minutes is None:
                    high_date_object = datetime.datetime(year, month, day, hour, 59, 59)
                    low_date_object = datetime.datetime(year, month, day, hour, 0, 0)
                elif second is None:
                    high_date_object = datetime.datetime(
                        year, month, day, hour, minutes, 59
                    )
                    low_date_object = datetime.datetime(
                        year, month, day, hour, minutes, 0
                    )

                high = int(high_date_object.timestamp())
                low = int(low_date_object.timestamp())
            except:
                errorhandler.log(INVALID_TIME)
        return low, high

    def _get_last_day_of_month(self, year: int, month: int) -> int:
        """ """
        next_month = (month + 1) % 12 or 12
        next_year = year if month != 12 else year + 1
        first_day_next_month = datetime.date(next_year, next_month, 1)
        last_day_current_month = first_day_next_month - datetime.timedelta(days=1)
        return last_day_current_month.day
