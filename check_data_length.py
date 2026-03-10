
import csv
import os

directory = r'D:\users\gxu\spur_scan\260228\dump'
for filename in os.listdir(directory):
    if filename.endswith('.csv'):
        file_path = os.path.join(directory, filename)
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            row_count = sum(1 for row in reader) - 1  # 减去标题行
            print(f'{filename}: {row_count} data rows')
