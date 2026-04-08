import pandas as pd
import sys

def explore_excel_file(file_path):
    print(f"=== Exploring {file_path} ===")
    try:
        xls = pd.ExcelFile(file_path)
        print(f"Sheet names: {xls.sheet_names}")
        
        for sheet in xls.sheet_names:
            print(f"\n--- Sheet: {sheet} ---")
            df = pd.read_excel(xls, sheet_name=sheet)
            print(f"Total records: {len(df)}")
            print(f"Columns: {list(df.columns)}")
            
            # Check key columns
            key_cols = {
                'wifi_format': 'wifi_format' in df.columns,
                'rate': 'rate' in df.columns,
                'tx_power_set(dBm)': 'tx_power_set(dBm)' in df.columns,
                'evm': 'evm' in df.columns,
                'rf_chan': 'rf_chan' in df.columns
            }
            print(f"Key columns present: {key_cols}")
            
            # Show sample values
            if 'wifi_format' in df.columns:
                print(f"Unique wifi_format values: {df['wifi_format'].unique()[:5]}")
            if 'rate' in df.columns:
                print(f"Unique rate values: {df['rate'].unique()[:5]}")
            if 'tx_power_set(dBm)' in df.columns:
                print(f"TX power range: {df['tx_power_set(dBm)'].min():.2f} to {df['tx_power_set(dBm)'].max():.2f} dBm")
            if 'evm' in df.columns:
                print(f"EVM range: {df['evm'].min():.2f} to {df['evm'].max():.2f} dB")
                
    except Exception as e:
        print(f"Error exploring file: {e}")
        import traceback
        print(traceback.format_exc())

def main():
    if len(sys.argv) < 2:
        print("Usage: python explore_excel.py <excel_file_path>")
        return
    
    file_path = sys.argv[1]
    explore_excel_file(file_path)

if __name__ == "__main__":
    main()
