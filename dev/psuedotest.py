# def shift(string, reverse=False) :
# 	"""Shift ord value of character within range."""
#
# 	new_string = []
#
# 	for char in string :
# 		try :
# 			value = ord(char)
#
# 			if value in range(ord('A'), ord('Z') + 1) :
# 				min = ord('A')
# 				max = ord('Z')
# 			elif value in range(ord('a'), ord('z') + 1) :
# 				min = ord('a')
# 				max = ord('z')
# 			values = range(min, max + 1)
#
# 			if reverse :
# 				index = values.index(value) - 1
# 			else :
# 				index = values.index(value) + 1
#
# 			new_string.append(chr(values[index % len(values)]))
#
# 		except :
# 			new_string.append(char)
#
# 	return ''.join(new_string)

def shift(number, reverse=False) :
	"""Shift digits of an integer within range."""

	digits = [int(digit) for digit in str(number)]
	new_digits = []

	for digit in digits :
		if reverse :
			new_digit = (digit - 1) % 10
		else :
			new_digit = (digit + 1) % 10
		new_digits.append(new_digit)

	return int(''.join(map(str, new_digits)))
result = shift(188647277181665280)
print(result)
print(shift(result, reverse=True))
