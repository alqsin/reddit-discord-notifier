import configparser
import os

class Auth:
    def __init__(self,AUTH_FILE='auth.ini'):
        self.AUTH_FILE = AUTH_FILE
        self.read_auth()
    def __getitem__(self,key):
        '''Returns a section from auth_dict.'''
        return self.auth_dict[key]
    def read_auth(self):
        '''Refreshes stored auth.'''
        self.auth_dict = read_config_as_dict(self.AUTH_FILE)

def read_config_as_dict(file):
    '''Reads config file, using section names as keys and section contents
    as values for a dict.'''
    config = configparser.ConfigParser()
    config.read(file)
    config_dict = {}
    for section in config.sections():
        curr_entry = {}
        for key in config[section]:
            curr_entry[key] = config[section][key]
        config_dict[section] = curr_entry
    return config_dict

def read_config_as_list(file):
    '''Reads config file, ignoring names of sections, and with each section as
    an entry in a list.'''
    config = configparser.ConfigParser()
    config.read(file)
    config_list = []
    for section in config.sections():
        curr_entry = {}
        for key in config[section]:
            curr_entry[key] = config[section][key]
        config_list.append(curr_entry)
    return config_list

def safe_write_config(file,config):
    '''Writes config to file by means of a temporary file.'''
    with open(file+' temp','w') as config_file:
        config.write(config_file)
    os.replace(file+' temp',file)

def write_config_from_list(file,config_list):
    '''Writes config from a list with numerical, ordered section names.'''
    config = configparser.ConfigParser()
    i = 1
    for config_item in config_list:
        config.add_section(str(i))
        for (key,item) in config_item.items():
            config[str(i)][str(key)] = item
        i += 1
    safe_write_config(file,config)

def add_config_item(file,new_item):
    '''Adds a new item to config file.'''
    config = configparser.ConfigParser()
    if not os.path.exists(file):
        raise ValueError('No such file!')
    config.read(file)
    curr_num_entries = len(config.sections())  # add some validation here?
    config.add_section(str(curr_num_entries+1))  # this works assuming current entries are named in [1,curr_num_entries]
    for (key,item) in new_item.items():
        config[str(curr_num_entries+1)][str(key)] = item
    safe_write_config(file,config)

def open_file_as_list(file):
    '''Opens file, returning contents as a list of lines.
    Returns empty list if file cannot be read.'''
    try:
        with open(file,'r') as f:
            file_contents = f.readlines()
    except Exception:
        return []
    file_contents = [line.strip() for line in file_contents if line.strip() is not None]
    return file_contents
