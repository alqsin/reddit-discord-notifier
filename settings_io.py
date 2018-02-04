import configparser
import os

# should I store a list of known auth values instead of passing them in?
def read_auth(file,entry,values):
	'''Uses configparser to get every entry=value in auth file
	Returns a dictionary with keys in values'''
	config = configparser.ConfigParser()
	auth_dict = {}
	config.read(file)
	for value in values:
		new_auth = config[entry][value]  # raises KeyError if doesn't exist
		if config[entry][value] is None:
			raise ValueError("Something wrong with value of {} from auth for {}.".format(value,entry))
		auth_dict[value] = new_auth
	return auth_dict

def read_config_as_dict(file):
	config = configparser.ConfigParser()
	config.read(file)
	config_dict = {}
	for section in config.sections():
		curr_entry = {}
		for key in config[section]:
			curr_entry[key] = config[section][key]
		config_dict[section] = curr_entry
	return config_dict

# may want to port this to just use read_config_as_dict() to make editing easier in future
def read_config_as_list(file):
	config = configparser.ConfigParser()
	config.read(file)
	config_list = []
	for section in config.sections():
		curr_entry = {}
		for key in config[section]:
			curr_entry[key] = config[section][key]
		config_list.append(curr_entry)
	return config_list

def add_path_to_file(filename):
	if not os.path.exists(os.path.dirname(filename)):
		os.makedirs(os.path.dirname(filename))

# figure out a scheme so that the main methods know when reading/writing failed
def safe_write_config(file,config):
	path_to_old = get_path_to_old(file)

	# makes sure you can write to the places you want to write to
	add_path_to_file(file)
	add_path_to_file(path_to_old)

	with open(file+' temp','w') as config_file:
		config.write(config_file)
	os.replace(file,path_to_old)
	os.rename(file+' temp',file)

def safe_write_config_no_undo(file,config):
	with open(file+' temp','w') as config_file:
		config.write(config_file)
	os.replace(file+' temp',file)

def get_path_to_old(filename):
	'''Adds /old/ to the path to file'''
	return os.path.join(os.path.dirname(filename),'old',os.path.basename(filename))

# TODO: store several copies and have undo strictly go backwards
def revert_previous_write(file):
	'''Swaps the archived user notifications file with current one'''
	path_to_old = get_path_to_old(file)

	if not os.path.exists(path_to_old):
		return 0
	os.rename(file,file+' temp')
	os.replace(path_to_old,file)
	os.replace(file+' temp',path_to_old)
	return 1

def write_config_from_list(file,config_list):
	config = configparser.ConfigParser()
	i = 1
	for config_item in config_list:
		config.add_section(str(i))
		for (key,item) in config_item.items():
			config[str(i)][str(key)] = item
		i += 1
	safe_write_config(file,config)

def add_config_item(file,new_item):
	config = configparser.ConfigParser()
	if not os.path.exists(file):
		create_config_file(file)  # don't know if this is the best way of handling
	config.read(file)
	curr_num_entries = len(config.sections())  # add some validation here?
	config.add_section(str(curr_num_entries+1))  # this works assuming current entries are named in [1,curr_num_entries]
	for (key,item) in new_item.items():
		config[str(curr_num_entries+1)][str(key)] = item
	safe_write_config_no_undo(file,config)

# determine a way to merge this and add_config_item() which uses the # of items as a section name
def add_named_config_item(file,new_item,new_item_name):
	config = configparser.ConfigParser()
	if not os.path.exists(file):
		create_config_file(file)
	config.read(file)
	if new_item_name in config.sections():
		config.remove_section(new_item_name)
	config.add_section(new_item_name)
	for (key,item) in new_item.items():
		config[new_item_name][str(key)] = item
	safe_write_config_no_undo(file,config)

def create_config_file(file):
	if os.path.exists(file):
		raise ValueError("File already exists.")
	open(file,'a').close()