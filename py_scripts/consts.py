import hashlib

days_from_num_to_full_text = {0: "Понедельник", 1: "Вторник", 2: "Среда", 3: "Четверг", 4: "Пятница", 5: "Суббота"}
days_from_short_text_to_num = {'Пн': 0, 'Вт': 1, 'Ср': 2, 'Чт': 3, 'Пт': 4, 'Сб': 5}
lessons_keys = {'0️⃣-й урок, 8:30 - 8:55:\n': '0\n08:30 - 08:55',
                    '1️⃣-й урок, 9:00 - 9:45:\n': '1\n09:00 - 09:45',
                    '2️⃣-й урок, 9:55 - 10:40:\n': '2\n09:55 - 10:40',
                    '3️⃣-й урок, 10:50 - 11:35:\n': '3\n10:50 - 11:35',
                    '4️⃣-й урок, 11:45 - 12:30:\n': '4\n11:45 - 12:30',
                    '5️⃣-й урок, 12:50 - 13:35:\n': '5\n12:50 - 13:35',
                    '6️⃣-й урок, 13:55 - 14:40:\n': '6\n13:55 - 14:40',
                    '7️⃣-й урок, 14:50 - 15:35:\n': '7\n14:50 - 15:35',
                    '8️⃣-й урок, 15:45 - 16:30:\n': '8\n15:45 - 16:30'}

path_to_timetables = 'timetables/'
path_to_changes = 'changes_tt/'
path_to_timetables_csv = 'timetables_csv/'

password_hash = 'ba99373a11053f09dab43e2485c86e593bb6d2c5f469e8e7680bf5718d1850dc'


def my_hash(text):
    try:
        hash_obj = hashlib.sha256(text.encode('ascii'))
        hex_hash = hash_obj.hexdigest()
        return hex_hash
    except Exception:
        return '402'
