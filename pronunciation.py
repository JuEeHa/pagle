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

def get_common_prefix(a, b):
	for index in range(min(len(a), len(b))):
		if a[index] != b[index]:
			return a[:index]

	return a[:min(len(a), len(b))]

class PrefixMatchingError(Exception): None

Match = namedtuple('Match', ['pronunciation', 'latin_length', 'kana_length', 'latin_remaining', 'kana_remaining'])

def build_pronunciation(latin, kana, latin_prefixtree, kana_prefixtree):
	State = namedtuple('State', ['partial_pronunciation', 'latin_index', 'kana_index', 'latin_remaining', 'kana_remaining'])
	alternatives = []
	Farthest = namedtuple('Farthest', ['error', 'partial_pronunciation', 'latin_index', 'kana_index', 'latin_remaining', 'kana_remaining'])
	farthest = None

	partial_pronunciation = ''
	latin_index = 0
	kana_index = 0
	latin_remaining = ''
	kana_remaining = ''

	while latin_index < len(latin) or kana_index < len(kana) or latin_remaining != '' or kana_remaining != '':
		try:
			if len(latin_remaining) == 0:
				latin_prefixes = match_prefixes(latin[latin_index:], latin_prefixtree)
			else:
				latin_prefixes = [None]

			if len(kana_remaining) == 0:
				kana_prefixes = match_prefixes(kana[kana_index:], kana_prefixtree)
			else:
				kana_prefixes = [None]

			if len(latin_prefixes) == 0 and len(kana_prefixes) == 0:
				raise PrefixMatchingError('No matching latin or kana prefix')
			elif len(latin_prefixes) == 0:
				raise PrefixMatchingError('No matching latin prefix')
			elif len(kana_prefixes) == 0:
				raise PrefixMatchingError('No matching kana prefix')

			matches = []
			for latin_prefix in latin_prefixes:
				for kana_prefix in kana_prefixes:
					if latin_prefix is not None:
						latin_pronunciations = latin_prefixtree[latin_prefix].elements
					else:
						latin_pronunciations = [latin_remaining]

					if kana_prefix is not None:
						kana_pronunciations = kana_prefixtree[kana_prefix].elements
					else:
						kana_pronunciations = [kana_remaining]

					for latin_pronunciation in latin_pronunciations:
						for kana_pronunciation in kana_pronunciations:
							common_prefix = get_common_prefix(latin_pronunciation, kana_pronunciation)
							if common_prefix != '':
								latin_left = latin_pronunciation[len(common_prefix):]
								kana_left = kana_pronunciation[len(common_prefix):]
								latin_length = len(latin_prefix) if latin_prefix is not None else 0
								kana_length = len(kana_prefix) if kana_prefix is not None else 0
								matches.append((Match(common_prefix, latin_length, kana_length, latin_left, kana_left)))

			if len(matches) == 0:
				raise PrefixMatchingError('Pronunciations don\'t match')

			for match in matches:
				possible_pronunciation = partial_pronunciation + match.pronunciation
				possible_latin_index = latin_index + match.latin_length
				possible_kana_index = kana_index + match.kana_length
				possible_latin_remaining = match.latin_remaining
				possible_kana_remaining = match.kana_remaining
				alternatives.append(State(possible_pronunciation, possible_latin_index, possible_kana_index, possible_latin_remaining, possible_kana_remaining))

			partial_pronunciation, latin_index, kana_index, latin_remaining, kana_remaining = alternatives.pop()


		except PrefixMatchingError as err:
			if farthest is None or farthest.latin_index + farthest.kana_index < latin_index + kana_index:
				farthest = Farthest(err.args[0], partial_pronunciation, latin_index, kana_index, latin_remaining, kana_remaining)

			if len(alternatives) > 0:
				partial_pronunciation, latin_index, kana_index, latin_remaining, kana_remaining = alternatives.pop()
			else:
				print(farthest.partial_pronunciation + '…')
				print('%s|%s (%s)' % (latin[:farthest.latin_index], latin[farthest.latin_index:], farthest.latin_remaining))
				print('%s|%s (%s)' % (kana[:farthest.kana_index], kana[farthest.kana_index:], farthest.kana_remaining))
				raise PrefixMatchingError(farthest.error)

	return partial_pronunciation

def main():
	with open('prefixtrees', 'r') as f:
		serializeds = f.read().split('\n\n')

	kana_prefixtree = unserialize_prefixtree(serializeds[0])
	latin_prefixtree = unserialize_prefixtree(serializeds[1])

	pronunciations = []

	with open('words.text', 'r') as wordfile:
		for line in wordfile:
			while True:
				succeeded = True
				try:
					latin, kana = line.strip('\n').split('\t')
					pronunciation = build_pronunciation(latin, kana, latin_prefixtree, kana_prefixtree)

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

						_, kana, pronunciation = command
						kana_prefixtree.add_element(kana, pronunciation)

					elif command[0] == 'l':
						if len(command) != 3:
							print('?')
							continue

						_, latin, pronunciation = command
						latin_prefixtree.add_element(latin, pronunciation)

					elif command[0] == 's':
						if len(command) != 1:
							print('?')
							continue

						with open('prefixtrees', 'w') as f:
							f.write(serialize_prefixtree(kana_prefixtree) + '\n')
							f.write(serialize_prefixtree(latin_prefixtree) + '\n')

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
