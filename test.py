import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import bs4
from datetime import date


soup = BeautifulSoup(open('Лист1.html').read(), 'html.parser')
result = []
txt_to_int = {'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'мая': 5,
              'июн': 6, 'авг': 8, 'сент': 9, 'окт': 10, 'ноя': 11, 'дек': 12}

fl = True
header = []
for link in soup.find_all('tr'):
    r = link.find_all('td')
    txts_cols = []
    i = 0
    for el in r:
        txts_cols.append([el.text, int(el.get('colspan', '1')), int(el.get('rowspan', '1'))])
    if txts_cols and (txts_cols[0][0] or txts_cols[1][0]):
        del txts_cols[2]
        txts_cols[0], txts_cols[1] = txts_cols[1], txts_cols[0]
        if txts_cols[0][0][0].isalpha():
            if fl:
                fl = False
                header = txts_cols.copy()
            continue
        tmp = [txt_to_int[i] for i in txt_to_int.keys() if i in txts_cols[0][0]]
        if tmp:
            tmp = tmp[0]
            year = date.today().year
            month = date.today().month
            if 7 <= tmp <= 11 and 0 <= month <= 5:
                year -= 1
            elif 7 <= month <= 11 and 0 <= tmp <= 5:
                year += 1
            txts_cols[0][0] = date(year, tmp, int(txts_cols[0][0].split()[0]))
        result.append(txts_cols)
len_ = len(result) + 1
matrix = [[] for i in range(len_)]
for el in header:
    if el[0]:
        for i in range(el[1]):
            matrix[0].append(el[0])
row_len = len(matrix[0])
for i in range(1, len_):
    matrix[i] = ['' for j in range(row_len)]

for i in range(len_ - 1):
    ind = 0
    for j in range(len(result[i])):
        for k in range(result[i][j][1]):
            matrix[i + 1][ind] = result[i][j][0]
            if isinstance(matrix[i + 1][ind], str):
                matrix[i + 1][ind] = matrix[i + 1][ind].strip()
            ind += 1
            if ind == row_len:
                break
        if ind == row_len:
            break
df = pd.DataFrame(matrix[1:], columns=matrix[0])
df.to_csv('bot_files/exams.csv', index=False)
df2 = pd.read_csv('bot_files/exams.csv')
# df2.replace('', np.nan, inplace=True)
# df2.dropna(inplace=True)
df2.fillna('', inplace=True)
# print(df2.head(20).to_string())
df2['6 А'] = df2['6 А'] + '###' + df2['6 А.1']
df2 = df2[['Дата', '6 А']]
df2['Дата'] = pd.to_datetime(df2['Дата'])
df2 = df2[df2['Дата'].dt.month == 9]
print(df2.head(60).to_string())
print(df2.index.values)
for i in range(len(df2.index.values)):
    t_ = df2.iloc[i]
    print(t_['Дата'].date().strftime('%d.%m.%Y'))
print('###5'.split('###'))
print('5###'.split('###'))