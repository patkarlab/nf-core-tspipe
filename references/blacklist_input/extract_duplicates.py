#!/usr/bin/env python3
#This script will take a list of vcf files as input 
#The output will be a list of repetitive variants

import argparse
from collections import Counter
import pandas as pd

def extract_duplicates(arguments):
	outfile_name = arguments.output
	input_file_list = arguments.samples
	cutoff = round (arguments.fraction_cutoff * len(input_file_list))
	outfile = open(outfile_name, "w")

	print ("output file name is", outfile_name)
	print ("cutoff to be used", cutoff)
	#print ("input file list", input_file_list)

	row_counts = Counter()		# Counter object
	for ind, files in enumerate(input_file_list):
		with open(files) as infile:
			df = pd.DataFrame()
			chr=[]
			pos=[]
			ref=[]
			alt=[]
			for lines in infile:
				if not lines.startswith("#"):
					data = lines.split('\t')
					chr.append(data[1])
					pos.append(data[2])
					ref.append(data[4])
					alt.append(data[5])
			df = pd.DataFrame(list(zip(chr, pos, ref, alt)), columns=['chr', 'pos', 'ref', 'alt'])
			for row in df.itertuples(index=False, name=None):
				row_counts[row] += 1

	outfile.write("chr\tpos\tref\talt\tobserved_count\n")
	for row, count in row_counts.items():
		if count > cutoff:
			outfile.write("\t".join(map(str, row)) + f"\t{count}\n")
	outfile.close()

def parse_arguments():
	parser = argparse.ArgumentParser(description="Extraction of repetitive variants")
	parser.add_argument('--output', help='list of tab separated variants eg: variants.txt')	# positional argument
	parser.add_argument('--samples', nargs='*', help='list of vcf files to obtain duplicates')
	parser.add_argument('--fraction_cutoff', default=0.5, help='fraction of files which should contain the variant', type=float)
	return parser.parse_args()

def main ():
	args = parse_arguments()
	extract_duplicates(args)

if __name__ == "__main__":
	main()
