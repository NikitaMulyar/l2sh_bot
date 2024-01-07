path_to_timetables = 'timetables/'
path_to_changes = 'changes_tt/'
path_to_timetables_csv = 'timetables_csv/'

password_hash = 'ba99373a11053f09dab43e2485c86e593bb6d2c5f469e8e7680bf5718d1850dc'

import hashlib


def my_hash(text):
    try:
        hash_obj = hashlib.sha256(text.encode('ascii'))
        hex_hash = hash_obj.hexdigest()
        return hex_hash
    except Exception:
        return '402'
