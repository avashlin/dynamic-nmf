#!/usr/bin/env python
"""
Merge document partitions from window topics to create an overall document partition for a dynamic model.

Usage: 
python create-dynamic-partition.py -o out/dynamic-combined.pkl out/dynamictopics_k05.pkl out/month1_windowtopics_k05.pkl out/month2_windowtopics_k08.pkl out/month3_windowtopics_k08.pkl
"""
import os, sys
import re
import logging as log
from optparse import OptionParser
from prettytable import PrettyTable
import unsupervised.nmf, unsupervised.rankings

# --------------------------------------------------------------

def get_options():
    parser = OptionParser(usage="usage: %prog [options] dynamic_topics window_topics1 window_topics2...")
    parser.add_option("-m", "--model", action="store", type="string", dest="dynamic_model", help="the path to the dynamic topic model", default=None)
    parser.add_option("-o","--output", action="store",type="string",dest="out_path",help="output path", default=None)
    parser.add_option("-s","--selected_file", action="store",type="string",dest="selected_file",help="file containing the optimal number for k for different windows", default=None)
    parser.add_option("-p","--pattern", action="store",type="string",dest="pattern",help="pattern to use for selecting the models to use", default=None)
    parser.add_option("-b","--base_path", action="store",type="string",dest="window_base_path",help="the directory that contains the window models", default="")
    parser.add_option("-l","--log", action="store",type="string",dest="log_file",help="log file", default=None)
    

    (options, args) = parser.parse_args()

# We don't need this check anymore because we are not parsing window models as arguments anymore
#     if( len(args) < 3 ):
#         parser.error( "Must specify at least a dynamic topic file, followed by two or more window topic files (in order of time window)" )


    return options,args


def main(options,args):
    
    
    if options.selected_file is not None:
        
        parser = re.compile(options.pattern)
        data = open(options.selected_file).readlines()
        files = []
        i = 0 
        for line in data:
            if i == 0:
                i += 1
                continue
            vals = line.split(',')
            prefix = vals[0]
            k = vals[1].replace("\n","")
            
            if int(k) < 10:
                name = prefix + "_windowtopics_k0"+k+".pkl"
            else:
                name = prefix + "_windowtopics_k"+k+".pkl"
            
            if parser.match(name):
                files.append(os.path.join(options.window_base_path,name))

                
    if options.log_file is None:
        log.basicConfig(level=20, format='%(message)s')
    else:
        log.basicConfig(level=20, format="%(message)s",filename=options.log_file)


    # Load dynamic results: (doc_ids, terms, term_rankings, partition, W, H, labels)
    dynamic_in_path = options.dynamic_model #args[0]
    dynamic_res = unsupervised.nmf.load_nmf_results( dynamic_in_path )
    dynamic_k = len(dynamic_res[2])
    dynamic_partition = dynamic_res[3]
    log.info( "Loaded model with %d dynamic topics from %s" % (dynamic_k, dynamic_in_path) )

    # Create a map of window topic label -> dynamic topic
    assigned_window_map = {}
    dynamic_partition = dynamic_res[3]
    for idx, window_topic_label in enumerate(dynamic_res[0]):
        assigned_window_map[window_topic_label] = dynamic_partition[idx]

    all_partition = []
    all_doc_ids = []

    # Process each window topic model
    window_num = 0
    for in_path in files:
        window_num += 1
        log.info( "Reading window topics for window %d from %s ..." % ( window_num, in_path ) )
        # Load window results: (doc_ids, terms, term_rankings, partition, W, H, labels)
        window_res = unsupervised.nmf.load_nmf_results( in_path )
        window_doc_ids = window_res[0]
        window_k = len(window_res[2])
        window_partition = window_res[3]
        for window_topic_idx, window_topic_label in enumerate(window_res[6]):
            dynamic_topic_idx = assigned_window_map[window_topic_label]
            for i, doc_id in enumerate(window_doc_ids):
                if window_partition[i] == window_topic_idx:
                    all_doc_ids.append( doc_id )
                    all_partition.append( dynamic_topic_idx )

    log.info("Created overall partition covering %d documents" % len(all_doc_ids) )

    # TODO: fix W and H
    if options.out_path is None:
        results_out_path = "dynamic-combined.pkl"
    else:
        results_out_path = options.out_path
    unsupervised.nmf.save_nmf_results( results_out_path, all_doc_ids, dynamic_res[1], dynamic_res[2], all_partition, None, None, dynamic_res[6] )

# --------------------------------------------------------------

if __name__ == "__main__":
    options,args = get_options()
    main(options,args)
