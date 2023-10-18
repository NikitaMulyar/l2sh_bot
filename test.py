from datetime import *
from consts import *
import os
import asyncio
import pdfplumber
import pandas as pd



async def save_edits_in_timetable_csv():
    # filename format: DD.MM.YYYY
    time_ = datetime.now()
    day_ = str(time_.day).rjust(2, '0')
    month_ = str(time_.month).rjust(2, '0')
    today_file = f'{day_}.{month_}.{time_.year}.pdf'

    path_ = path_to_changes + today_file
    dfs = []
    cabs = ['Класс', 'Урок №', 'Урок по расписанию', 'Замены кабинетов']
    lessons = ['Класс', 'Урок №', 'Урок по расписанию', 'Замены']
    fl_first_time = True
    are_working_with_cabs = False
    with pdfplumber.open(path_) as pdf:
        tables = []
        for page in pdf.pages:
            t = page.extract_tables()
            if len(t) == 1:
                tables.append(t[0])
            elif len(t) > 1:
                tables.extend(t)
        for table in tables:
            if len(table[0]) < 3:
                continue
                # какие-то беды с парсингом
            df = pd.DataFrame(table[1:], columns=table[0])
            df = df.fillna('')
            df = df.rename(columns={None: 'Замена2', 'Замена': 'Замены',
                                    'Замена кабинета': 'Замены кабинетов',
                                    "№\nурока": "Урок №",
                                    "№ урока": "Урок №",
                                    'Замена\nкабинета': 'Замены кабинетов',
                                    'Урок по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет по\nрасписанию': 'Урок по расписанию',
                                    'Урок и кабинет\nпо расписанию': 'Урок по расписанию'})
            if fl_first_time:
                cols_vals = df.columns.values
                if 'Замены' in cols_vals:
                    df['Замены'] = df['Замены'] + '//' + df['Замена2']
                    df.drop('Замена2', axis=1, inplace=True)
                fl_first_time = False
            if "Замены кабинетов" in df.columns.values:
                are_working_with_cabs = True
                for k in range(len(table)):
                    if table[k].count(None) == 2:
                        table[k] = [table[k][0], '', '', table[k][1]]
            fl_cabs = False
            fl_lessons = False
            for i in range(len(cabs)):
                if cabs[i] != df.columns.values[i]:
                    fl_cabs = True
                    break
            for i in range(len(lessons)):
                if lessons[i] != df.columns.values[i]:
                    fl_lessons = True
                    break
            if fl_lessons and fl_cabs and not are_working_with_cabs:
                for k in range(len(table)):
                    if len(table[k]) == 5:
                        table[k] = table[k][:3] + ["//".join(table[k][3:])]
                    else:
                        table[k] = table[k][:3] + [table[k][3] + "//"]
                df = pd.DataFrame(table, columns=list(dfs[-1].columns.values))
                df = df.fillna('')
                last = dfs[-1].index.values[-1]
                for ind in df.index.values:
                    df = df.rename(index={ind: last + ind + 1})
                # Далее: если формат такой, какой был 19.10.2023
                indexes = df.index.values
                curr_ind = indexes[-1] + 1
                for line in indexes:
                    if line == 0:
                        continue
                    classes = df.iloc[line]['Класс'].split('\n')
                    urok_num = df.iloc[line]['Урок №'].split('\n')
                    urok_po_rasp = df.iloc[line]['Урок по расписанию'].split('\n')
                    zameny = df.iloc[line]['Замены'].split('\n')
                    summ = 0
                    for i in ['6', '7', '8', '9', '10', '11']:
                        for cl in classes:
                            summ += cl.count(i)
                    if summ > 1:
                        urok_num = urok_num * summ
                        zameny = zameny * summ
                        df.at[line, 'Класс'] = classes[0]
                        df.at[line, 'Урок по расписанию'] = urok_po_rasp[0]
                        df.at[line, 'Урок №'] = urok_num[0]
                        df.at[line, 'Замены'] = zameny[0]
                        for i in range(1, summ):
                            df.loc[curr_ind] = [classes[i], urok_num[i], urok_po_rasp[i], zameny[i]]
                            curr_ind += 1
                    elif len(urok_num) != 1:
                        classes = classes * len(urok_num)
                        zameny_ = "\n".join(zameny)
                        lesson, teacher_ = zameny_.split('//')
                        lesson = lesson.split('\n')
                        teacher_ = teacher_.split('\n')
                        teacher = []
                        zameny = []
                        for i in range(0, len(teacher_), 2):
                            teacher.append(f"{teacher_[i]}\n{teacher_[i + 1]}")
                        for i in range(len(urok_num)):
                            zameny.append(f"{lesson[i]}//{teacher[i]}")
                        df.at[line, 'Класс'] = classes[0]
                        df.at[line, 'Урок по расписанию'] = urok_po_rasp[0]
                        df.at[line, 'Урок №'] = urok_num[0]
                        df.at[line, 'Замены'] = zameny[0]
                        for i in range(1, len(urok_num)):
                            df.loc[curr_ind] = [classes[i], urok_num[i], urok_po_rasp[i], zameny[i]]
                            curr_ind += 1
                dfs[-1] = pd.concat([dfs[-1], df], axis='rows')
            elif fl_lessons and fl_cabs and are_working_with_cabs:
                df = pd.DataFrame(table, columns=list(dfs[-1].columns.values))
                df = df.fillna('')
                last = dfs[-1].index.values[-1]
                for ind in df.index.values:
                    df = df.rename(index={ind: last + ind + 1})
            else:
                indexes = df.index.values
                if 'Замены' in df.columns.values:
                    curr_ind = indexes[-1] + 1
                    for line in indexes:
                        if line == 0:
                            continue
                        classes = df.iloc[line]['Класс'].split('\n')
                        urok_num = df.iloc[line]['Урок №'].split('\n')
                        urok_po_rasp = df.iloc[line]['Урок по расписанию'].split('\n')
                        zameny = df.iloc[line]['Замены'].split('\n')
                        summ = 0
                        for i in ['6', '7', '8', '9', '10', '11']:
                            for cl in classes:
                                summ += cl.count(i)
                        if summ > 1:
                            urok_num = urok_num * summ
                            zameny = zameny * summ
                            df.at[line, 'Класс'] = classes[0]
                            df.at[line, 'Урок по расписанию'] = urok_po_rasp[0]
                            df.at[line, 'Урок №'] = urok_num[0]
                            df.at[line, 'Замены'] = zameny[0]
                            for i in range(1, summ):
                                df.loc[curr_ind] = [classes[i], urok_num[i], urok_po_rasp[i], zameny[i]]
                                print([classes[i], urok_num[i], urok_po_rasp[i], zameny[i]])
                                curr_ind += 1
                        elif len(urok_num) != 1:
                            classes = classes * len(urok_num)
                            zameny_ = "\n".join(zameny)
                            lesson, teacher_ = zameny_.split('//')
                            lesson = lesson.split('\n')
                            teacher_ = teacher_.split('\n')
                            teacher = []
                            zameny = []
                            for i in range(0, len(teacher_), 2):
                                teacher.append(f"{teacher_[i]}\n{teacher_[i + 1]}")
                            for i in range(len(urok_num)):
                                zameny.append(f"{lesson[i]}//{teacher[i]}")
                            df.at[line, 'Класс'] = classes[0]
                            df.at[line, 'Урок по расписанию'] = urok_po_rasp[0]
                            df.at[line, 'Урок №'] = urok_num[0]
                            df.at[line, 'Замены'] = zameny[0]
                            for i in range(1, len(urok_num)):
                                df.loc[curr_ind] = [classes[i], urok_num[i], urok_po_rasp[i], zameny[i]]
                                curr_ind += 1
                dfs.append(df)
    for i in range(len(dfs)):
        dfs[i] = dfs[i].sort_values(['Урок №'])
        name = 'cabinets'
        if 'Замены' in dfs[i].columns.values:
            name = 'lessons'
        dfs[i].to_csv(path_to_changes + f'{day_}.{month_}.{time_.year}_{name}.csv')


async def get_edits_in_timetable(next_day_tt):
    # filename format: DD.MM.YYYY
    time_ = datetime.now()
    if next_day_tt and time_.weekday() == 5:
        time_ = time_ + timedelta(days=1)
        next_day_tt = '2DAYS'
    day_ = str(time_.day).rjust(2, '0')
    month_ = str(time_.month).rjust(2, '0')
    today_file1 = f'{day_}.{month_}.{time_.year}_lessons.csv'
    today_file2 = f'{day_}.{month_}.{time_.year}_cabinets.csv'
    time_2 = time_ + timedelta(days=1)
    day_ = str(time_2.day).rjust(2, '0')
    month_ = str(time_2.month).rjust(2, '0')
    tomorrow_file1 = f'{day_}.{month_}.{time_2.year}_lessons.csv'
    tomorrow_file2 = f'{day_}.{month_}.{time_2.year}_cabinets.csv'

    if len([i for i in os.walk(path_to_changes)][0][-1]) == 0:
        # Файла с изменениями нет
        return [], ''
    if next_day_tt:
        if not (os.path.exists(path_to_changes + tomorrow_file1) or
                os.path.exists(path_to_changes + tomorrow_file2)):
            # Файла с изменениями нет
            return [], ''
    else:
        if not (os.path.exists(path_to_changes + today_file1) or
                os.path.exists(path_to_changes + today_file2)):
            # Файла с изменениями нет
            return [], ''

    if not next_day_tt:
        day = "*Изменения на сегодня*"
        path_1 = path_to_changes + today_file1
        path_2 = path_to_changes + today_file2
    else:
        if next_day_tt == '2DAYS':
            day = "*Изменения на послезавтра*"
        else:
            day = "*Изменения на завтра*"
        path_1 = path_to_changes + today_file1
        path_2 = path_to_changes + today_file2
    day = prepare_for_markdown('🔔') + day + prepare_for_markdown('🔔\n')
    dfs = []
    if os.path.exists(path_1):
        dfs.append(pd.read_csv(path_1))
    if os.path.exists(path_2):
        dfs.append(pd.read_csv(path_2))
    return dfs, day


res = asyncio.run(get_edits_in_timetable())