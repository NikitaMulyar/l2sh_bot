import requests


res = requests.get('https://engine.lifeis.porn/api/millionaire.php', params={
    'qType': 1, 'count': 2
}).json()
print(res)