import pandas as pd


df = pd.read_excel('exams.xlsx', engine='openpyxl')
print(df.to_string())
df2 = pd.read_csv('График контрольных работ 23-24 - Лист1.csv')
print(df.to_string())