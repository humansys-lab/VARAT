import itertools
import os
import pathlib
import re
import sys
import warnings

import pandas as pd

DATA_FOLDER = pathlib.Path(os.getcwd()) / "data/Anno"


def generate_df_with_ID_Def(process: str, paper: str, data_folder=DATA_FOLDER):
    xlsx_path = data_folder / process / paper / (paper + ".xlsx")
    df = pd.read_excel(xlsx_path, index_col=0, dtype="str")

    id_list = []
    definition_list = []
    for i, extractable_str_ in enumerate(df["extractable"]):
        if extractable_str_ == "0":
            continue
        extractable_list_ = extractable_str_.split("\n")
        def_extracted_list_ = df["definition_extracted"][i].split("\n")

        for ii, (def_extracted_, extractable_) in enumerate(
            zip(def_extracted_list_, extractable_list_)
        ):
            if extractable_ == "1":
                id_list.append(f"{process}/{paper}/{df.index[i]}_{ii}")

                for math_elem in re.findall("MATH_[0-9]{4}", def_extracted_):
                    def_extracted_ = def_extracted_.replace(
                        math_elem, df["identifier_tex"][math_elem]
                    )

                definition_list.append(def_extracted_)

    return pd.DataFrame(definition_list, index=id_list, columns=["Definition"])


def load_dict(process: str, data_folder=DATA_FOLDER):
    xlsx_path = data_folder / process / "Dict.xlsx"
    df = pd.read_excel(xlsx_path, dtype=str)
    return df


def judge_equivalence_by_dict(df_dict, def_0, def_1):
    dict_index_ID_0 = df_dict["ID"][((df_dict == def_0).sum(axis=1) == 1)].values
    dict_index_ID_1 = df_dict["ID"][((df_dict == def_1).sum(axis=1) == 1)].values
    if dict_index_ID_0.size > 0 and dict_index_ID_1.size > 0:
        if len(dict_index_ID_0) > 1 or len(dict_index_ID_0) > 1:
            warnings.warn(
                f"len(dict_index_ID_0) is {len(dict_index_ID_0)} and\
                     len(dict_index_ID_1) is {len(dict_index_ID_1)}. \
                        Each length should be 0 or 1.\n \
                        def_0: {def_0}\t def_1: {def_1}"
            )
        is_equivalent = "".join(dict_index_ID_0) == "".join(dict_index_ID_1)
    else:
        is_equivalent = False
    return is_equivalent


def main():
    args = sys.argv
    process = args[1]  # e.g. crystallization

    process_path = DATA_FOLDER / process

    df_dict = load_dict(process)

    paper_list = [
        f for f in os.listdir(process_path) if os.path.isdir(process_path / f)
    ]
    paper_combinations = itertools.combinations(paper_list, 2)

    label_ID_Def_list = []
    for i, (paper_0, paper_1) in enumerate(paper_combinations):
        print(i, paper_0, paper_1)

        df_0_ID_Def = generate_df_with_ID_Def(process, paper_0)
        df_1_ID_Def = generate_df_with_ID_Def(process, paper_1)

        product_set_ID_Def = itertools.product(df_0_ID_Def.index, df_1_ID_Def.index)
        for ID_pair in product_set_ID_Def:
            ID_0, ID_1 = ID_pair

            def_0 = df_0_ID_Def["Definition"][ID_0]
            def_1 = df_1_ID_Def["Definition"][ID_1]
            is_equivalent = int(judge_equivalence_by_dict(df_dict, def_0, def_1))

            def remove_article(def_word: str, target: str = None):
                article_list = ["the", "The", "a", "an", "A", "An"]
                def_word_list = def_word.split(" ")
                if def_word_list[0] in article_list:
                    def_word = " ".join(def_word_list[1:])
                if target == "all":
                    def_word = [x for x in def_word_list if x not in article_list]
                return def_word

            def_0 = remove_article(def_0)
            def_1 = remove_article(def_1)

            def_0_no_article = remove_article(def_0, "all")
            def_1_no_article = remove_article(def_1, "all")
            if def_0_no_article == def_1_no_article:
                continue

            label_ID_Def_list.append(
                (
                    is_equivalent,
                    ID_0,
                    ID_1,
                    def_0,
                    def_1,
                )
            )
    df_var_pair = pd.DataFrame(
        label_ID_Def_list, columns=["label", "ID0", "ID1", "Definition0", "Definition1"]
    )

    df_var_pair.to_excel(DATA_FOLDER / process / "variable_pair.xlsx", index=0)
    df_var_pair.to_csv(DATA_FOLDER / process / "variable_pair.tsv", sep="\t", index=0)


if __name__ == "__main__":
    main()
