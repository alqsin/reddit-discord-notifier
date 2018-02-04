def is_integer(x):
	try:
		int(x)
	except:
		return False
	return True