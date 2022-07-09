import csv
from typing import List, Dict


def str_missing_key(error):
    """Return the name of a missing key from MissingKey exceptions."""
    e = str(error)
    e = e[1:]
    e = e[:-1]
    return e


def is_valid_email(email: str) -> bool:
    """
    Helper function that checks if the input is a string and contains "@"
    Args:
        email: String that you want to know if it's an email or not.

    Returns:
        bool: Is email valid?
    """
    if type(email) is str and "@" in email:
        return True
    else:
        return False


def csv_to_dict(filepath) -> List[Dict]:
    """
    Converts a string filepath of a csv to a list of dicts representing rows of that csv.
    Args:
        filepath: string or pathlib path representing the absolute or relative filepath

    Returns:
        list with a dict per row of csv
    """
    out_list = []
    with open(filepath, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            out_list.append(row)
    return out_list
