This software classifies errors in the output of coreference resolution
systems.  For a full description of the method, and discussion of results when
applied to the systems from the 2011 CoNLL Shared Task, see:

   [Error-Driven Analysis of Challenges in Coreference Resolution](http://www.aclweb.org/anthology/D13-1027)
   Jonathan K. Kummerfeld and Dan Klein, 
   EMNLP 2013

To use the system, download it one of these ways, and run `classify_coreference_errors.py`
as shown below:

- [Download .zip](https://github.com/jkkummerfeld/berkeley-coreference-analyser/zipball/master)
- [Download .tar.gz](https://github.com/jkkummerfeld/berkeley-coreference-analyser/tarball/master)
- `git clone https://github.com/jkkummerfeld/berkeley-coreference-analyser.git`

If you use my code in your own work, please cite the paper:

```
@InProceedings{Kummerfeld-Klein:2013:EMNLP,
  author    = {Jonathan K. Kummerfeld  and  Dan Klein},
  title     = {Error-Driven Analysis of Challenges in Coreference Resolution},
  booktitle = {Proceedings of the 2013 Conference on Empirical Methods in Natural Language Processing},
  address   = {Seattle, Washington, USA},
  month     = {October},
  year      = {2013},
  pages     = {265--277},
  url       = {http://www.aclweb.org/anthology/D13-1027},
  software  = {https://github.com/jkkummerfeld/berkeley-coreference-analyser},
}
```

Example of system output (groupings indicate system clusters, colours indicate gold clusters):

![Image of system terminal output](./example_coref_analysis_output.png)

##  Running the System

There are three main programs:

- `classify_coreference_errors.py`, Classify errors in system output, using the CoNLL output format
- `print_errors.py`, Print system output in several ways, to illustrate the errors
- `coreference_format_conversion.py`, Convert the output of several systems to the CoNLL format

Running each with no arguments will provide help information.  Also see the
sample folders for example runs.  These were generated as follows:

```
./classify_coreference_errors.py data/classified/stanford data/gold/ data/homogenised/stanford.homogenised.out

./print_errors.py data/pretty_printed/stanford data/gold/ data/homogenised/stanford.homogenised.out

./coreference_format_conversion.py data/homogenised/stanford.homogenised stanford_xml data/stanford_xml_out/ data/gold/
```


For the error analysis runs the files produced are:
- stanford.summary -
   Counts of errors, and counts of the raw operations involved.
- stanford.classified -
   A simple view of the errors.
- stanford.classified.detailed -
   Same as the previous file, but with extra output describing properties of each error.
- stanford.classified.properties -
	 Every error gets a single line, with a list of properties (see the top of the file for an explanation of properties).

The rest of the files are output in the CoNLL format that has some of the
errors corrected, for use in measuring the impact of each error type:

- stanford.gold
- stanford.system
- stanford.corrected.none
- stanford.corrected.span_errors
- stanford.corrected.confused_entities
- stanford.corrected.extra_mention
- stanford.corrected.extra_entity
- stanford.corrected.divided
- stanford.corrected.missing_mention
- stanford.corrected.missing_entity

These are similar to the above files, but with errors progressively corrected,
so by the final file there are no errors left.

- stanford.corrected.extra_mention_prog
- stanford.corrected.extra_entity_prog
- stanford.corrected.divided_prog
- stanford.corrected.missing_mention_prog
- stanford.corrected.missing_entity_prog

Running the commands with an invalid number of arguments will give you the following execution information:

```
./classify_coreference_errors.py <prefix> <gold_dir> <test_file> [--keepsingletons] [--lang=<en|nl>]

./print_errors.py <prefix> <gold_dir> <test_file> [--resolvespanerrors] [--lang=<en|nl>]

./coreference_format_conversion.py <prefix> <[cherrypicker,ims,bart,conll,stanford_xml,stanford,uiuc,reconcile]> <dir | file> <gold_dir>
```
By default all optional flags are disabled and English data is expected.

- `prefix`: write output to filenames starting with this prefix;
   e.g., passing `/tmp/foo` will create files /tmp/foo.gold, /tmp/foo.system, etc.
- `gold_dir`: specify a directory with gold conll files
- `test_file`: the conll file with the system output; for each document in this
  file, a corresponding gold file is searched in `gold_dir`; i.e., if
  `test_file` contains `#begin document foo`, the corresponding file
  `gold_dir/foo.conll` should exist.

The output contains colors with ANSI codes. To view the colors and scroll through the output,
use `less -R` or [bat](https://github.com/sharkdp/bat).

##  Questions and Answers

Q: I'm getting errors such as "TypeError: initial_value must be unicode or None, not str",
what's broken?

A: Check your version of Python.  This code was designed for Python 2.7.x, but
later converted to Python 3.3+, it will not work with earlier versions.

Q: What about languages other than English?

A: In principle the code is fairly language agnostic, the main thing that would
need to be altered is the head finder.  I do not plan to add support for other
languages in the near future, but am happy to incorporate proposals of code
amendments!

**UPDATE**: Pass the option `--lang=nl` to work with Dutch data; assumes Alpino trees
and rich POS tags in gold CoNLL data; POS tags should have parentheses replaced
by square brackets; e.g., `VNW[pers,pron,nomin,vol,1,ev]`.
To add support for another language, search for the variable `lang` in
`nlp_util/head_finder.py` and `nlp_util/coreference.py`.
