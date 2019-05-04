#!/usr/bin/env python

import sys
import string
import getopt
from collections import defaultdict

from nlp_util import coreference, init, coreference_reading, coreference_rendering, head_finder, nlp_eval

def get_cluster_info(cluster, gold_doc, lang):
	text = gold_doc['text']
	gold_ner = gold_doc['ner']
	parses = gold_doc['parses']
	heads = gold_doc['heads']

	ner, number, person, gender = set(), set(), set(), set()
	for mention in cluster:
		mtext = coreference_rendering.mention_text(text, mention).lower()
		parse = parses[mention[0]]
		head = heads[mention[0]]
		tgender, tnumber, tperson = coreference.pronoun_properties(
				mtext, mention, parse, head, lang)
		if tgender != 'unknown':
			gender.add(tgender)
		if tnumber != 'unknown':
			number.add(tnumber)
		if tperson != 'unknown':
			person.add(tperson)
		if mention in gold_ner:
			ner.add(gold_ner[mention])
	return ner, number, person, gender

def match_boundaries(gold_mention_set, auto_mention_set, auto_mentions, auto_clusters, text, parses, heads):
	changed = set()
	# Apply changes for cases where the difference is only leading or trailing punctuation
	mapping = {}
	used_gold = set()
	unique_to_gold = gold_mention_set.difference(auto_mention_set)
	unique_to_auto =  auto_mention_set.difference(gold_mention_set)
	for amention in unique_to_auto:
		sentence, astart, aend = amention
		while (astart < aend - 1 and
				(text[sentence][astart] == "the" or
				(len(text[sentence][astart]) == 1 and
				text[sentence][astart][0] not in string.letters))):
			astart += 1
		while (astart < aend - 1 and
				(text[sentence][aend - 1] == "'s" or
				(len(text[sentence][aend - 1]) == 1 and
				text[sentence][aend - 1][0] not in string.letters))):
			aend -= 1
		for gmention in unique_to_gold:
			if gmention in used_gold:
				continue
			gsentence, gstart, gend = gmention
			if sentence != gsentence:
				continue
			while (gstart < gend - 1 and
					(text[sentence][gstart] == "the" or
					(len(text[sentence][gstart]) == 1 and
					text[sentence][gstart][0] not in string.letters))):
				gstart += 1
			while (gstart < gend - 1 and
					(text[sentence][gend - 1] == "'s" or
					(len(text[sentence][gend - 1]) == 1 and
					text[sentence][gend - 1][0] not in string.letters))):
				gend -= 1
			if astart == gstart and aend == gend:
				mapping[amention] = gmention
				used_gold.add(gmention)
	# Apply mapping to create new auto_mention_set
	for mention in mapping:
		auto_mention_set.remove(mention)
		auto_mention_set.add(mapping[mention])
		cluster_id = auto_mentions.pop(mention)
		auto_mentions[mapping[mention]] = cluster_id
		auto_clusters[cluster_id].remove(mention)
		auto_clusters[cluster_id].append(mapping[mention])
		changed.add((mention, mapping[mention]))

	# Create a mapping based on heads
	head_dict = defaultdict(lambda: {'auto': [], 'gold': []})
	for mention in auto_mention_set.difference(gold_mention_set):
		sentence, start, end = mention
		head = coreference.mention_head(mention, text, parses, heads, default_last=True)
		# This will default to last word if the mention is not a constituent, is
		# there an alternative?
		if head is not None:
			head = (mention[0], head[0])
			head_dict[head]['auto'].append(mention)
	for mention in gold_mention_set.difference(auto_mention_set):
		sentence, start, end = mention
		head = coreference.mention_head(mention, text, parses, heads, default_last=True)
		if head is not None:
			head = (mention[0], head[0])
			head_dict[head]['gold'].append(mention)

	mapping = {}
	for head in head_dict:
		amentions = head_dict[head]['auto']
		gmentions = head_dict[head]['gold']
		if len(amentions) == 1 and len(gmentions) == 1:
			mapping[amentions[0]] = gmentions[0]

	# Apply mapping to create new auto_mention_set
	for mention in mapping:
		auto_mention_set.remove(mention)
		auto_mention_set.add(mapping[mention])
		cluster_id = auto_mentions.pop(mention)
		auto_mentions[mapping[mention]] = cluster_id
		auto_clusters[cluster_id].remove(mention)
		auto_clusters[cluster_id].append(mapping[mention])
		changed.add((mention, mapping[mention]))

	# Add notes
	nchanges = []
	for smention, gmention in changed:
		properties = [smention, gmention]
		pre_extra_text = None
		pre_missing_text = None
		post_extra_text = None
		post_missing_text = None
		pre_extra_nodes = None
		pre_missing_nodes = None
		post_extra_nodes = None
		post_missing_nodes = None
		if smention[1] < gmention[1]:
			pre_extra_text = ' '.join(text[smention[0]][smention[1]:gmention[1]]).lower()
			nodes = parses[gmention[0]].get_spanning_nodes(smention[1], gmention[1])
			pre_extra_nodes = ' '.join([node.label for node in nodes])
		if smention[1] > gmention[1]:
			pre_missing_text = ' '.join(text[smention[0]][gmention[1]:smention[1]]).lower()
			nodes = parses[gmention[0]].get_spanning_nodes(gmention[1], smention[1])
			pre_missing_nodes = ' '.join([node.label for node in nodes])
		if smention[2] < gmention[2]:
			post_missing_text = ' '.join(text[smention[0]][smention[2]:gmention[2]]).lower()
			nodes = parses[gmention[0]].get_spanning_nodes(smention[2], gmention[2])
			post_missing_nodes = ' '.join([node.label for node in nodes])
		if smention[2] > gmention[2]:
			post_extra_text = ' '.join(text[smention[0]][gmention[2]:smention[2]]).lower()
			nodes = parses[gmention[0]].get_spanning_nodes(gmention[2], smention[2])
			post_extra_nodes = ' '.join([node.label for node in nodes])
		snode = parses[smention[0]].get_nodes('lowest', smention[1], smention[2])
		properties.append("in the parse" if snode is not None else "not in the parse")
		properties.append(pre_extra_text)
		properties.append(pre_missing_text)
		properties.append(post_extra_text)
		properties.append(post_missing_text)
		properties.append(pre_extra_nodes)
		properties.append(pre_missing_nodes)
		properties.append(post_extra_nodes)
		properties.append(post_missing_nodes)
		nchanges.append(tuple(properties))
	return nchanges

def split_merge_properties(part, cluster, auto, gold, text, parses, heads, gold_mentions, gold_clusters, auto_mentions, gold_doc, lang):
	ans = []
	rest = cluster.difference(part)

	# Size of part
	ans.append(len(part)) # 0

	# Size of rest
	ans.append(len(rest)) # 1

	# If size 1, what the text is
	mtext = None
	if len(part) == 1:
		mention = iter(part).next()
		mtext = '_'.join(coreference_rendering.mention_text(text, mention).lower().split())
	ans.append(mtext) # 2

	# Does this part have any cataphoric pronouns
	count = 0
	acluster = set()
	for mention in cluster:
		if mention in auto_mentions:
			acluster.add(mention)
	non_pronoun = min_non_pronoun(acluster, text, parses, heads, lang)
	if non_pronoun is not None and non_pronoun not in part:
		for mention in part:
			if mention in auto_mentions and mention < non_pronoun:
				mtype = coreference.mention_type(mention, text, parses, heads, lang)
				if mtype == 'pronoun':
					count += 1
	ans.append("%d_cataphoric" % count)

	# Number of pronouns, nominals, names present in it
	type_counts = {'pronoun': 0, 'name': 0, 'nominal': 0}
	for mention in part:
		mtype = coreference.mention_type(mention, text, parses, heads, lang)
		type_counts[mtype] += 1
	ans.append(type_counts['name']) # 3
	ans.append(type_counts['nominal']) # 4
	ans.append(type_counts['pronoun']) # 5

	# Number of pronouns, nominals, names, in rest
	type_counts = {'pronoun': 0, 'name': 0, 'nominal': 0}
	for mention in rest:
		mtype = coreference.mention_type(mention, text, parses, heads, lang)
		type_counts[mtype] += 1
	ans.append(type_counts['name']) # 6
	ans.append(type_counts['nominal']) # 7
	ans.append(type_counts['pronoun']) # 8

	# Whether this is extra
	all_extra = True
	for mention in part:
		if mention in gold_mentions:
			all_extra = False
	ans.append(all_extra) # 9

	# Whether the rest is all extra
	all_extra = True
	for mention in rest:
		if mention in gold_mentions:
			all_extra = False
	ans.append(all_extra) # 10

	# Whether there is an exact string match between a mention in the part and cluster (excluding pronouns)
	match_present = 'no_string_match'
	for smention in part:
		mtype = coreference.mention_type(smention, text, parses, heads, lang)
		if mtype == 'pronoun':
			continue
		for rmention in rest:
			mtype = coreference.mention_type(rmention, text, parses, heads, lang)
			if mtype == 'pronoun':
				continue
			stext = coreference_rendering.mention_text(text, smention).lower()
			rtext = coreference_rendering.mention_text(text, rmention).lower()
			if stext == rtext:
				match_present = 'string_match'
				break
		if 'no' not in match_present:
			break
	ans.append(match_present) # 11

	# Whether there is a head match between a mention in the part and cluster (excluding pronouns)
	match_present = 'no_head_match'
	for smention in part:
		mtype = coreference.mention_type(smention, text, parses, heads, lang)
		if mtype == 'pronoun':
			continue
		for rmention in rest:
			mtype = coreference.mention_type(rmention, text, parses, heads, lang)
			if mtype == 'pronoun':
				continue
			shead = coreference.mention_head(smention, text, parses, heads)[1].lower()
			rhead = coreference.mention_head(rmention, text, parses, heads)[1].lower()
			if shead == rhead:
				match_present = 'head_match'
				break
		if 'no' not in match_present:
			break
	ans.append(match_present) # 12

	# What has happened, or will happen
	example = iter(part).next()
	action = 'nothing'
	if example not in gold_mentions:
		action = 'delete'
	elif part != set(gold_clusters[gold_mentions[example]]):
		action = 'merge'
	ans.append(action) # 13

	action = 'nothing'
	if example not in auto_mentions:
		action = 'introduce'
	else:
		for acluster in auto:
			if example in acluster:
				if acluster != part:
					action = 'split'
				break
	ans.append(action) # 14

	# NER, number, person, gender
	cproperties = get_cluster_info(rest, gold_doc, lang)
	pproperties = get_cluster_info(part, gold_doc, lang)
	for prop in xrange(4):
		ans.append(cproperties[prop] == pproperties[prop])
		cprop = list(cproperties[prop])
		cprop.sort()
		pprop = list(pproperties[prop])
		pprop.sort()
		ans.append('part_' + '_'.join(pprop))
		ans.append('cluster_' + '_'.join(cprop))

	return ans

def mention_error_properties(mention, cluster, text, parses, heads, gold_doc, lang):
	ans = []
	rest = cluster.difference({mention})

	# Type of mention
	mtype = coreference.mention_type(mention, text, parses, heads, lang)
	ans.append(mtype)

	# Text of mention
	mtext = coreference_rendering.mention_text(text, mention).lower()
	ans.append('_'.join(mtext.split()))

	# Does it have a string match with something in the cluster?
	matches = 'no_text_match'
	for omention in rest:
		otext = coreference_rendering.mention_text(text, omention).lower()
		if otext == mtext:
			matches = 'text_match'
			break
	ans.append(matches)

	# Does it have a head match with something in the cluster?
	matches = 'no_head_match'
	mhead = coreference.mention_head(mention, text, parses, heads)[1].lower()
	for omention in rest:
		ohead = coreference.mention_head(omention, text, parses, heads)[1].lower()
		if mhead == ohead:
			matches = 'head_match'
			break
	ans.append(matches)

	# Is it nested within another mention in the cluster
	nested = 'not_nested'
	for omention in rest:
		if omention[0] == mention[0]:
			if mention[1] < omention[1] and omention[2] < mention[2]:
				if nested == 'nested_inside':
					nested = 'nested_both'
					break
				else:
					nested = 'nested_outside'
			if omention[1] < mention[1] and mention[2] < omention[2]:
				if nested == 'nested_outside':
					nested = 'nested_both'
					break
				else:
					nested = 'nested_inside'
	ans.append(nested)

	# Was it first in the cluster?
	ans.append(mention == min(cluster))

	# Was it last in the cluster?
	ans.append(mention == max(cluster))

	# Is it a case of cataphora?
	non_pronoun = min_non_pronoun(cluster, text, parses, heads, lang)
	ans.append(non_pronoun is not None and mention < non_pronoun)

	# Do NER, number, person, or gender of mention and cluster match?
	cluster_properties = get_cluster_info(rest, gold_doc, lang)
	mention_properties = get_cluster_info({mention}, gold_doc, lang)
	words = ['ner', 'number', 'person', 'gender']
	for i in xrange(4):
		if len(mention_properties[i]) == 0 or len(cluster_properties[i]) == 0:
			ans.append(words[i] + '_unknown')
		elif len(mention_properties[i].intersection(cluster_properties[i])) > 0:
			ans.append(words[i] + '_matches')
		else:
			ans.append(words[i] + '_does_not_match')

	return ans

def cluster_error_properties(cluster, text, parses, heads, gold_doc, lang):
	ans = []

	# How big is the cluster
	ans.append(len(cluster))

	# Counts of each type in the cluster
	counts = [0, 0, 0]
	for mention in cluster:
		mtype = coreference.mention_type(mention, text, parses, heads, lang)
		if mtype == 'name':
			counts[0] += 1
		elif mtype == 'nominal':
			counts[1] += 1
		elif mtype == 'pronoun':
			counts[2] += 1
	ans += counts

	# If it is one pronoun and something else, more info on the pronoun
	if counts[0] + counts[1] == 1 and counts[2] == 1:
		pronoun = None
		for mention in cluster:
			mtype = coreference.mention_type(mention, text, parses, heads, lang)
			if mtype == 'pronoun':
				pronoun = mention
		mtext = coreference_rendering.mention_text(text, pronoun).lower()
		ans.append(mtext)
	else:
		ans.append(None)

	# Number of cataphoric pronouns
	cataphora = 0
	non_pronoun = min_non_pronoun(cluster, text, parses, heads, lang, True)
	for mention in cluster:
		if mention < non_pronoun:
			mtype = coreference.mention_type(mention, text, parses, heads, lang)
			if mtype == 'pronoun':
				cataphora += 1
	ans.append(cataphora)

	# NER types
	ner = set()
	for mention in cluster:
		if mention in gold_doc['ner']:
			ner.add(gold_doc['ner'][mention])
	ner = list(ner)
	ner.sort()
	ans.append(ner)

	# Are all the mentions the same?
	mtext = set()
	for mention in cluster:
		mtext.add(coreference_rendering.mention_text(text, mention).lower())
	ans.append(len(mtext) == 1)

	# Are all the heads the same?
	mhead = set()
	for mention in cluster:
		mhead.add(coreference.mention_head(mention, text, parses, heads)[1].lower())
	ans.append(len(mhead) == 1)

	return ans

def repair(auto, gold, auto_mentions, gold_mention_set, text, parses, heads, gold_clusters, gold_mentions, gold_doc, lang):
	changes = defaultdict(lambda: [])

	# Split auto into pieces that each contain only one cluster
	nauto = []
	for acluster in auto:
		used = set()
		for gcluster in gold:
			intersection = acluster.intersection(gcluster)
			if len(intersection) > 0:
				nauto.append(intersection)
				used.update(intersection)
				if len(intersection) != len(acluster):
					properties = ['split'] + split_merge_properties(intersection, acluster, auto, gold, text, parses, heads, gold_mentions, gold_clusters, auto_mentions, gold_doc, lang)
					changes["split"].append((intersection.copy(), acluster.copy(), '', properties))
		for mention in acluster.difference(used):
			properties = ['split'] + split_merge_properties({mention}, acluster, auto, gold, text, parses, heads, gold_mentions, gold_clusters, auto_mentions, gold_doc, lang)
			changes["split"].append(({mention}, acluster.copy(), 'going nowhere', properties))
			changes["remove"].append(({mention},))

	# Add missing mentions as singletons:
	for cluster in gold:
		for mention in cluster:
			if mention not in auto_mentions:
				changes['introduce'].append(({mention},))
				nauto.append({mention})

	# Merge pieces together
	for gcluster in gold:
		for acluster in nauto:
			if acluster != gcluster and acluster.issubset(gcluster):
				properties = ['merge'] + split_merge_properties(acluster, gcluster, auto, gold, text, parses, heads, gold_mentions, gold_clusters, auto_mentions, gold_doc, lang)
				changes["merge"].append((acluster.copy(), gcluster.copy(), properties))

	return changes

def min_non_pronoun(cluster, text, parses, heads, lang, check_head=False):
	ans = None
	for mention in cluster:
		if coreference.mention_type(mention, text, parses, heads, lang) == 'pronoun':
			continue
		if check_head:
			head = coreference.mention_head(mention, text, parses, heads, default_last=True)
			if coreference.mention_type((mention[0], head[0][0], head[0][1]), text, parses, heads, lang) == 'pronoun':
				continue
		if ans is None or ans > mention:
			ans = mention
	return ans

def categorise(auto, gold, changes, text, parses, heads, gold_mention_set, auto_mentions, gold_doc, lang):
	# Not an Entity
	# A set of splits to singles that cover an entire cluster
	to_add = defaultdict(lambda: [])
	for split in changes['split']:
		is_disjoint = True
		for mention in split[1]:
			if mention in gold_mention_set:
				mtype = coreference.mention_type(mention, text, parses, heads, lang)
				if mtype != 'pronoun':
					is_disjoint = False
					break
		if is_disjoint:
			all_extra = True
			for mention in split[0]:
				if mention in gold_mention_set:
					all_extra = False
					break
			if all_extra:
				to_add[tuple(split[1])].append(split)
	for cluster in to_add:
		splits = to_add[cluster]
		cluster = set(cluster)
		split_cluster = set()
		for split in splits:
			split_cluster.update(split[0])
		if len(split_cluster) == 1:
			continue
		properties = ['extra'] + cluster_error_properties(split_cluster, text, parses, heads, gold_doc, lang)
		changes['extra entity'].append((split_cluster, cluster.copy(), properties))
		for split in splits:
			changes['split'].remove(split)
			to_remove = None
			for remove in changes['remove']:
				if iter(split[0]).next() in remove[0]:
					to_remove = remove
					break
			if to_remove is not None:
				changes['remove'].remove(to_remove)

	# Missed Entity
	# A set of merges of singles that form a single cluster
	to_remove = []
	for cluster in gold:
		is_disjoint = True
		missing = 0
		for mention in cluster:
			if mention not in auto_mentions:
				missing += 1
			else:
				if coreference.mention_type(mention, text, parses, heads, lang) != 'pronoun':
					is_disjoint = False
					break
		if is_disjoint and missing > 1:
			properties = ['missing'] + cluster_error_properties(cluster, text, parses, heads, gold_doc, lang)
			changes['missing entity'].append((cluster.copy(),properties))
			for mention in cluster:
				if mention in auto_mentions:
					continue
				operations = []
				for merge in changes['merge']:
					if len(merge[0]) == 1 and mention in merge[0]:
						operations.append(merge)
						break
				for introduce in changes['introduce']:
					if len(introduce[0]) == 1 and mention in introduce[0]:
						operations.append(introduce)
						break
				to_remove.append(tuple(operations))
	for merge, introduce in to_remove:
		changes['merge'].remove(merge)
		changes['introduce'].remove(introduce)

	# Remove the splits and merges that involve the earliest non-pronoun mentions in the cluster
	to_remove = []
	for split in changes['split']:
		if min_non_pronoun(split[0], text, parses, heads, lang) == min_non_pronoun(split[1], text, parses, heads, lang):
			if min_non_pronoun(split[0], text, parses, heads, lang) is None and min(split[0]) != min(split[1]):
				continue
			found = False
			for remove in changes['remove']:
				if split[0] == remove[0]:
					to_remove.append((split, remove))
					found = True
					break
			if not found:
				to_remove.append((split, None))
	for split, remove in to_remove:
		changes['split'].remove(split)
		if remove is not None:
			changes['remove'].remove(remove)
	to_remove = []
	for merge in changes['merge']:
		if min_non_pronoun(merge[0], text, parses, heads, lang) == min_non_pronoun(merge[1], text, parses, heads, lang):
			if min_non_pronoun(merge[0], text, parses, heads, lang) is None and min(merge[0]) != min(merge[1]):
				continue
			found = False
			for introduce in changes['introduce']:
				if introduce[0] == merge[0]:
					found = True
					to_remove.append((merge, introduce))
					break
			if not found:
				to_remove.append((merge, None))
	for merge, introduce in to_remove:
		changes['merge'].remove(merge)
		if introduce is not None:
			changes['introduce'].remove(introduce)

	# Remaining cases of splitting a singleton, which does not get merged, are incorrectly referential
	to_remove = []
	for split in changes['split']:
		if len(split[0]) == 1:
			if split[2] != '':
				to_remove.append(split)
	for split in to_remove:
		changes['split'].remove(split)
		to_remove = None
		for remove in changes['remove']:
			if iter(split[0]).next() in remove[0]:
				to_remove = remove
				break
		if to_remove is not None:
			changes['remove'].remove(to_remove)
		properties = ['extra'] + mention_error_properties(iter(split[0]).next(), split[1], text, parses, heads, gold_doc, lang)
		changes['extra mention'].append((split[0], split, properties))

	# Pair up introduces and merges to form incorrectly non-referential
	to_remove = []
	for merge in changes['merge']:
		if len(merge[0]) == 1:
			elsewhere = False
			for split in changes['split']:
				if len(split[0]) == 1:
					smention = list(split[0])[0]
					mmention = list(merge[0])[0]
					if smention == mmention:
						elsewhere = True
						break
			if not elsewhere:
				mention = list(merge[0])[0]
				if mention != min_non_pronoun(merge[1], text, parses, heads, lang) and mention not in auto_mentions:
					properties = ['missing'] + mention_error_properties(mention, merge[1], text, parses, heads, gold_doc, lang)
					changes['missing mention'].append(({mention}, merge[1], merge, properties))
					for introduce in changes['introduce']:
						if len(introduce[0]) == 1 and mention in introduce[0]:
							to_remove.append((merge, introduce))
							break
	for merge, introduce in to_remove:
		changes['merge'].remove(merge)
		changes['introduce'].remove(introduce)

	return changes

def print_pre_change_info(out, auto, gold, auto_mentions, gold_mention_set, text, parses, heads, gold_clusters, gold_mentions, gold_doc, auto_clusters, lang):
	# Cataphora
	mentions = defaultdict(lambda: [None, None, None])

	for cluster in gold:
		non_pronoun = min_non_pronoun(cluster, text, parses, heads, lang)
		for mention in cluster:
			mtype = coreference.mention_type(mention, text, parses, heads, lang)
			if mtype == 'pronoun':
				if non_pronoun is not None and mention < non_pronoun:
					mentions[mention][0] = True
				else:
					mentions[mention][0] = False

	for cluster in auto:
		non_pronoun = min_non_pronoun(cluster, text, parses, heads, lang)
		for mention in cluster:
			mtype = coreference.mention_type(mention, text, parses, heads, lang)
			if mtype == 'pronoun':
				if non_pronoun is not None and mention < non_pronoun:
					mentions[mention][1] = True
				else:
					mentions[mention][1] = False

	in_both = []
	for mention in mentions:
		if mentions[mention][0] and mentions[mention][1]:
			in_both.append(mention)
	for mention in in_both:
		acluster = auto_clusters[auto_mentions[mention]]
		gcluster = gold_clusters[gold_mentions[mention]]
		anon_pronoun = min_non_pronoun(acluster, text, parses, heads, lang)
		gnon_pronoun = min_non_pronoun(gcluster, text, parses, heads, lang)
		if anon_pronoun == gnon_pronoun:
			mentions[mention][2] = True
		else:
			mentions[mention][2] = False

	for mention in mentions:
		mtext = coreference_rendering.mention_text(text, mention).lower()
		print >> out['out'], "Cataphoric properties", mentions[mention], mtext

def process_document(doc_name, part_name, gold_doc, auto_doc, out, lang, remove_singletons=True):
	for ofile in [out['out'], out['short out']]:
		print >> ofile
		print >> ofile, '-' * 79
		print >> ofile, doc_name, part_name
		print >> ofile, '-' * 79
		print >> ofile
	text = gold_doc['text']

	gold_parses = gold_doc['parses']
	gold_heads = gold_doc['heads']
	gold_mentions = gold_doc['mentions']
	gold_clusters = gold_doc['clusters']

	auto_mentions = auto_doc['mentions'].copy()
	auto_clusters = auto_doc['clusters'].copy()

	if remove_singletons:
		to_remove = set()
		for cluster in auto_clusters:
			if len(auto_clusters[cluster]) == 1:
				to_remove.add(cluster)
				for mention in auto_clusters[cluster]:
					auto_mentions.pop(mention)
		for cluster in to_remove:
			auto_clusters.pop(cluster)

	gold_cluster_set = coreference.set_of_clusters(gold_clusters)
	auto_cluster_set = coreference.set_of_clusters(auto_clusters)
	gold_mention_set = coreference.set_of_mentions(gold_clusters)
	auto_mention_set = coreference.set_of_mentions(auto_clusters)

	coreference_rendering.print_conll_style_part(out['system output'], text, auto_mentions, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['gold'], text, gold_mentions, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: original'], text, auto_mentions, doc_name, part_name)

	# Fix boundary match errors
	errors = []
	span_errors = match_boundaries(gold_mention_set, auto_mention_set, auto_mentions, auto_clusters, text, gold_parses, gold_heads)
	if len(span_errors) == 0:
		print >> out['out'], "No",
		print >> out['short out'], "No",
	print >> out['out'], "Span Errors: (system, gold)"
	print >> out['short out'], "Span Errors: (system, gold)"
	for error in span_errors:
		errors.append(('span mismatch', error))
		before = coreference_rendering.print_mention(None, False, gold_parses, gold_heads, text, error[0], return_str=True)
		after = coreference_rendering.print_mention(None, False, gold_parses, gold_heads, text, error[1], return_str=True)
		print >> out['out'], '{:<50}    {:<50}'.format(before, after)
		print >> out['short out'], '{:<50}    {:<50}'.format(before, after)
	print >> out['out']
	print >> out['short out']
	for error in errors:
		print >> out['out'], 'span mismatch', error
		print >> out['properties'], ['span error'] + list(error[1])
	print >> out['out']
	print >> out['out'], '-' * 79
	print >> out['short out']
	print >> out['short out'], '-' * 79

	coreference_rendering.print_conll_style_part(out['error: span mismatch'], text, auto_mentions, doc_name, part_name)

	auto_mentions_split = auto_mentions.copy()
	auto_mentions_extra_mention = auto_mentions.copy()
	auto_mentions_extra_entity = auto_mentions.copy()
	auto_mentions_merge = auto_mentions.copy()
	auto_mentions_missing_mention = auto_mentions.copy()
	auto_mentions_missing_entity = auto_mentions.copy()
	auto_mentions_extra_mention_prog = auto_mentions.copy()
	auto_mentions_extra_entity_prog = auto_mentions.copy()
	auto_mentions_merge_prog = auto_mentions.copy()
	auto_mentions_missing_mention_prog = auto_mentions.copy()
	auto_mentions_missing_entity_prog = auto_mentions.copy()
	max_cluster = 0
	if len(auto_mentions) > 0:
		max_cluster = auto_mentions[max(auto_mentions, key=lambda mention: auto_mentions[mention])]

	groups = coreference.confusion_groups(gold_mentions, auto_mentions, gold_clusters, auto_clusters)
	for auto, gold in groups:
###		print_pre_change_info(out, auto, gold, auto_mentions, gold_mention_set, text, gold_parses, gold_heads, gold_clusters, gold_mentions, gold_doc, auto_clusters, lang)

		if nlp_eval.coreference_cluster_match(gold, auto):
			continue

		# Print clusters with errors shown
		print >> out['out']
		print >> out['short out']
		colours = coreference_rendering.print_cluster_error_group([auto, gold], out['out'], text, gold_parses, gold_heads, gold_mentions)
		colours2 = coreference_rendering.print_cluster_error_group([auto, gold], out['short out'], text, gold_parses, gold_heads, gold_mentions)

		# Work out the errors
		changes = repair(auto, gold, auto_mentions, gold_mention_set, text, gold_parses, gold_heads, gold_clusters, gold_mentions, gold_doc, lang)
		print >> out['out'], "\nRaw changes:"
		for name in changes:
			print >> out['out'], name, len(changes[name])
			for change in changes[name]:
				errors.append(('raw ' + name, change))

		# Categorise
		changes = categorise(auto, gold, changes, text, gold_parses, gold_heads, gold_mention_set, auto_mentions, gold_doc, lang)

		# Apply updates to corrected sets
		if 'split' in changes:
			for change in changes['split']:
				max_cluster += 1
				for mention in change[0]:
					auto_mentions_split[mention] = max_cluster
					auto_mentions_extra_mention_prog[mention] = max_cluster
					auto_mentions_extra_entity_prog[mention] = max_cluster
					auto_mentions_merge_prog[mention] = max_cluster
					auto_mentions_missing_mention_prog[mention] = max_cluster
					auto_mentions_missing_entity_prog[mention] = max_cluster
				rest = change[1].difference(change[0])
				if len(rest) == 1:
					rest = iter(rest).next()
					if rest not in gold_mentions:
						auto_mentions_split.pop(rest)
						auto_mentions_extra_mention_prog.pop(rest)
						auto_mentions_extra_entity_prog.pop(rest)
						auto_mentions_merge_prog.pop(rest)
						auto_mentions_missing_mention_prog.pop(rest)
						auto_mentions_missing_entity_prog.pop(rest)

		if 'extra mention' in changes:
			for change in changes['extra mention']:
				for mention in change[0]:
					auto_mentions_extra_mention.pop(mention)
					auto_mentions_extra_mention_prog.pop(mention)
					auto_mentions_extra_entity_prog.pop(mention)
					auto_mentions_merge_prog.pop(mention)
					auto_mentions_missing_mention_prog.pop(mention)
					auto_mentions_missing_entity_prog.pop(mention)

		if 'extra entity' in changes:
			for change in changes['extra entity']:
				for mention in change[0]:
					auto_mentions_extra_entity.pop(mention)
					auto_mentions_extra_entity_prog.pop(mention)
					auto_mentions_merge_prog.pop(mention)
					auto_mentions_missing_mention_prog.pop(mention)
					auto_mentions_missing_entity_prog.pop(mention)

		if 'merge' in changes:
			for change in changes['merge']:
				for cauto_mentions in [auto_mentions_merge, auto_mentions_merge_prog, auto_mentions_missing_mention_prog, auto_mentions_missing_entity_prog]:
					non_pronoun = min_non_pronoun(change[1], text, gold_parses, gold_heads, lang)
					if non_pronoun is None:
						non_pronoun = min(change[1])
					if non_pronoun not in cauto_mentions:
						max_cluster += 1
						cauto_mentions[non_pronoun] = max_cluster
					ncluster_id = cauto_mentions[non_pronoun]
					done = set()
					for mention in change[0]:
						if mention not in cauto_mentions:
							cauto_mentions[mention] = ncluster_id
						elif cauto_mentions[mention] not in done:
							pcluster_id = cauto_mentions[mention]
							done.add(pcluster_id)
							for smention in cauto_mentions:
								if cauto_mentions[smention] == pcluster_id:
									cauto_mentions[smention] = ncluster_id

		if 'missing mention' in changes:
			for change in changes['missing mention']:
				for cauto_mentions in [auto_mentions_missing_mention, auto_mentions_missing_mention_prog, auto_mentions_missing_entity_prog]:
					min_in_goal = None
					for mention in change[1]:
						if mention in cauto_mentions:
							if min_in_goal is None or min_in_goal > mention:
								min_in_goal = mention
					mention = iter(change[0]).next()
					if min_in_goal is not None:
						cauto_mentions[mention] = cauto_mentions[min_in_goal]
					else:
						min_mention = min(change[1])
						max_cluster += 1
						cauto_mentions[min_mention] = max_cluster
						cauto_mentions[mention] = max_cluster

		if 'missing entity' in changes:
			for change in changes['missing entity']:
				max_cluster += 1
				for mention in change[0]:
					auto_mentions_missing_entity[mention] = max_cluster
					auto_mentions_missing_entity_prog[mention] = max_cluster

		# Aggregate and count errors
		print >> out['out'], "\nCategorised:"
		print >> out['short out'], "\nErrors:"
		rename = {
			'span mismatch': "Span Error",
			'split': 'Conflated Entities',
			'extra mention': 'Extra Mention',
			'extra entity': 'Extra Entity',
			'merge': 'Divided Entity',
			'missing mention': 'Missing Mention',
			'missing entity': 'Missing Entity',
			'introduce': 'Introduced Mention',
		}
		for name in changes:
			if len(changes[name]) > 0:
				print >> out['out'], len(changes[name]), rename[name]
				print >> out['short out'], len(changes[name]), rename[name]
		print >> out['out'], '\nDetailed error listing:'
		for name in changes:
			for change in changes[name]:
				mention = None
				if len(change[0]) == 1:
					mention = change[0].copy().pop()
				if mention is not None:
					print >> out['out'], name,
					if mention in gold_mentions:
						colour = 15
						if gold_mentions[mention] in colours:
							colour = colours[gold_mentions[mention]]
						coreference_rendering.print_mention(out['out'], False, gold_parses, gold_heads, text, mention, colour)
					else:
						coreference_rendering.print_mention(out['out'], False, gold_parses, gold_heads, text, mention, extra=True)
				print >> out['out'], name, change
				print >> out['out'], "Properties included:", name, change[-1]
				print >> out['properties'], [name] + list(change[-1])
				errors.append((name, change))
		print >> out['out']
		print >> out['out'], '-' * 79
		print >> out['short out']
		print >> out['short out'], '-' * 79

	# Print corrected output
	coreference_rendering.print_conll_style_part(out['error: split'], text, auto_mentions_split, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: extra mention'], text, auto_mentions_extra_mention, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: extra entity'], text, auto_mentions_extra_entity, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: merge'], text, auto_mentions_merge, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: missing mention'], text, auto_mentions_missing_mention, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: missing entity'], text, auto_mentions_missing_entity, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: extra mention prog'], text, auto_mentions_extra_mention_prog, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: extra entity prog'], text, auto_mentions_extra_entity_prog, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: merge prog'], text, auto_mentions_merge_prog, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: missing mention prog'], text, auto_mentions_missing_mention_prog, doc_name, part_name)
	coreference_rendering.print_conll_style_part(out['error: missing entity prog'], text, auto_mentions_missing_entity_prog, doc_name, part_name)

	return errors


def main():
	# Process params
	try:
		opts, args = getopt.gnu_getopt(
				sys.argv[1:], '', ['keepsingletons', 'lang='])
		output_prefix, gold_dir, test_file = args
	except (getopt.GetoptError, ValueError):
		print('Print coreference resolution errors')
		print('./%s <prefix> <gold_dir> <test_file> '
				'[--keepsingletons] [--lang=<en|nl>]' % sys.argv[0])
		return
	opts = dict(opts)
	remove_singletons = '--keepsingletons' not in opts
	lang = opts.get('--lang', 'en')
	out = {
		'out': open(output_prefix + '.classified.detailed', 'w'),
		'properties': open(output_prefix + '.classified.properties', 'w'),
		'short out': open(output_prefix + '.classified', 'w'),
		'summary': open(output_prefix + '.summary', 'w'),
		'system output': open(output_prefix + '.system', 'w'),
		'gold': open(output_prefix + '.gold', 'w'),
		'error: original': open(output_prefix + '.corrected.none', 'w'),
		'error: span mismatch': open(output_prefix + '.corrected.span_errors', 'w'),
		'error: split': open(output_prefix + '.corrected.confused_entities', 'w'),
		'error: extra mention': open(output_prefix + '.corrected.extra_mention', 'w'),
		'error: extra entity': open(output_prefix + '.corrected.extra_entity', 'w'),
		'error: merge': open(output_prefix + '.corrected.divided', 'w'),
		'error: missing mention': open(output_prefix + '.corrected.missing_mention', 'w'),
		'error: missing entity': open(output_prefix + '.corrected.missing_entity', 'w'),
		'error: extra mention prog': open(output_prefix + '.corrected.extra_mention_prog', 'w'),
		'error: extra entity prog': open(output_prefix + '.corrected.extra_entity_prog', 'w'),
		'error: merge prog': open(output_prefix + '.corrected.divided_prog', 'w'),
		'error: missing mention prog': open(output_prefix + '.corrected.missing_mention_prog', 'w'),
		'error: missing entity prog': open(output_prefix + '.corrected.missing_entity_prog', 'w')
	}

	# Header info
	init.header(sys.argv, out['out'])
	init.header(sys.argv, out['short out'])
	init.header(sys.argv, out['properties'])
	init.header(sys.argv, out['summary'])
	print >> out['properties'], '''# Each line below describes a single error.
# The fields included for the seven error types are:
# span mismatch
#   System span (sentence, start, end)
#   Gold span (sentence, start, end)
#   Is the gold span a node in the gold parse?
#   Extra text to left
#   Missing text to left
#   Extra text to right
#   Missing text to right
#   Nodes spanning extra text to left
#   Nodes spanning missing text to left
#   Nodes spanning extra text to right
#   Nodes spanning missing text to right
#
# missing and extra entity
#   Missing or extra
#   Size
#   Number of proper names
#   Number of nominals
#   Number of pronouns
#   If it is 1 pronoun and 1 nominal/name, the pronoun
#   Number of cataphoric pronouns
#   NER types assigned to mentions in this cluster
#   Is there an exact string match for all mentions?
#   Is there a head match for all mentions?
#
# extra and missing mentions
#   Missing or extra
#   Mention type
#   The mention
#   Is there an exact match with something in the cluster?
#   Is there a head match with something in the cluster?
#   Is this a nested mention?
#   Was this the first mention in the cluster?
#   Was this the last mention in the cluster?
#   Was this a case of cataphoa?
#   Does NER match?
#   Does number match?
#   Does person match?
#   Does gender match?
#
# split and merge (conflated entities and divided entity)
#   Split or merge
#   Size of the part being split/merged ('part' for the rest of these notes)
#   Size of the rest of the cluster ('rest' for the rest of these notes)
#   If the part is a single mention, its text
#   The number of cataphoric pronouns in the part
#   Number of names in the part
#   Number of nominals in the part
#   Number of pronouns in the part
#   Number of names in the rest
#   Number of nominals in the rest
#   Number of pronouns in the rest
#   Whether the mentions in the part are extra
#   Whether the rest is made up of extra mentions
#   Is there an exact string match between a mention in the part and one in the rest?
#   Is there a head match between a mention in the part and one in the rest?
#   Will this part be merged or deleted later?
#   Has this part been split or introduced earlier?
#   NER type(s) of part and rest match
#   NER types of the part
#   NER types of the rest
#   Number type(s) of part and rest match
#   Number types of the part
#   Number types of the rest
#   Gender type(s) of part and rest match
#   Gender types of the part
#   Gender types of the rest
#   Person type(s) of part and rest match
#   Person types of the part
#   Person types of the rest
'''

	# Read input
	auto = coreference_reading.read_conll_coref_system_output(test_file)
	gold = coreference_reading.read_conll_matching_files(auto, gold_dir, lang)

	# Define an order
	order = []
	for doc in auto:
		for part in auto[doc]:
			order.append((doc, part))
	order.sort()

	# Work out the errors
	counts = defaultdict(lambda: [])
	for doc, part in order:
		if doc not in gold or part not in gold[doc]:
			print >> sys.stderr, doc, part, "not in gold"
		if 'text' not in auto[doc][part]:
			auto[doc][part]['text'] = gold[doc][part]['text']
		errors = process_document(doc, part, gold[doc][part], auto[doc][part], out, lang, remove_singletons)
		for error in errors:
			counts[error[0]].append(error)

	# Print a summary of the changes and errors
	order = [
		(None, "Operations:"),
		('span mismatch', 'Correct Span'),
		('raw introduce', 'Introduce Mention'),
		('raw split', 'Split from Cluster'),
		('raw merge', 'Merge into Cluster'),
		('raw remove', 'Remove Mention'),
		(None, ''),
		(None, 'Errors:'),
		('span mismatch', "Span Error"),
		(None, ''),
		('split', 'Conflated Entities'),
		('extra mention', 'Extra Mention'),
		('extra entity', 'Extra Entity'),
		(None, ''),
		('merge', 'Divided Entity'),
		('missing mention', 'Missing Mention'),
		('missing entity', 'Missing Entity')
	]
	for key, text in order:
		if key is None:
			print >> out['summary'], text
		else:
			print >> out['summary'], "%6d   %s" % (len(counts[key]), text)

	for name in out:
		out[name].close()


if __name__ == '__main__':
	main()
