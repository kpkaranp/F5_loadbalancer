import pandas as pd
import os

# Folder containing your Excel files
folder_path = './excel_files/'  # Change this to your actual path

# List to collect data from all files
combined_data = []

# Loop through all Excel files in the folder
for file_name in os.listdir(folder_path):
    if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
        file_path = os.path.join(folder_path, file_name)
        try:
            # Read first 6 rows and first 10 columns from the 'Summary' sheet
            df = pd.read_excel(file_path, sheet_name="Summary", nrows=6, usecols="A:J")
            df.insert(0, 'Source File', file_name)  # Add column for file name
            combined_data.append(df)
        except Exception as e:
            print(f"Error reading {file_name}: {e}")

# Combine all into one DataFrame
final_df = pd.concat(combined_data, ignore_index=True)

# Save the result to a new Excel file
output_path = 'combined_summary_6x10.xlsx'
final_df.to_excel(output_path, index=False)

print(f"Combined summary saved to: {output_path}")
