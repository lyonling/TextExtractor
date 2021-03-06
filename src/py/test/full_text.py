# 2019-05-28
# Full Text Search on monthly sentences and projection sentences

import os, re, xlwt
from py.extractor import InfoTools, ConvenantTools


if __name__ == '__main__':

    """
    Monthly & Projection extraction core steps：
    1. According to keywords to do full text search, cut before and after keywords 150 words as sentences  
        1.1. "financial statement, financial report, consolidated, consolidating, balance sheet, cash flow statement,  
        statement of cash flow, income statement, statement of income, audited, unaudited" for Monthly
        1.2. "budgeted budgets budget projections projected projection forecasted forecast anticipated anticipations
        anticipation plans plan" for Projections
    For Projections
    2.1 For each sentence, find the position of "month，monthly", if there are any numbers or words representing number 
    among before and after the position 3 words, this sentence would be filtered.  
    2.2 For each sentence, 5 wordsb Before and after "plan, plans", there should NOT have any "stock, equity, incentive, 
    option, retire, retirement, pension, employee"
    2.3 For each sentence, there should have "provide, deliver, delivery, report, prepare, submit, send, express, 
    communicate, convey, direct, guide, assign, issue, grant"
    
    What's more
    3. USE a variable to record whether the first ten valid lines of each file contain words like "bank*, debt*, 
    loan*, credit*,borrow*" or not
    4. USE a variable to record whether the file is original or not, by keys "AMENDED, AMENDMENT, RESTATED, revis,
    amend, modif, restate, supplement, addendum"
    5. Use three xlsx file to contain results, one for file name/is amended/is debt...，one for monthly，one for 
    projection
    """

    info_tools = InfoTools()
    covenant_processor = ConvenantTools()
    fail_list = []

    text_folder = './text/txt_result/'

    suc_counter = 0
    err_counter = 0
    date_dict = {}

    year_file_dic = {}
    years = [1996, 2018]
    for year in range(*years):
        year_folder = os.path.join(text_folder, str(year))
        year_file_dic[year] = [file for file in os.listdir(year_folder) if file.endswith('.txt')]

    types = ['basic', 'duedate', 'proj']
    headers = {}
    headers['basic'] = ['name', 'is_original', 'is_debt', 'first_lines']
    headers['duedate'] = ['name', 'shorten_sen', 'is_new', 'due_date_sen']
    headers['proj'] = ['name', 'shorten_sen', 'is_new', 'projection_sen']
    books = {}
    sheets = {}
    row_counter = {}

    for year, file_names in tuple(year_file_dic.items())[:1]:

        # 初始化excel workbook，否则信息会累加到后面的文件中
        for t in types:
            books[t] = xlwt.Workbook()
            sheets[t], row_counter[t] = info_tools.write_xls_header(headers[t], books[t])

        date_dict[year] = {'duedate': 0, 'proj': 0}

        year_folder = os.path.join(text_folder, str(year))

        for name in file_names:

            is_debt = False
            # check first line to get origin and debt info about this contract
            with open(os.path.join(year_folder, name), 'r', encoding='utf-8') as f:
                lines = [line for line in f.readlines() if line.strip()]
                first_lines = covenant_processor.get_n_lines(5, lines)
                is_origin = True if covenant_processor.is_original(first_lines) else False
                is_debt = True if re.search(info_tools.debt_pat, covenant_processor.get_n_lines(10, lines)) else False
                content = '\n'.join(lines)
            del lines

            # cleaning
            content = re.subn(r'\-[0-9]{1,2}\-', '', content)[0]
            content = re.subn(r'[-=_ ]{5,}', '', content)[0]

            fin_sens = info_tools.global_search_by_fin_key(content, 150)
            proj_sens = info_tools.global_search_by_proj_key(content, 150)

            fin_full_shorten_sens = info_tools.global_filter_by_key(fin_sens, pattern='month_pat')
            proj_full_shorten_sens = info_tools.global_filter_by_key(proj_sens, pattern='date_pat')

            # write info into xls by each file iteration

            sheets['basic'], row_counter['basic'] = info_tools.write_xls_sheet(sheet=sheets['basic'],
                                                                              row=row_counter['basic'],
                                                                              headers=headers['basic'],
                                                                              name=name,
                                                                              is_original=is_origin,
                                                                              is_debt=is_debt,
                                                                              first_lines=first_lines)
            if fin_full_shorten_sens:
                date_dict[year]['duedate'] += 1
                sheets['duedate'], row_counter['duedate'] = info_tools.write_xls_sheet(sheet=sheets['duedate'],
                                                                                      row=row_counter['duedate'],
                                                                                      headers=headers['duedate'],
                                                                                      name=name,
                                                                                      matched_sens=fin_full_shorten_sens)
            if proj_full_shorten_sens:
                date_dict[year]['proj'] += 1
                sheets['proj'], row_counter['proj'] = info_tools.write_xls_sheet(sheet=sheets['proj'],
                                                                                row=row_counter['proj'],
                                                                                headers=headers['proj'],
                                                                                name=name,
                                                                                matched_sens=proj_full_shorten_sens)

        for t in types:
            books[t].save(os.path.join('./output/fulltext', f'{t}_{year}.xls'))
            del books[t]

        print(f'{year}: ')
        print('monthly\t', date_dict[year]['duedate'], ' / ', len(year_file_dic[year]))
        print('project\t', date_dict[year]['proj'], ' / ', len(year_file_dic[year]))

    print('finished!')