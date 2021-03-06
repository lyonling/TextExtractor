import re
import os
import json
import xlwt
import sys

from py.settings import cove_folder, output_folder, truncated_cove_folder, truncated_dd_folder, text_folder
from py.utils import roman_num, num_roman
from py.utils import split_sen, split_para, find_files_with_postfix
from py.extractor import ConvenantTools


class InfoTools:

    def __init__(self):

        # self.time_pat = r'\s(?:month|quarter|annual|end|day)\s'
        # self.month_pat = re.compile(r'(?<=\s)(?:months|monthly|month)(?=\s)', re.IGNORECASE)     # 需要做等值比较的，不能有空格
        self.month_pat = re.compile(r'(?<=[ -])(?:|monthly|month)(?=[ -])', re.IGNORECASE)     # 需要做等值比较的，不能有空格
        self.date_pat = re.compile(r'(?<=[ -])(?:days|year|annual|quarterly|quarter|monthly|month)(?=[ -])', re.IGNORECASE)

        self.number_pat = re.compile(r'(?<=[ -])(?:one|two|three|four|five|six|seven|eight|nine|ten|'
                                     r'eleven|twelve|thir|forty|'
                                     r'first|second|fif|nin)', re.IGNORECASE)

        self.quarter_pat = r'quarter'
        self.annual_pat = r'annual'
        self.time_pat = r'(?:end|day)'
        self.cont_pat = r'\s(?:report|financial statement)\s'

        self.routine_pat = re.compile(r'\s(?:each|every)\s', re.IGNORECASE)
        self.fin_pat = re.compile(r'\s(?:financial_statement|financial_report|consolidated|consolidating|'
                                  r'balance_sheet|cash_flow_statement|statement_of_cash_flow|income_statement|'
                                  r'statement_of_income|unaudited|audited)\s', re.IGNORECASE)
        # self.fin_pat2 = re.compile(r'EBIT|EBDIT|EPS')
        self.debt_pat = re.compile(r'bank|debt|loan|credit|borrow', re.IGNORECASE)

        # projection info
        self.proj_pat = re.compile(r'\s(?:budgeted|budgets|budget|projections|projected|projection|forecasted|'
                                   r'forecast|anticipated|anticipations|anticipation|plans|plan)', re.IGNORECASE)
        # stock, equity, incentive, option, retire,retirement,pension,employee,benefit,employer
        self.plan_fit_pat = re.compile(r'\s(?:stock|equity|equitie|incentive|option|retire|retirement|pension|'
                                   r'employee|employer|benefit)s?\s', re.IGNORECASE)
        # provide, deliver, delivery, report, prepare, submit, send, express, convey,  issue
        self.proj_conf_pat = re.compile(r'\s(?:provid|deliver|delivery|report|prepar|submit|send|sent|express|'
                                        r'convey|issue)(?:e|ed|s|es|ing)?\s', re.IGNORECASE)

    def get_duedate_sens(self, para: str) -> dict:
        """
        return the sentence that contains the due date in this paragraph
        if None, that means it does not has due date info
        """

        possible_sens = []
        due_date_sens = {'month': [], 'quarter': [], 'annual': [], 'others': []}

        # 首先在段落中查找包含 financial 相关的关键词的句子
        sens = split_sen(para)
        for sen in sens:

            fin_keys = []
            fin_keys.extend([fk.strip() for fk in self.fin_pat1.findall(sen)])
            fin_keys.extend([fk.strip() for fk in self.fin_pat2.findall(sen)])
            fin_keys = list(set(fin_keys))
            if fin_keys:
                possible_sens.append((sen, fin_keys))

        del sens, para      # 手动释放内存

        # 在候选句子中选择 monthly 信息的句子
        # month前后五个词之内 each/every
        for psen, fin_keys in possible_sens:

            is_true = False
            shorten_month_sen = []

            month_words = [month_word.strip() for month_word in self.month_pat.findall(psen)]
            psen_words = psen.strip().split()

            m_pointer = 0
            s_pointer = 0
            for p_w in psen_words:
                if m_pointer >= len(month_words):
                    break
                if month_words[m_pointer] != p_w:
                    s_pointer += 1
                    continue
                else:
                    try:
                        start = max(0, s_pointer - 6)
                        end = min(s_pointer + 5, len(psen_words))
                        short_sen = ' '.join(psen_words[start: end])
                        routine_key = self.routine_pat.search(short_sen)
                        if routine_key:
                            routine_key = routine_key.group().strip()
                            shorten_month_sen = psen_words[start: end]

                            rk_index = shorten_month_sen.index(routine_key)

                            psen_words[start+rk_index] = f'****{routine_key}****'
                            psen_words[s_pointer] = f'****{month_words[m_pointer]}****'
                            shorten_month_sen[rk_index] = f'****{routine_key}****'
                            shorten_month_sen[s_pointer-start] = f'****{month_words[m_pointer]}****'

                            is_true = True
                        m_pointer += 1
                        s_pointer += 1
                    except:
                        print('error: 91: ', short_sen)

            if is_true:
                due_date_sens['month'].append((' '.join(psen_words), ' '.join(shorten_month_sen), fin_keys))

        return due_date_sens

    def get_shorten_sen(self, key_word: str, sentence: str) -> str:
        sen_list = sentence.strip().split()
        key_position = 0
        try:
            key_position = sen_list.index(key_word.strip())
        except:
            count = 0
            for word in sen_list:
                if key_word in word:
                    # key_position = sen_list.index(word)
                    key_position = count
                    break
                count += 1
        start = max(0, key_position-6)
        end = min(key_position+5, len(sen_list))
        return ' '.join(sen_list[start:end])

    def get_highlight_sen(self, key_words: list, sentence: str) -> str:
        if type(key_words) is not list:
            key_words = [key_words]
        # remove duplicated keys
        for w in set(key_words):
            sentence = sentence.replace(w, f'****{w}****', 100)
        return sentence

    def write_xls_header(self, headers, xls_book, sheet_name='sheet1'):
        """
        :param xls_book:
        :param headers:
        :return: xls_sheet, row_iter
        """
        # init headers for sheet
        xls_sheet = xls_book.add_sheet(sheet_name)
        for col, head in enumerate(headers):
            xls_sheet.write(0, col, head)
        row_iter = 1

        return xls_sheet, row_iter

    def write_xls_sheet(self, sheet, row, headers, **content: dict):
        """
        :param sheet: target sheet
        :param row: new row to be wrote
        :param content: dict to be write into sheet, which should contain
                        name, is_original, first_lines, shorten_sen, due_date_sen
        :return: sheet object, next row number
        """
        matched_sens = content.pop('matched_sens', None)
        if matched_sens:
            for sen, short_sen, is_new in matched_sens:
                # re-clean
                sen = re.subn(r'[-= ]{5,}', '', sen)[0]

                sheet.write(row, 0, content['name'])
                sheet.write(row, 1, short_sen)
                sheet.write(row, 2, is_new)
                sheet.write(row, 3, sen)
                row += 1
        else:
            # re-clean first lines
            content['first_lines'] = re.subn(r'[-= ]{5,}', '', content.get('first_lines', ''))[0]
            for i in range(len(headers)):
                sheet.write(row, i, content.get(headers[i], None))
            row += 1

        return sheet, row

    def global_search_by_fin_key(self, content, interval) -> list:

        # preprocessing
        content = re.subn(r'balance sheet', 'balance_sheet', content)[0]
        content = re.subn(r'financial statement', 'financial_statement', content)[0]
        content = re.subn(r'financial report', 'financial_report', content)[0]
        content = re.subn(r'cash flow statement', 'cash_flow_statement', content)[0]
        content = re.subn(r'statement of cash flow', 'statement_of_cash_flow', content)[0]
        content = re.subn(r'income statement', 'income_statement', content)[0]
        content = re.subn(r'statement of income', 'statement_of_income', content)[0]

        def search_fin_keys(txt):
            # fin_keys_1 = [fk.strip() for fk in self.fin_pat1.findall(txt)]
            # fin_keys_2 = [fk.strip() for fk in self.fin_pat2.findall(txt)]
            # return fin_keys_1, fin_keys_2
            fin_keys = [fk.strip() for fk in self.fin_pat.findall(txt)]
            return fin_keys

        sens_res = []

        # fin_keys_1, fin_keys_2 = search_fin_keys(content)
        fin_keys = search_fin_keys(content)

        pter_content = 0
        # pter_fk_1 = 0
        # pter_fk_2 = 0
        pter_fk = 0

        content_words = [wd.strip() for wd in content.split()]
        total_length = len(content_words)
        while pter_fk < len(fin_keys) and pter_content < total_length:

            # fk_1 = fin_keys_1[pter_fk_1] if pter_fk_1 < len(fin_keys_1) else ''
            # fk_2 = fin_keys_2[pter_fk_2] if pter_fk_2 < len(fin_keys_2) else ''
            fk = fin_keys[pter_fk]

            # if content_words[pter_content] == fk_1 or content_words[pter_content] == fk_2:
            if content_words[pter_content] == fk:
                start = max(0, pter_content-interval)
                end = min(total_length, pter_content+interval)
                sentence = ' '.join(content_words[start: end])
                tmp_fk = search_fin_keys(sentence)

                # highlight key words
                sentence = self.get_highlight_sen(tmp_fk, sentence)
                sens_res.append(sentence)

                # incease pointer index
                # pter_content += end
                pter_fk += 1
            pter_content += 1

        return sens_res

    def global_search_by_proj_key(self, content, interval) -> list:

        def search_proj_keys(txt):
            proj_keys = [pro_k.strip() for pro_k in self.proj_pat.findall(txt)]
            return proj_keys

        sens_res = []

        proj_keys = search_proj_keys(content)

        pter_content = 0
        pter_pk = 0

        content_words = [wd.strip() for wd in content.split()]
        total_length = len(content_words)
        while pter_pk < len(proj_keys) and pter_content < total_length:

            pk = proj_keys[pter_pk] if pter_pk < len(proj_keys) else ''

            if content_words[pter_content] == pk:
                start = max(0, pter_content-interval)
                end = min(total_length, pter_content+interval)
                sentence = ' '.join(content_words[start: end])
                tmp_pk = search_proj_keys(sentence)

                # highlight key words
                sentence = self.get_highlight_sen(tmp_pk, sentence)
                sens_res.append(sentence)

                # incease pointer index
                pter_pk += 1
            pter_content += 1

        return sens_res

    def global_filter_by_key(self, content_list, pattern) -> list:

        def filter_plan_conf(src_list, word):
            try:
                words = re.findall(word, ' '.join(src_list))
                idx = -1        # will be increased by 1, to make it be 0 at beginning
                for i in words:
                    idx = src_list.index(word, idx+1)
                    start = max(0, idx - 5)
                    end = min(idx + 6, len(content_words))
                    if self.plan_fit_pat.search(' '.join(src_list[start:end])):
                        return True
                return False
            except:
                return False

        full_shorten_res = []

        for content in content_list:

            is_new = 'TRUE'
            matched_keys = getattr(self, pattern).findall(content)
            if not matched_keys:
                continue

            content_words = content.split()
            total_length = len(content_words)
            s_pointer = 0
            m_pointer = 0

            if pattern == 'month_pat':
                while m_pointer < len(matched_keys) and s_pointer < total_length:
                    if content_words[s_pointer] == matched_keys[m_pointer]:
                        start = max(0, s_pointer - 10)
                        end = min(s_pointer + 10, total_length)
                        # check if there number word in former 5 words,
                        # if yes, pass this sentence
                        tmp_former = ' '.join(content_words[max(0, s_pointer-3):s_pointer])
                        if self.number_pat.search(tmp_former):
                            break
                        if re.search(r'\d{1,}', tmp_former):
                            break

                        shorten_month_sen = content_words[start: end]
                        content_words[s_pointer] = f'****{content_words[s_pointer]}****'
                        shorten_month_sen[s_pointer - start] = f'****{matched_keys[m_pointer]}****'
                        full_shorten_res.append((' '.join(content_words), ' '.join(shorten_month_sen), is_new))
                        is_new = ' '

                        m_pointer += 1
                    s_pointer += 1

            elif pattern == 'date_pat':

                proj_conf_keys = self.proj_conf_pat.findall(content)
                if not proj_conf_keys:
                    break
                if filter_plan_conf(content_words, 'plan'):
                    break
                if filter_plan_conf(content_words, 'plans'):
                    break

                for pck in set(proj_conf_keys):
                    pck = pck.strip()
                    content = content.replace(pck, f' ****{pck}**** ')
                content_words = content.split()

                while m_pointer < len(matched_keys) and s_pointer < total_length:
                    if content_words[s_pointer] == matched_keys[m_pointer]:
                        start = max(0, s_pointer - 10)
                        end = min(s_pointer + 10, total_length)

                        shorten_month_sen = content_words[start: end]
                        content_words[s_pointer] = f'****{content_words[s_pointer]}****'
                        shorten_month_sen[s_pointer - start] = f'****{matched_keys[m_pointer]}****'
                        full_shorten_res.append((' '.join(content_words), ' '.join(shorten_month_sen), is_new))
                        is_new = ' '

                        m_pointer += 1
                    s_pointer += 1
        return full_shorten_res
