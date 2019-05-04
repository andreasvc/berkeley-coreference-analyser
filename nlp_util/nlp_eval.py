from __future__ import print_function, absolute_import


def coreference_cluster_match(gold, auto):
	if len(gold) != len(auto):
		return False
	for gcluster in gold:
		matched = False
		for acluster in auto:
			if acluster == gcluster:
				matched = True
				break
		if not matched:
			return False
	return True


def calc_prf(match, gold, test):
	"""Calculate Precision, Recall and F-Score, with:
	True Positive = match
	False Positive = test - match
	False Negative = gold - match

	>>> print(calc_prf(0, 0, 0))
	(1.0, 1.0, 1.0)
	>>> print(calc_prf(0, 0, 5))
	(0.0, 1.0, 0.0)
	>>> print(calc_prf(0, 4, 5))
	(0.0, 0.0, 0.0)
	>>> print(calc_prf(0, 4, 0))
	(0.0, 0.0, 0.0)
	>>> print(calc_prf(2, 2, 8))
	(0.25, 1.0, 0.4)
	"""
	if gold == 0:
		if test == 0:
			return 1.0, 1.0, 1.0
		return 0.0, 1.0, 0.0
	if test == 0 or match == 0:
		return 0.0, 0.0, 0.0
	p = match / float(test)
	r = match / float(gold)
	try:
		f = 2 * match / (float(test + gold))
		return p, r, f
	except Exception:
		return 0.0, 0.0, 0.0
