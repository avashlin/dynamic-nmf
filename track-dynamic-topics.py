#!/usr/bin/env python
"""
Script to track the individual topics from each window that contribute to an overall set of dynamic topics.

Usage: 
python track-dynamic-topics.py -l out/dynamictopics_k05.pkl out/month1_windowtopics_k05.pkl out/month2_windowtopics_k05.pkl out/month3_windowtopics_k05.pkl
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
    parser.add_option("-t", "--top", action="store", type="int", dest="top", help="number of top terms to display", default=10)
    parser.add_option("-l","--long", action="store_true", dest="long_display", help="long format display")
    parser.add_option("-d", "--dynamic", action="store", type="string", dest="dynamic_required", help="to view a subset of dynamic topics, specify one or more topic numbers comma separated", default=None)
    parser.add_option("-o","--output", action="store",type="string",dest="output_path",help="output_file", default=None)
    parser.add_option("-s","--selected_file", action="store",type="string",dest="selected_file",help="file containing the optimal number for k for different windows", default=None)
    parser.add_option("-p","--pattern", action="store",type="string",dest="pattern",help="pattern to use for selecting the models to use", default=None)
    parser.add_option("-b","--base_path", action="store",type="string",dest="window_base_path",help="the directory that contains the window models", default="")
    
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

    if options.output_path is None:
        log.basicConfig(level=20, format='%(message)s')
    else:
        log.basicConfig(level=20, format="%(message)s",filename=options.output_path)

    # Load dynamic results: (doc_ids, terms, term_rankings, partition, W, H, labels)
    dynamic_in_path = options.dynamic_model#args[0]
    dynamic_res = unsupervised.nmf.load_nmf_results( dynamic_in_path )
    dynamic_k = len(dynamic_res[2])
    dynamic_term_rankings = unsupervised.rankings.truncate_term_rankings( dynamic_res[2], options.top )

    log.info( "Loaded model with %d dynamic topics from %s" % (dynamic_k, dynamic_in_path) )

    # Create a map of window topic label -> dynamic topic
    assigned_window_map = {}
    dynamic_partition = dynamic_res[3]
    print(dynamic_res[0])
    for idx, window_topic_label in enumerate(dynamic_res[0]):
        assigned_window_map[window_topic_label] = dynamic_partition[idx]

    all_tracked_topics = []
    for i in range(dynamic_k):
        all_tracked_topics.append( [] )

    if not options.dynamic_required is None:
        dynamic_required = [ int(x) for x in options.dynamic_required.split(",") ]

    # Load all of the individual window topics models
    # Note: We should have one result for each window
    window_num = 0

    for in_path in files:
        window_num += 1
        log.debug( "Loading window topics for window %d from %s ..." % ( window_num, in_path ) )
        # Load window results: (doc_ids, terms, term_rankings, partition, W, H, labels)
        window_res = unsupervised.nmf.load_nmf_results( in_path )
        window_k = len(window_res[2])
        window_term_rankings = unsupervised.rankings.truncate_term_rankings( window_res[2], options.top )
        log.info( "Loaded model with %d window topics from %s" % (window_k, in_path) )
        for idx, window_topic_label in enumerate(window_res[6]):
            
            dynamic_topic_idx = assigned_window_map[window_topic_label]
            ranking = window_term_rankings[idx]
            all_tracked_topics[dynamic_topic_idx].append( (window_num,ranking) )

    # Now display each dynamic topic by building a PrettyTable
    for i in range(dynamic_k):
        # do we want to display this dynamic topic?
        if (not options.dynamic_required is None) and ( not (i+1) in dynamic_required ) :
            continue
        dynamic_topic_label = dynamic_res[6][i]
        log.info("- Dynamic Topic: %s" % dynamic_topic_label )
        # long format?
        if options.long_display:
            # standard format?
            current_labels = [ "Overall" ]
            current_rankings = [ dynamic_term_rankings[i] ]
            for t in all_tracked_topics[i]:
                current_labels.append( "Window %d" % t[0] )
                current_rankings.append( t[1] )
            log.info( unsupervised.rankings.format_term_rankings_long( current_rankings, current_labels, options.top ).strip() )
        else:
            header = ["Rank", "Overall"]
            for t in all_tracked_topics[i]:
                field = "Window %d" % t[0]
                # deal with multiple window topics from same window
                suffix = 1
                while field in header:
                    suffix += 1
                    field = "Window %d(%d)" % (t[0],suffix)
                header.append( field )
            tab = PrettyTable(header)
            tab.align["Rank"] = "r"
            for label in header[1:]:
                tab.align[label] = "l"
            # add the term rows
            for pos in range(options.top): 
                row = [ str(pos+1) ]
                # the term from the overall (dynamic) topic
                row.append( dynamic_term_rankings[i][pos] )
                # the term for each time window topic 
                for t in all_tracked_topics[i]:
                    # have we run out of terms?
                    if len(t[1]) <= pos:
                        row.append( "" ) 
                    else:
                        row.append( t[1][pos] ) 
                tab.add_row( row )
            log.info( tab )

# --------------------------------------------------------------

if __name__ == "__main__":
    options,args = get_options()
    main(options,args)
 
