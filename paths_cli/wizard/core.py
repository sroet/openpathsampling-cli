import random
from paths_cli.wizard.joke import name_joke
from paths_cli.wizard.tools import a_an

from collections import namedtuple

WizardSay = namedtuple("WizardSay", ['msg', 'mode'])

def name(wizard, obj, obj_type, store_name, default=None):
    wizard.say(f"Now let's name your {obj_type}.")
    name = None
    while name is None:
        name = wizard.ask("What do you want to call it?")
        if name in getattr(wizard, store_name):
            wizard.bad_input(f"Sorry, you already have {a_an(obj_type)} "
                             f"{obj_type} named {name}. Please try another "
                             "name.")
            name = None

    obj = obj.named(name)

    wizard.say(f"'{name}' is a good name for {a_an(obj_type)} {obj_type}. "
               + name_joke(name, obj_type))
    return obj

def abort_retry_quit(wizard, obj_type):
    a_an = a_an(obj_type)
    retry = wizard.ask(f"Do you want to try again to make {a_an} "
                       f"{obj_type}, do you want to continue without, or "
                       f"do you want to quit?",
                       options=["[R]etry", "[C]ontinue", "[Q]uit"])
    if retry == 'q':
        exit()
    elif retry == 'r':
        return
    elif retry == 'c':
        return "continue"
    else:
        raise ImpossibleError()


def interpret_req(req):
    _, min_, max_ = req
    string = ""
    if min_ == max_:
        return str(min_)

    if min_ >= 1:
        string += "at least " + str(min_)

    if max_ < float("inf"):
        if string != "":
            string += " and "
        string += "at most " + str(max_)

    return string


def get_missing_object(wizard, obj_dict, display_name, fallback_func):
    if len(obj_dict) == 0:
        obj = fallback_func(wizard)
    elif len(obj_dict) == 1:
        obj = list(obj_dict.values())[0]
    else:
        objs = list(obj_dict.keys())
        sel = wizard.ask_enumerate(f"Which {display_name} would you like "
                                   "to use?", options=objs)
        obj = obj_dict[sel]
    return obj


def get_object(func):
    def inner(*args, **kwargs):
        obj = None
        while obj is None:
            obj = func(*args, **kwargs)
        return obj
    return inner


