from __future__ import print_function, absolute_import
import io
import sys
import time


def header(args, out=sys.stdout):
	header = "# Time of run:\n# "
	header += time.ctime(time.time())
	header += "\n# Command:\n# "
	header += ' '.join(args)
	header += "\n#"
	print(header, file=out)
