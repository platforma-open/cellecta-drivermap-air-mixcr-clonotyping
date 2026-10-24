#!/usr/bin/env python3
import argparse
import pandas as pd
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import KernelDensity
from scipy.signal import find_peaks, argrelextrema
from scipy.stats import iqr

######
### qc_mixcr_output -- check quality of MiXCR output
###	inputs: 
###    input_file = file containing all clonotypes from MiXCR with VBC preset
### outputs:
###    qc_ok = TRUE or FALSE
######

def qc_mixcr_output(input_file):
    
    print("Running clonotype qc...")    
    
    # Read TSV file
    df = pd.read_csv(input_file, sep='\t', low_memory=False)
    
    # Check that there are at least N number of clonotypes in df
    clonotype_count = df.shape[0]
    if clonotype_count < 1000:
        return False
    
    return True

######
### barcode_hopping_filter -- barcode hopping filter; remove VBCs with low reads relative to other VBCs of the same clonotype sequence
###	inputs: 
###    input_file = file containing all clonotypes from MiXCR with VBC preset
###    percentage = cutoff percentage of reads that a VBC must have to be considered non-barcode hopping 
### outputs:
###    output = barcode hopping filtered tsv
######

def barcode_hopping_filter(input_file, percentage, mode="bulk"):
    
    print("Running barcode hopping filtering...")    
    
    # Read TSV file
    df = pd.read_csv(input_file, sep='\t', low_memory=False)
    if mode == "single_cell":
        group_cols = ['cloneId', 'tagValueMIWELLNAME']
    else:
        group_cols = ['cloneId']
    # Calculate maximum read count per cloneId/tagValueMIWELLNAME group
    df['group_max'] = df.groupby(group_cols)['readCount'].transform('max')
    
    # Filter rows where readCount >= fraction_threshold of group maximum
    fraction_threshold = percentage/100
    filtered_df = df[df['readCount'] >= fraction_threshold * df['group_max']].copy()
    
    # Clean up temporary column
    filtered_df.drop(columns=['group_max'], inplace=True)
    
    # Print Stats
    original_rows = df.shape[0]
    filtered_rows = filtered_df.shape[0]    
    original_rows_readSum = int(df['readCount'].sum())
    filtered_rows_readSum = int(filtered_df['readCount'].sum())
    print(f"Original number of rows: {original_rows:,}")
    print(f"Original number of reads: {original_rows_readSum:,}")
    print(f"Final number of rows after barcode hopping filtering: {filtered_rows:,}")
    print(f"Final number of reads after barcode hopping filtering: {filtered_rows_readSum:,}")
    print(f"Reads removed: {original_rows_readSum - filtered_rows_readSum:,} "
          f"({(original_rows_readSum - filtered_rows_readSum)/original_rows_readSum:.1%})")
    print()

    # Return filtered data    
    return filtered_df

######
### find_kde_mimima_threshold -- function to model histograms by KDE and find maximas/minimas;
###    helper function for reads_per_clonotype_filter
######

def find_kde_mimima_threshold(data, barcode_count, sample_name, default_low_thresh, min_valley_depth=0.10):
    """Finds threshold using KDE minima detection between two highest maxima."""

    # Function return format: (threshold cutoff, left peak max, right peak max, threshold cutoff kde value)
             
    if len(data) < 10:
        return (default_low_thresh,            # threshold cutoff
                float('nan'),                  # left peak max location
                float('nan'),                  # right peak max location
                float('nan'),                  # threshold cutoff KDE value
                float('nan'),                  # left peak max KDE value
                float('nan')                   # right peak max KDE value
        )
    
    data_array = np.log10(data[data > 0].values).reshape(-1, 1)
    
    # Adaptive bandwidth selection
    #bandwidth = 0.5 * data_array.std()
    n = len(data_array)
    sigma = np.std(data_array, ddof=1)
    bandwidth = 1.06 * sigma * (n ** (-1/5))
    if bandwidth == 0 or np.isnan(bandwidth):
        return (default_low_thresh,            # threshold cutoff
                float('nan'),                  # left peak max location
                float('nan'),                  # right peak max location
                float('nan'),                  # threshold cutoff KDE value
                float('nan'),                  # left peak max KDE value
                float('nan')                   # right peak max KDE value
        )
    
    # Perform KDE analysis
    kde = KernelDensity(bandwidth=bandwidth)
    kde.fit(data_array)
    x = np.linspace(data_array.min(), data_array.max(), 1000).reshape(-1, 1)
    log_dens = kde.score_samples(x)
    
    # Find local minima and maxima
    minima = argrelextrema(log_dens, np.less)[0]
    maxima = argrelextrema(log_dens, np.greater)[0]

    # Check if we have at least two maxima
    if len(maxima) == 0:
        return (default_low_thresh,            # threshold cutoff
                float('nan'),                  # left peak max location
                float('nan'),                  # right peak max location
                float('nan'),                  # threshold cutoff KDE value
                float('nan'),                  # left peak max KDE value
                float('nan')                   # right peak max KDE value
        )
    
    if len(maxima) == 1:
        left_max = 0 # setting the first peak as non-existent at 0
        right_max = maxima[0]
        
        # Find minima between these two maxima
        between_minima = minima[(minima > left_max) & (minima < right_max)]
        if between_minima.size > 0:
            # Select the most prominent minimum (lowest log density)
            selected_min = between_minima[np.argmin(log_dens[between_minima])]
            return (10**x[selected_min][0],            # threshold cutoff 
                    10**x[left_max][0],                # left peak max location 
                    10**x[right_max][0],               # right peak max location
                    np.exp(log_dens[selected_min]),    # threshold cutoff KDE value 
                    np.exp(log_dens[left_max]),        # left peak max KDE value
                    np.exp(log_dens[right_max])        # right peak max KDE value
            )
        
        # unlikely case because there's a maxima (so there has to be a low point)
        if between_minima.size == 0:
            return (default_low_thresh,                  # threshold cutoff 
                    10**x[left_max][0],                  # left peak max location 
                    10**x[right_max][0],                 # right peak max location
                    np.exp(log_dens[default_low_thresh]),# threshold cutoff KDE value
                    np.exp(log_dens[left_max]),          # left peak max KDE value
                    np.exp(log_dens[right_max])          # right peak max KDE value
            )
            
    if len(maxima) == 2:
        # Get two highest maxima (by log density)
        sorted_maxima = maxima[np.argsort(-log_dens[maxima])]
        top_two_max = sorted_maxima[:2]
        left_max, right_max = sorted(top_two_max)
                
        # Find minima between these two maxima
        between_minima = minima[(minima > left_max) & (minima < right_max)]
        selected_min = between_minima[np.argmin(log_dens[between_minima])]
    
    elif len(maxima) > 2:
        # Find the lowest minimum (by log density)
        leftmost_max = np.min(maxima)
        rightmost_max = np.max(maxima)
        between_minima = minima[(minima > leftmost_max) & (minima < rightmost_max)]
        
        # For each candidate minimum, find the minima that provides best separation between left peaks and right peaks
        best_score = None
        best_min = None
        for candidate_min in between_minima:
            left_maximas = maxima[maxima < candidate_min]
            right_maximas = maxima[maxima > candidate_min]
            # Sum of squared distances to cluster means
            left_mean = np.mean(left_maximas)
            right_mean = np.mean(right_maximas)
            left_ssd = np.sum((left_maximas - left_mean) ** 2)
            right_ssd = np.sum((right_maximas - right_mean) ** 2)
            total_ssd = left_ssd + right_ssd
            # Select minimum total within-cluster sum of squares (similar to kmeans)
            if (best_score is None) or (total_ssd < best_score):
                best_score = total_ssd
                best_min = candidate_min
        
        if best_min is not None:
            selected_min = best_min
            left_maximas = maxima[maxima < selected_min]
            right_maximas = maxima[maxima > selected_min]
            left_max = left_maximas[np.argmax(log_dens[left_maximas])]
            right_max = right_maximas[np.argmax(log_dens[right_maximas])]           
            
    # Check if the selected minimum is a valid valley
    min_log_dens = log_dens[selected_min]
    left_peak = log_dens[left_max]
    right_peak = log_dens[right_max]

    # Calculate relative depth of valley compared to smaller peak
    peak_max_lower = min(left_peak, right_peak)
    relative_depth = abs((peak_max_lower - min_log_dens)/peak_max_lower)
    if relative_depth >= min_valley_depth:
        return (10**x[selected_min][0],            # threshold cutoff 
                10**x[left_max][0],                # left peak max location 
                10**x[right_max][0],               # right peak max location
                np.exp(log_dens[selected_min]),    # threshold cutoff KDE value
                np.exp(log_dens[left_max]),        # left peak max KDE value
                np.exp(log_dens[right_max])        # right peak max KDE value
        )
    else:
        # Valley is too shallow, consider as one peak
        zero_left_max = 0
        return (default_low_thresh,                  # threshold cutoff 
                zero_left_max,                       # left peak max location 
                10**x[right_max][0],                 # right peak max location
                np.exp(log_dens[default_low_thresh]),# threshold cutoff KDE value
                np.exp(log_dens[zero_left_max]),     # left peak max KDE value
                np.exp(log_dens[right_max])          # right peak max KDE value
        )

######
### is_normalization_reliable -- check reliability of normalization threshold for a VBC bin
###    helper function for reads_per_clonotype_filter
######

def is_normalization_unreliable(nVBC, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values):
    """
    Checks if normalization threshold for a VBC bin is reliable.
    Returns True if reliable, False otherwise.
    """
    unreliable_norm_flag = False
    print(f"Checking reliability of normalization for VBC = {nVBC}...")

    # VBC = nVBC Statistics
    vbc_reads = clone_total_reads[clone_total_reads['barcode_count'] == nVBC]['readCount']
    vbc_thresh = thresholds.get(nVBC, None)
    vbc_thresh_kde_value = thresholds_kde_values.get(nVBC, None)
    vbc_peak = right_maxes.get(nVBC, None)
    vbc_peak_kde_values = right_maxes_kde_values.get(nVBC, None)
    
    # Thresholding cutoffs
    min_vbc_points = 10  # Minimum required data points for VBC = nVBC
    min_peak_distance = 2  # Minimum fold distance between threshold and 2nd peak
    min_peak_height_diff = 2  # Minimum KDE fold height difference between threshold and 2nd peak
    
    # Check that none of the measured variables are NA
    if np.isnan(vbc_thresh) or np.isnan(vbc_thresh_kde_value) or np.isnan(vbc_peak) or np.isnan(vbc_peak_kde_values):
        print(f"WARNING: NaN value for either threshold or right max peak.")
        unreliable_norm_flag = True

    # Check that the number of data points approximating the VBC = nVBC normalization value is sufficient
    num_above_thresh = (vbc_reads > vbc_thresh).sum()
    if num_above_thresh < min_vbc_points:
        print(f"WARNING: Too few data points in VBC bin passing threshold. Normalization may be unreliable.")
        unreliable_norm_flag = True
    
    # Check that the second peak is sufficiently far from the threshold OR is sufficiently higher than the threshold
    if vbc_thresh*min_peak_distance > vbc_peak or vbc_thresh_kde_value*min_peak_height_diff > vbc_peak_kde_values:
        print(f"WARNING: Second peak and threshold value too close in VBC. Normalization may be unreliable.")
        unreliable_norm_flag = True
    
    return unreliable_norm_flag

######
### reads_per_clonotype_filter -- filter clonotypes with low number of reads using VBC bins
### inputs:
###     input_file = barcode hopping filter data frame
###     sample_name = prefix name of output file
### outputs: 
###     output_file = clonotypes filtered by the number of reads
######
    
def reads_per_clonotype_filter(input_file, directory, sample_name, default_low_thresh, mode="bulk"):
    
    print("Running VBC filtering...")
    
    df = input_file
    if mode == "single_cell":
        group_cols = ['cloneId', 'tagValueMIWELLNAME']
        n_barcodes = 4
    else:
        group_cols = ['cloneId']
        n_barcodes = 8
    # Calculate barcode counts and total reads per cloneId/tagValueMIWELLNAME
    clone_barcode_counts = df.groupby(group_cols)['tagValueMIBC'].nunique()
    clone_total_reads = df.groupby(group_cols)['readCount'].sum().reset_index()
    clone_total_reads['barcode_count'] = clone_total_reads.set_index(group_cols).index.map(clone_barcode_counts)
    
    #---------------------------------------------------------------------------------------------------#
    #---------------------------------------------------------------------------------------------------#

    # KDE analysis:
    
    thresholds = {}
    left_maxes = {}
    right_maxes = {}
    thresholds_kde_values = {}
    left_maxes_kde_values = {}
    right_maxes_kde_values = {}  
    for barcode_count in range(1, n_barcodes + 1):
        subset = clone_total_reads[clone_total_reads['barcode_count'] == barcode_count]['readCount']
        (
            thresholds[barcode_count],
            left_maxes[barcode_count],
            right_maxes[barcode_count],
            thresholds_kde_values[barcode_count],
            left_maxes_kde_values[barcode_count],
            right_maxes_kde_values[barcode_count]
        ) = find_kde_mimima_threshold(subset, barcode_count, sample_name, default_low_thresh)
    
    #---------------------------------------------------------------------------------------------------#
    #---------------------------------------------------------------------------------------------------#
    
    # Threshold checks:

    # Check results of KDE analysis across 8 barcodes before writing to file and performing filtering
    # in certain cases, the VBC = 4 or higher have no first peak but there might be a small peak after the second peak 
    # for a couple of clonotypes. we know that the increase of values from VBC = 1, 2, etc is a slight doubling, so
    # we're using this information to check if the value of the filter went haywire. the cutoff that we're using is 20x
    # increase.
    
    sorted_keys = sorted(thresholds.keys())
    original_thresholds = thresholds.copy()

    for i in range(1, len(sorted_keys)):

        current_key = sorted_keys[i]
        previous_key = sorted_keys[i - 1]
        
        # (1) Check if the neighboring thresholds are much different from one another
        # check if previous threshold is 20x less than the current threshold (previousThresholdFoldx)
        if thresholds[current_key] is not default_low_thresh and thresholds[previous_key] is not default_low_thresh:
            if current_key > 3: # prevents threshold changes in cases where VBC = 1, 2 are much lower than the rest
                previousThresholdFoldx = thresholds[current_key] > 20 * thresholds[previous_key]
            else:
                previousThresholdFoldx = False
        else: 
            previousThresholdFoldx = False
        
        # check if next threshold is 10x more than the current threshold (nextThresholdFoldx)   
        if thresholds[current_key] is not default_low_thresh and current_key < len(sorted_keys):
            next_key = sorted_keys[i + 1]
            if thresholds[next_key] is not default_low_thresh:
                nextThresholdFoldx = thresholds[next_key] > 20 * thresholds[current_key]
            else:
                nextThresholdFoldx = False
        else:
            nextThresholdFoldx = False
        
        # modify thresholds file if previousThresholdFoldx or nextThresholdFoldx is True
        if previousThresholdFoldx or nextThresholdFoldx: 
            thresholds[current_key] = thresholds[previous_key]					
        
        # (2) Check if the thresholds are lower than the previous threshold
        if thresholds[current_key] < thresholds[previous_key]:
            thresholds[current_key] = thresholds[previous_key]
    
    #---------------------------------------------------------------------------------------------------#
    #---------------------------------------------------------------------------------------------------#

    # Normalization value reliability checks:

    # Checks to make sure that the VBC=1 normalization value is reliable. It checks as to 
    # whether there are enough data points in the VBC=1 bin and whether the threshold and
    # second peak are sufficiently separated.
    
    # Check reliability of VBC = 1 normalization, if reliable dont change normalization value. 
    # If not, check VBC = 2 normalization reliability. If reliable, use VBC = 2 threshold for VBC = 1. 
    # If not, check VBC = 3 normalization reliability. If reliable, use VBC = 3 threshold for VBC = 1.
    # If not, set VBC = 1 normalization to NaN to prevent normalization. 

    vbc1_unreliability = is_normalization_unreliable(1, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values)
    if vbc1_unreliability == True:
        print(f"WARNING: VBC=1 normalization may be unreliable.")
        vbc2_unreliability = is_normalization_unreliable(2, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values)
        if vbc2_unreliability == True:
            print(f"WARNING: VBC=2 normalization may be unreliable.")
            vbc3_unreliability = is_normalization_unreliable(3, clone_total_reads, thresholds, thresholds_kde_values, right_maxes, right_maxes_kde_values)
            if vbc3_unreliability == True:
                print(f"WARNING: VBC=3 normalization may be unreliable.")      
                right_maxes[1] = float('nan')
            else:
                right_maxes[1] = right_maxes[3]/3 # peak of VBC = 3 is 3x that of VBC = 1
        else:
            right_maxes[1] = right_maxes[2]/2 # peak of VBC = 2 is 2x that of VBC = 1
    
    #---------------------------------------------------------------------------------------------------#
    #---------------------------------------------------------------------------------------------------#            
    
    # Save maxima and threshold locations to a file
    maximas_file = os.path.join(directory, f"{sample_name}.kde.maximas.txt")
    with open(maximas_file, "a") as f:
        for barcode_count in range(1, n_barcodes + 1):
            # write in csv: thresholds, left max right max
            f.write(f"{barcode_count}\t{thresholds[barcode_count]}\t{left_maxes[barcode_count]}\t{right_maxes[barcode_count]}\t{thresholds_kde_values[barcode_count]}\t{left_maxes_kde_values[barcode_count]}\t{right_maxes_kde_values[barcode_count]}\n")
            # write in csv: thresholds, left max, right max, threshold density, left max density, right max density
            #f.write(f"{barcode_count}\t{thresholds[barcode_count]}\t{left_maxes[barcode_count]}\t{right_maxes[barcode_count]}\n")
    
    # Plot histograms and KDEs for clones
    histogram_file = os.path.join(directory, f"{sample_name}.histograms.pdf")
    fig, axes = plt.subplots(nrows=1 if n_barcodes <= 4 else 2, ncols=n_barcodes if n_barcodes <= 4 else 4, figsize=(4*n_barcodes if n_barcodes <= 4 else 16, 8 if n_barcodes > 4 else 4))
    axes = axes.flatten() if n_barcodes > 1 else [axes]
    for i, barcode_count in enumerate(range(1, n_barcodes + 1)):
        subset = clone_total_reads[clone_total_reads['barcode_count'] == barcode_count]

        if not subset.empty:
            ax = axes[i]
            sns.histplot(subset['readCount'], bins=30, kde=True, ax=ax, log_scale=True)

            threshold = thresholds.get(barcode_count)
            if threshold and not np.isnan(threshold):
                ax.axvline(threshold, color='red', linestyle='dashed', linewidth=2)
                ax.text(threshold, ax.get_ylim()[1] * 0.8, f'Threshold: {int(threshold)}',
                        color='red', ha='right', fontsize=10, weight='bold')

            ax.set_title(f'Clones in {barcode_count} Barcodes')
            ax.set_xlabel('Total Reads (log scale)')
            ax.set_ylabel('Frequency')

    plt.tight_layout()
    plt.savefig(histogram_file)
    plt.close()

    # Apply thresholds to clones
    clone_total_reads = clone_total_reads.copy()
    clone_total_reads.loc[:, 'keep'] = clone_total_reads.apply(
        lambda row: row['readCount'] >= thresholds.get(row['barcode_count'], np.inf),
        axis=1
    )
    clones_to_keep = clone_total_reads[clone_total_reads['keep']][group_cols]
    final_data = df.merge(clones_to_keep, on=group_cols, how='inner').copy()

    # Group final data by cloneId/tagValueMIWELLNAME and calculate summary statistics
    grouped_final_data = final_data.groupby(group_cols).first().reset_index()
    grouped_final_data['readCount'] = final_data.groupby(group_cols)['readCount'].sum().values
    grouped_final_data['barcode_count'] = grouped_final_data.set_index(group_cols).index.map(clone_barcode_counts)
    grouped_final_data = grouped_final_data.drop(columns=['tagValueMIBC'], errors='ignore')
    grouped_final_data = grouped_final_data.sort_values("readCount", ascending=False)

    # Print summary statistics
    original_rows = df.shape[0]
    filtered_rows = int(grouped_final_data['barcode_count'].sum())
    original_rows_readSum = int(df['readCount'].sum())
    filtered_rows_readSum = int(grouped_final_data['readCount'].sum())
    print(f"Original number of rows: {original_rows:,}")
    print(f"Original number of reads: {original_rows_readSum:,}")
    print(f"Final number of rows after mutated sequence filtering: {filtered_rows:,}")
    print(f"Final number of reads after mutated sequence filtering: {filtered_rows_readSum:,}")
    print(f"Reads removed: {original_rows_readSum - filtered_rows_readSum:,} "
          f"({(original_rows_readSum - filtered_rows_readSum)/original_rows_readSum:.1%})")
    print()

    return grouped_final_data

######
### simplify_clonotypes_table -- simplifies clonotype table by creating one row for each clonotype and extra columns for each VBC count;
###     helper function for filter_passing_clonotypes
######

def simplify_clonotypes_table(df_filtered, mode="bulk"):
    """
    Simplifies the clonotypes table by creating read counts column for each VBC 
    This reduces the number of rows on the table
    Then it creates a new column for the total read counts called readCount
    """
    if mode == "single_cell":
        index_cols = ['cloneId', 'tagValueMIWELLNAME']
    else:
        index_cols = ['cloneId']
    # Create simplified table for readCount values, set value to 0 if the BC does not have a particular clonotype
    df_pivot = df_filtered.pivot_table(
        index=index_cols,
        columns='tagValueMIBC',
        values='readCount',
        fill_value=0
    ).add_prefix('readCount_')

    for bc in [f'BC{i}' for i in range(1, 9)]:
        col_name = f'readCount_{bc}'
        if col_name not in df_pivot.columns:
            df_pivot[col_name] = 0
    
    # Reorder columns and add total readCount column
    bc_columns = [f'readCount_BC{i}' for i in range(1, 9)]
    df_pivot = df_pivot[bc_columns]
    df_pivot['readCount'] = df_pivot.sum(axis=1)

    # Get metadata from row with max readCount per cloneId/tagValueMIWELLNAME
    idx = df_filtered.groupby(index_cols)['readCount'].idxmax()
    other_columns = df_filtered.columns.difference(
        ['tagValueMIBC', 'readCount', 'readFraction']
    )
    df_other = df_filtered.loc[idx, other_columns].reset_index(drop=True)
    
    # Merge pivot table with metadata
    df_final = df_pivot.reset_index().merge(
        df_other,
        on=index_cols,
        how='left'
    )
    
    return df_final

######
### filter_passing_clonotypes -- generate final table of passing clonotypes
### inputs:
###     df_bcHop_filtered = barcode hopping filtered df (output of barcode_hopping_filter)
###     df_rpclon_filtered = reads per clonotype filtered df (output of reads_per_clonotype_filter)
###     sample_name = sample name
### outputs: 
###     df_passing_clonotypes = simplified df post-barcode hopping and reads per clonotype filters
######

def filter_passing_clonotypes(df_bcHop_filtered, df_rpclon_filtered, mode="bulk"):

    if mode == "single_cell":
        # Filter by both targetSequences and tagValueMIWELLNAME
        key_cols = ["targetSequences", "tagValueMIWELLNAME"]
        df_rpclon_filtered = df_rpclon_filtered.dropna(subset=["targetSequences", "tagValueMIWELLNAME"])
        keys = set(tuple(x) for x in df_rpclon_filtered[key_cols].values)
        df_filtered = df_bcHop_filtered[
            df_bcHop_filtered[key_cols].apply(tuple, axis=1).isin(keys)
        ]
    else:
        # Bulk mode: filter by targetSequences only
        unique_target_sequences = set(df_rpclon_filtered["targetSequences"].dropna())
        df_filtered = df_bcHop_filtered[df_bcHop_filtered["targetSequences"].isin(unique_target_sequences)]

    # Create simplified data frame with simplify_clonotypes_table
    df_simplified = simplify_clonotypes_table(df_filtered, mode=mode)

    return df_simplified
    
######
### main 
### inputs:
###     input_file = file containing all clonotypes from MiXCR with VBC preset
###     directory = location of mixcr files (set as "", i.e. blank, if working in Platforma)
###     sample_name = sample name
### outputs: 
###     df_passing_clonotypes = simplified df post-barcode hopping and reads per clonotype filters
######
    
def main(input_file, directory, sample_name, mode="bulk"):
    """
    Step 1: barcode_hopping_filter -- filter barcode hopping 
    Step 2: reads_per_clonotype_filter -- filter low read count clonotypes
    Step 3: filter_passing_clonotypes -- generate final table
    """
    
    default_low_thresh = 2 # default value for threshold for VBC clonotype filtering
    
    # Validate Inputs
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)
    
    percentage = 5 # default setting for barcode hopping filter
    mixcr_clones_file = input_file
    
    # Check Data Quality
    
    qcIsGood = qc_mixcr_output(mixcr_clones_file)
    output_filename = f"{sample_name}.clones_ALL.filtered.tsv"
    output_path = os.path.join(directory, output_filename)	
    
    if qcIsGood:
        
        # Run VBC filtering steps if data quality is good
        df_bcHop_filtered = barcode_hopping_filter(mixcr_clones_file, percentage, mode=mode)
        df_rpclon_filtered = reads_per_clonotype_filter(df_bcHop_filtered, directory, sample_name, default_low_thresh, mode=mode)
        df_passing_clonotypes = filter_passing_clonotypes(df_bcHop_filtered, df_rpclon_filtered, mode=mode)
    
        df_passing_clonotypes = df_passing_clonotypes.sort_values(by=['readCount'], ascending = False)
        df_passing_clonotypes.to_csv(output_path, sep="\t", index=False)
    
    else:
        
        # Return the same MiXCR output file if the QC is not good
        df = pd.read_csv(mixcr_clones_file, sep='\t', low_memory=False)    
        df.to_csv(output_path, sep="\t", index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quality control filtering using VBCs for Cellecta DriverMap AIR.")
    parser.add_argument("input_file", type=str, help="Path to input TSV file.")
    parser.add_argument("directory", type=str, help="Directory of MiXCR output files")
    parser.add_argument("sample_name", type=str, help="Prefix for output files.")
    parser.add_argument("--mode", type=str, choices=["bulk", "single_cell"], default="bulk", help="Processing mode: 'bulk' or 'single_cell' DriverMap AIR.")
    args = parser.parse_args()
    main(args.input_file, args.directory, args.sample_name, mode=args.mode)
