import os
import pathlib
import re
import subprocess

import lxml.html
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from lib.util import e2htmltext, extract_symbols, sentence_segmentation


def main():

    st.set_page_config(page_title="Annotation tool", page_icon="random", layout="wide")
    """
    ### VARAT: Variable Annotation Tool for Engineering-domain Documents
    """

    ##############
    DATA_FOLDER = pathlib.Path(os.getcwd()) / "data/Anno"

    process_list = [
        f for f in os.listdir(DATA_FOLDER) if os.path.isdir(DATA_FOLDER / f)
    ]

    process_select_expander = st.expander("Select process and document.", expanded=True)

    with process_select_expander:
        process_path = DATA_FOLDER / st.selectbox(
            "Which process is used?", process_list
        )

    paper_list = [
        f for f in os.listdir(process_path) if os.path.isdir(process_path / f)
    ]

    def initialize_session_state():
        st.session_state.sentence_extracted_list = []
        st.session_state.def_extracted = ""
        st.session_state.def_true = ""
        if "symbol_number" in st.session_state:
            del st.session_state["symbol_number"]

    with process_select_expander:
        doc_folder_path = st.selectbox(
            "Which document is used?", paper_list, on_change=initialize_session_state
        )

    doc_tex_path = process_path / doc_folder_path / (doc_folder_path + ".tex")
    doc_html_path = process_path / doc_folder_path / (doc_folder_path + ".html")

    if not os.path.isfile(doc_html_path):
        if not os.path.isfile(doc_tex_path):
            st.warning("Prepare tex file.")
            st.stop()
        st.write("html file does not exist. Convert tex to html.")
        subprocess_var = subprocess.run(
            [
                "latexmlc",
                str(doc_tex_path),
                "--preload=amsmath.sty",
                "--dest=" + str(doc_html_path),
            ],
            check=True,
        )
        st.write("Finish conversion.")

    doc_processed_path = (
        process_path / doc_folder_path / (doc_folder_path + "_preprocessed.html")
    )

    if not os.path.isfile(doc_processed_path):
        st.write("preprocessed html file does not exist. Convert tex to html.")
        subprocess.run(["python", "-m", "tools.preprocess", doc_html_path], check=True)
        st.write("Finish preprocessing.")

    tree = lxml.html.parse(str(doc_processed_path))
    root = tree.getroot()
    doc_article = root.cssselect("article")[0]
    doc_article_original = e2htmltext(doc_article)
    doc_article = e2htmltext(doc_article)

    symbol_list = []
    replaced_string_list = []
    # formula_list = []

    for symbol_type in ["serial", "single"]:
        doc_article_html = lxml.html.fromstring(doc_article)
        math_component_list = doc_article_html.cssselect("math")
        symbol_list, replaced_string_list = extract_symbols(
            math_component_list, symbol_list, replaced_string_list, symbol_type
        )
        for replaced_string_ in replaced_string_list:
            doc_article = doc_article.replace(replaced_string_[1], replaced_string_[2])

    doc_article = lxml.html.fromstring(doc_article)
    doc_text = doc_article.text_content()
    doc_text = re.sub(r"\n+", r"\n", doc_text)

    @st.cache
    def return_sentence_list(sentences):
        return sentence_segmentation(sentences)

    sentence_list = return_sentence_list(doc_text)

    ##########################################################################
    # save doc
    ##########################################################################
    doc_text_path = process_path / doc_folder_path / (doc_folder_path + "_article.txt")
    if not os.path.isfile(doc_text_path):
        with open(doc_text_path, "w") as f:
            f.write(doc_text)

    doc_article_sentence_path = (
        process_path / doc_folder_path / (doc_folder_path + "_article_sentence.txt")
    )
    if not os.path.isfile(doc_article_sentence_path):
        with open(doc_article_sentence_path, "w") as f:
            for i, s_ in enumerate(sentence_list):
                f.write(f"{i}\t{s_}\n")

    doc_article_masked_path = (
        process_path / doc_folder_path / (doc_folder_path + "_article_masked.html")
    )
    if not os.path.isfile(doc_article_masked_path):
        with open(doc_article_masked_path, "w") as f:
            f.write(e2htmltext(doc_article))
    ##########################################################################

    xlsx_path = process_path / doc_folder_path / (doc_folder_path + ".xlsx")

    col_left, col_right = st.columns([1, 1])
    # HTML_WIDTH = 700
    HTML_HEIGHT = 500
    with col_left:
        with st.expander("Processed text", expanded=True):
            components.html(
                e2htmltext(doc_article), height=HTML_HEIGHT * 1.5, scrolling=True
            )
        with st.expander("Original text", expanded=False):
            components.html(doc_article_original, height=HTML_HEIGHT, scrolling=True)

    # TODO: これより上の処理でxlsxのinitializeをして，ここはloadだけにする
    # （引数がxlsx_pathだけになるように設計し直す方がすっきりする）
    # xlsxがあったら前処理不要

    def load_xlsx(xlsx_path, symbol_list):

        if os.path.isfile(xlsx_path):
            df = pd.read_excel(xlsx_path, index_col=0, dtype=str)
        else:
            df_columns = [
                "identifier_html",
                "identifier_tex",
                "definition_extracted",
                "definition_true",
                "extractable",
                "sentence_number",
                "sentence_with_definition",
            ]
            df_index = [f"MATH_{i:04d}" for i, _ in enumerate(symbol_list)]
            df = pd.DataFrame(columns=df_columns, index=df_index)
            for i, index_ in enumerate(df_index):
                df.loc[index_]["identifier_html"] = symbol_list[i].text_html
                df.loc[index_]["identifier_tex"] = symbol_list[i].text_tex
        return df

    df = load_xlsx(xlsx_path, symbol_list)
    with col_right:

        def update_form(df, sentence_list):
            symbol_MATH = f"MATH_{st.session_state.symbol_number:04d}"
            # TODO:１文に対して変数の意味は１つしかないと仮定しているが，この仮定が成り立たない可能性はある
            if pd.isna(df.loc[symbol_MATH]["sentence_number"]):
                s_list_ = []
            else:
                s_list_ = df.loc[symbol_MATH]["sentence_number"].split("\n")
            st.session_state.sentence_extracted_list = [
                sentence_list[int(i)] for i in s_list_
            ]

            def_ex_ = df.loc[symbol_MATH]["definition_extracted"]
            if pd.isna(def_ex_):
                def_ex_ = ""
            st.session_state.def_extracted = def_ex_

            def_true_ = df.loc[symbol_MATH]["definition_true"]
            if pd.isna(def_true_):
                def_true_ = ""
            st.session_state.def_true = def_true_

        if "symbol_number" not in st.session_state:
            st.session_state.symbol_number = 0
            update_form(df, sentence_list)

        symbol_number = st.selectbox(
            "Choose variable No. ",
            [i for i, _ in enumerate(symbol_list)],
            key="symbol_number",
            on_change=update_form,
            args=(
                df,
                sentence_list,
            ),
        )
        symbol_selected = symbol_list[symbol_number]
        symbol_MATH = f"MATH_{symbol_number:04d}"
        st.write(
            f"HTML format: {symbol_selected.text_html}  \n TeX format: {symbol_selected.text_tex}"
        )

        sentence_extracted_list = st.multiselect(
            "Select the sentence including the variable definition.",
            sentence_list,
            key="sentence_extracted_list",
        )
        st.write(sentence_extracted_list)

        def_extracted = st.text_area(
            "Input the variable definition in the sentence.", key="def_extracted"
        )
        def_extracted = def_extracted.strip()

        st.write(def_extracted.split("\n"))

        def_true = st.text_area(
            "Input the correct variable definition.", key="def_true"
        )
        def_true = def_true.strip()
        st.write(def_true.split("\n"))

        save_button = st.button("Save")
        if save_button:
            extractable_list = ["0"]
            if sentence_extracted_list:
                if def_extracted == "":
                    st.warning("Extract variable from the selected sentence.")
                    st.stop()
                else:
                    # 抽出した文と変数が1対1対応しているか
                    def_extracted_list = def_extracted.split("\n")
                    not_one_to_one_flag = not all(
                        [
                            d_ in s_
                            for d_, s_ in zip(
                                def_extracted_list, sentence_extracted_list
                            )
                        ]
                    )
                    diff_len_flag = len(def_extracted_list) != len(
                        sentence_extracted_list
                    )
                    if not_one_to_one_flag or diff_len_flag:
                        st.warning(
                            "The number of the variables should be the same as the number of the sentences."
                        )
                        st.stop()
                    extractable_list = [
                        str(int(def_e in def_true.split("\n")))
                        for def_e in def_extracted_list
                    ]
                if def_true == "":
                    st.warning("Input correct variable definition.")
                    st.stop()
            else:
                if def_extracted != "":
                    st.warning(
                        "Select the sentence including the extractable definition."
                    )
                    st.stop()

            df.loc[symbol_MATH]["sentence_number"] = "\n".join(
                [str(sentence_list.index(s)) for s in sentence_extracted_list]
            )
            df.loc[symbol_MATH]["sentence_with_definition"] = "\n".join(
                sentence_extracted_list
            )
            df.loc[symbol_MATH]["definition_extracted"] = def_extracted
            df.loc[symbol_MATH]["definition_true"] = def_true
            df.loc[symbol_MATH]["extractable"] = "\n".join(extractable_list)
            df.to_excel(xlsx_path)
            st.write("Successfully saved table.")
            n_annotated = pd.notna(df["definition_true"]).sum()

        table_expander = st.expander("Table", expanded=False)
        with table_expander:
            st.dataframe(df)
        n_annotated = pd.notna(df["extractable"]).sum()
        msg_progress = f"Progress: {n_annotated:d} / {df.shape[0]:d}"
        st.write(msg_progress)
        progress_rate = n_annotated / df.shape[0]
        st.progress(progress_rate)
        if progress_rate == 1:
            st.balloons()


if __name__ == "__main__":
    main()
