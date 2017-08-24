#!/usr/bin/env python3
from collections import namedtuple
import sys

class PrefixTree:
	def __init__(self, elements = None):
		self.children = dict()
		if elements != None:
			if type(elements) == str:
				self.elements = set([elements])
			else:
				self.elements = set(elements)
		else:
			self.elements = set()

	def __contains__(self, indexes):
		if len(indexes) == 0:
			return len(self.elements) > 0
		else:
			if indexes[0] in self.children:
				return indexes[1:] in self.children[indexes[0]]
			else:
				return False

	def __getitem__(self, indexes):
		assert len(indexes) > 0
		if len(indexes) == 1:
			return self.children[indexes[0]]
		else:
			return self.children[indexes[0]][indexes[1:]]

	def __setitem__(self, indexes, child):
		assert len(indexes) > 0
		if len(indexes) == 1:
			self.children[indexes[0]] = child
		else:
			if indexes[0] not in self.children:
				self.children[indexes[0]] = PrefixTree()
			self.children[indexes[0]][indexes[1:]] = child

	def add_element(self, indexes, element):
		if len(indexes) == 0:
			self.elements.add(element)
		else:
			if indexes[0] not in self.children:
				self.children[indexes[0]] = PrefixTree()
			self.children[indexes[0]].add_element(indexes[1:], element)

def serialize_prefixtree(prefixtree, *, _prefix = '', _inner = False):
	serialized = ''
	if len(prefixtree.elements) > 0:
		serialized += _prefix + '\t' + '\t'.join(prefixtree.elements) + '\n'

	for name, subtree in prefixtree.children.items():
		serialized += serialize_prefixtree(subtree, _prefix = _prefix + name, _inner = True)

	if not _inner and serialized == '':
		serialized += '\n'

	return serialized

def unserialize_prefixtree(serialized):
	prefixtree = PrefixTree()
	for line in (i for i in serialized.split('\n') if i != ''):
		key, *elements = line.split('\t')
		for element in elements:
			prefixtree.add_element(key, element)

	return prefixtree

def match_prefixes(text, prefixtree):
	"""Return a list of all matching prefixes, with longest sorted first"""
	longest_prefix = ''
	current = prefixtree
	for char in text:
		if char in current.children:
			longest_prefix += char
			current = current.children[char]
		else:
			break

	prefixes = []
	for i in reversed(range(len(longest_prefix))):
		if longest_prefix[:i + 1] in prefixtree:
			prefixes.append(longest_prefix[:i + 1])

	return prefixes

class PrefixMatchingError(Exception): None

def transliterate_kana(kana, kana_prefixtree):
	index = 0
	partial_romaji = ''

	try:
		while index < len(kana):
			prefixes = match_prefixes(kana[index:], kana_prefixtree)

			if len(prefixes) == 0:
				raise PrefixMatchingError('No transliteration')

			romajis = kana_prefixtree[prefixes[0]].elements
			if len(romajis) != 1:
				raise PrefixMatchingError('Too many transliterations')

			romaji,= romajis
			partial_romaji += romaji
			index += len(prefixes[0])

		return partial_romaji

	except PrefixMatchingError as err:
		print(partial_romaji + '…')
		print('%s|%s' % (kana[:index], kana[index:]))
		raise err

Match = namedtuple('Match', ['pronunciation', 'latin', 'romaji'])

def build_pronunciation(latin, romaji, latin_prefixtree, romaji_prefixtree):
	State = namedtuple('State', ['partial_pronunciation', 'latin_index', 'romaji_index'])
	alternatives = []

	partial_pronunciation = ''
	latin_index = 0
	romaji_index = 0

	while latin_index < len(latin) or romaji_index < len(romaji):
		try:
			latin_prefixes = match_prefixes(latin[latin_index:], latin_prefixtree)
			romaji_prefixes = match_prefixes(romaji[romaji_index:], romaji_prefixtree)
			if len(latin_prefixes) == 0 or len(romaji_prefixes) == 0:
				raise PrefixMatchingError('No matching prefix')

			matches = []
			for latin_prefix in latin_prefixes:
				for romaji_prefix in romaji_prefixes:
					latin_pronunciations = latin_prefixtree[latin_prefix].elements
					romaji_pronunciations = romaji_prefixtree[romaji_prefix].elements

					for pronunciation in latin_pronunciations:
						if pronunciation in romaji_pronunciations: 
							matches.append((Match(pronunciation, latin_prefix, romaji_prefix)))

			if len(matches) == 0:
				raise PrefixMatchingError('Pronunciations don\'t match')
			elif len(matches) > 1:
				for match in matches:
					possible_pronunciation = partial_pronunciation + match.pronunciation
					possible_latin_index = latin_index + len(match.latin)
					possible_romaji_index = romaji_index + len(match.romaji)
					alternatives.append(State(possible_pronunciation, possible_latin_index, possible_romaji_index))

				partial_pronunciation, latin_index, romaji_index = alternatives.pop()
			else:
				partial_pronunciation += matches[0].pronunciation
				latin_index += len(matches[0].latin)
				romaji_index += len(matches[0].romaji)


		except PrefixMatchingError as err:
			if len(alternatives) > 0:
				partial_pronunciation, latin_index, romaji_index = alternatives.pop()
			else:
				print(partial_pronunciation + '…')
				print('%s|%s' % (latin[:latin_index], latin[latin_index:]))
				print('%s|%s' % (romaji[:romaji_index], romaji[romaji_index:]))
				raise err

	return partial_pronunciation

def main():
	with open('prefixtrees', 'r') as f:
		serializeds = f.read().split('\n\n')

	kana_prefixtree = unserialize_prefixtree(serializeds[0])
	latin_prefixtree = unserialize_prefixtree(serializeds[1])
	romaji_prefixtree = unserialize_prefixtree(serializeds[2])

	pronunciations = []

	with open('words.text', 'r') as wordfile:
		for line in wordfile:
			while True:
				succeeded = True
				try:
					latin, kana = line.strip('\n').split('\t')
					romaji = transliterate_kana(kana, kana_prefixtree)
					pronunciation = build_pronunciation(latin, romaji, latin_prefixtree, romaji_prefixtree)

					print('>>> %s → %s' % (latin, pronunciation))
					pronunciations.append((latin, pronunciation))

				except PrefixMatchingError as err:
					print(err)
					succeeded = False

				if succeeded:
					break

				while True:
					command = input(': ')
					command = [i for i in command.split(' ') if i != '']

					if len(command) == 0:
						break

					elif command[0] == 'k':
						if len(command) != 3:
							print('?')
							continue

						_, kana, romaji = command
						kana_prefixtree.add_element(kana, romaji)

					elif command[0] == 'l':
						if len(command) != 3:
							print('?')
							continue

						_, latin, pronunciation = command
						latin_prefixtree.add_element(latin, pronunciation)

					elif command[0] == 'r':
						if len(command) != 3:
							print('?')
							continue

						_, romaji, pronunciation = command
						romaji_prefixtree.add_element(romaji, pronunciation)

					elif command[0] == 's':
						if len(command) != 1:
							print('?')
							continue

						with open('prefixtrees', 'w') as f:
							f.write(serialize_prefixtree(kana_prefixtree) + '\n')
							f.write(serialize_prefixtree(latin_prefixtree) + '\n')
							f.write(serialize_prefixtree(romaji_prefixtree) + '\n')

						with open('pronunciations.text', 'w') as f:
							for latin, pronunciation in pronunciations:
								f.write('%s\t%s\n' % (latin, pronunciation))

					elif command[0] == 'q':
						if len(command) != 1:
							print('?')
							continue

						sys.exit(0)

					else:
						print('?')

if __name__ == '__main__':
	main()
