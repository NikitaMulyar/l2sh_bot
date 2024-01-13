from datetime import datetime

now_ = datetime.now()

tmp = '11.01.2024'.split('.')
edits_date = (int(tmp[2]), int(tmp[1]), int(tmp[0]))
today_date = (now_.year, now_.month, now_.day)
print(now_.isoformat())