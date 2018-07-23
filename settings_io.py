import configparser
import os

class Auth:
	def __init__(self,AUTH_FILE='auth.ini'):
		self.AUTH_FILE = AUTH_FILE
		self.read_auth()
	def __getitem__(self,key):
		'''Returns a section from auth_dict'''
		return self.auth_dict[key]
	def read_auth(self):
		'''Refreshes stored auth.'''
		self.auth_dict = read_config_as_dict(self.AUTH_FILE)

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

def safe_write_config(file,config):
	with open(file+' temp','w') as config_file:
		config.write(config_file)
	os.replace(file+' temp',file)

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
		raise ValueError('No such file!')
	config.read(file)
	curr_num_entries = len(config.sections())  # add some validation here?
	config.add_section(str(curr_num_entries+1))  # this works assuming current entries are named in [1,curr_num_entries]
	for (key,item) in new_item.items():
		config[str(curr_num_entries+1)][str(key)] = item
	safe_write_config(file,config)

def create_config_file(file):
	if os.path.exists(file):
		raise ValueError("File already exists.")
	open(file,'a').close()

def open_file_as_list(file):
	try:
		with open(file,'r') as f:
			file_contents = f.readlines()
		file_contents = [line.strip() for line in file_contents]
		return file_contents
	except:
		return []