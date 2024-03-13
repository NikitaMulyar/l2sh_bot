a = 'Пылева Т.csv'
b = 'Пылeва Т.csv'
for i in range(len('Пылeва Т.csv')):
    if a[i] != b[i]:
        print(ord(a[i]), ord(b[i]))

s = 'ёйцукенгшщзхъфывапролджэячсмитьбю'
for i in range(len('Пылeва Т.csv')):
    print(i, ord(a[i]), ord(b[i]))
print(ord('e'))