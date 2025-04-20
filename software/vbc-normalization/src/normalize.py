import pandas as pd
import os
import math
import argparse

def quantify_templates(maxima_file, input_file, output_file):
    
    # Get normFactor from kde.maximas file
    try:
        # Check if maxima file is empty
        if os.path.getsize(maxima_file) == 0:
            print("Maxima file is empty. Creating empty output file with headers.")
            # Read input file to get columns
            input_df = pd.read_csv(input_file, sep='\t')
            # Create empty dataframe with same columns plus templateEstimate
            empty_df = pd.DataFrame(columns=input_df.columns.tolist() + ['templateEstimate', 'templateEstimateFraction'])
            # Save to output file
            empty_df.to_csv(output_file, sep='\t', index=False)
            return
        
        maxima_df = pd.read_csv(maxima_file, sep='\t', header=None)
        normFactor = float(maxima_df.iloc[0, 3])
    except Exception as e:
        print(f"Error reading maxima file: {str(e)}")
        return

    # Process each chain type
    try:
        df = pd.read_csv(input_file, sep='\t')            
        if 'readCount' in df.columns:
            df['templateEstimate'] = df['readCount'].apply(
                lambda x: math.ceil(x / normFactor)
            )
            df['templateEstimateFraction'] = df['templateEstimate'] / df['templateEstimate'].sum()
            df.to_csv(output_file, sep='\t', index=False)
        else:
            print(f"'readCount' column missing in {input_file}")
            
    except Exception as e:
        print(f"Error processing: {str(e)}")
            

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Quantify templates based on normFactor")
    parser.add_argument("maxima_file", help="maxima_file")
    parser.add_argument("input_file", help="input_file")
    parser.add_argument("output_file", help="output_file")

    # Parse arguments
    args = parser.parse_args()
    
    # Run the processing function
    quantify_templates(args.maxima_file, args.input_file, args.output_file)
