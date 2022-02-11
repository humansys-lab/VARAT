import pandas as pd
import re
import pathlib
import os
import sys

DATA_FOLDER = pathlib.Path(os.getcwd()) / 'data/Anno'


def replace_math_mask_to_tex(definition: str, df):
    for math_elem in re.findall('MATH_[0-9]{4}', definition):
        definition = definition.replace(
            math_elem, df['identifier_tex'][math_elem])

    return definition


def generate_df_with_ID_Def(process: str, paper: str, data_folder=DATA_FOLDER):
    xlsx_path = data_folder / process / paper / (paper + '.xlsx')
    df = pd.read_excel(xlsx_path, index_col=0, dtype='str')

    # use definition_extracted
    id_list = []
    def_identifier_list = []
    for i, extractable_str_ in enumerate(df['extractable']):
        if extractable_str_ == '0':
            continue
        extractable_list_ = extractable_str_.split('\n')
        def_extracted_list_ = df['definition_extracted'][i].split('\n')

        for ii, (def_extracted_, extractable_) in enumerate(
                zip(def_extracted_list_, extractable_list_)):
            if extractable_ == '1':
                id_list.append(f'{process}/{paper}/{df.index[i]}_{ii}')

                for math_elem in re.findall('MATH_[0-9]{4}', def_extracted_):
                    def_extracted_ = def_extracted_.replace(
                        math_elem, df['identifier_tex'][math_elem])
                def_identifier_list.append(
                    [df['identifier_tex'][i], def_extracted_])

    # # use definition_true
    # id_list = []
    # def_identifier_list = []
    # for i, (def_str_, identifier_str_) in enumerate(
    #         zip(df['definition_true'], df['identifier_tex'])):

    #     if not isinstance(def_str_, str):
    #         continue
    #     def_list_ = def_str_.split('\n')

    #     id_list_ = [
    #         f'{process}/{paper}/{i}_{ii}' for ii,
    #         _ in enumerate(def_list_)]
    #     id_list.extend(id_list_)
    #     def_identifier_list_ = [
    #         [identifier_str_, replace_math_mask_to_tex(def_, df)] for def_ in def_list_]
    #     def_identifier_list.extend(def_identifier_list_)

    return pd.DataFrame(
        def_identifier_list,
        index=id_list,
        columns=[
            'identifier_tex',
            'Definition'])


def main():
    args = sys.argv
    process = args[1]  # e.g. crystallization
    process_path = DATA_FOLDER / process

    df_dict = pd.DataFrame(columns=['identifier_tex', 'Definition'])

    paper_list = [
        f for f in os.listdir(process_path) if os.path.isdir(
            process_path /
            f)]
    for paper_ in paper_list:
        df_dict = pd.concat(
            [df_dict, generate_df_with_ID_Def(process, paper_)],
            axis=0)
    df_dict['ID'] = [f'{i:04}' for i in range(df_dict.shape[0])]
    df_dict.to_excel(
        DATA_FOLDER /
        process /
        'Dict_0.xlsx',
        columns=[
            'ID',
            'identifier_tex',
            'Definition'])


if __name__ == '__main__':
    main()
