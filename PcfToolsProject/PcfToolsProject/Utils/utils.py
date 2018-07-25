#! /usr/bin/env python3
# coding: utf-8

import re

def cleaned_data(str_to_cleaned):
    """ Func to cleaned data from post and get query by security """
    if str_to_cleaned:
        return re.sub("[^a-zA-Z0-9°_+\-*/,\.]", " ", str_to_cleaned)
        # return = re.escape(str_to_cleaned) #this works
        # return = re.sub("[@|#|$|%|^|&|(|)|[|]|{|}|;|/|<|>|`|~]", " ", str_to_cleaned) #this works
    else:
        return None
