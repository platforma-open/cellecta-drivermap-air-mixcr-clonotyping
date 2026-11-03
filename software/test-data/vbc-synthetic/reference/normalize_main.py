import pandas as pd
import os
import math
import argparse
import numpy as np

######
### quantify_templates 
### inputs:
###     directory = location of mixcr files (set as "", i.e. blank, if working in Platforma)
###     sample_name =  sample name
### outputs: 
###     $SAMPLE_NAME.clones_ALL.quantified.tsv - clonotype table with molecular estimates (all chains in single table)
######

def quantify_templates(directory, sample_name, mode="bulk"):
    
    # Check if the analysis has already been completed
    report_file = f"{sample_name}.templateEstimation.report.txt"
    report_path = os.path.join(directory, report_file)
    if os.path.exists(report_path):
        print(f"Template estimation for {sample_name} has already completed. Will not run again...")
        return
    
    # Get normFactor from kde.maximas file
    
    maxima_file = f"{sample_name}.kde.maximas.txt"
    maxima_path = os.path.join(directory, maxima_file)

    if os.path.exists(maxima_path):    
        try:
            maxima_df = pd.read_csv(maxima_path, sep='\t', header=None)
            normFactor = float(maxima_df.iloc[0, 3])
        except Exception as e:
            print(f"Error reading maxima file: {str(e)}")
            return
    else:
        normFactor = float('nan')

    # Normalize read counts to template counts
    
    input_file = f"{sample_name}.clones_ALL.filtered.tsv"
    input_path = os.path.join(directory, input_file)
            
    try:
        df = pd.read_csv(input_path, sep='\t')
        if 'readCount' in df.columns:
            if not math.isnan(normFactor):
                df['templateEstimate'] = df['readCount'].apply(lambda x: int(np.floor(x / normFactor + 0.5)))  # avoids Python round's "banker's rounding"
                # count the number of 0s in templateEstimate which needs to be filtered
                before_rows = len(df)
                df = df[df['templateEstimate'] != 0].copy()
                normalizationFiltered = before_rows - len(df)
            else:
                df['templateEstimate'] = "NA"
            output_file = f"{sample_name}.clones_ALL.quantified.tsv"
            output_path = os.path.join(directory, output_file)
            df.to_csv(output_path, sep='\t', index=False)
            if os.path.exists(output_path):
                os.remove(input_path)
        else:
            print(f"'readCount' column missing in {input_file}")
    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")
            
    # Create report file
    round_normFactor = round(normFactor, 2)
    with open(report_path, 'w') as report:
        report.write("Template Estimation Analysis Completed\n")
        report.write(f"Norm Factor: {round_normFactor}\n")
        if 'normalizationFiltered' in locals():
            report.write(f"Normalization Filtered/Templates Estimated ~ 0: {normalizationFiltered} clonotypes removed\n")
        else:
            report.write("Normalization Filtered/Templates Estimated ~ 0: No clonotypes removed\n")
        if 'output_file' in locals():
            report.write("Processed Files:\n")
            report.write(f"- {output_file}\n") 
    
    print(f"Template estimation analysis completed for {sample_name}\n")

if __name__ == "__main__":
    # Set up argument Parser
    parser = argparse.ArgumentParser(description="Quantify templates based on normFactor")
    parser.add_argument("directory", help="Directory containing the sample_name files")
    parser.add_argument("sample_name", help="sample_name name")
    parser.add_argument("--mode", type=str, choices=["bulk", "single_cell"], default="bulk", help="Processing mode: 'bulk' or 'single_cell' DriverMap AIR.")

    # Parse arguments
    args = parser.parse_args()
    
    # Run the processing function
    quantify_templates(args.directory, args.sample_name, mode=args.mode)

