import re
import sys
import warnings

import lxml.html
import stanza

from lib.xmldoc_child import Identifier


def e2htmltext(e: lxml.html.HtmlElement) -> str:
    return lxml.html.tostring(e, encoding="unicode", with_tail=False)


def is_identifier(e_mltag: lxml.html.HtmlElement) -> bool:
    """return whether input string represents a variable.

    Args:
        e_mltag (HtmlElement):

    Returns:
        bool: Is e_mltag represents a variable?
    """
    math_txt = e_mltag.text_content()
    # for only sub/super script. e.g. $^*$
    if math_txt == "":
        return False

    not_number = math_txt[0] not in [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]

    def is_variable_for_mi(e):
        len_1 = len(e.text_content()) == 1
        not_roman = e.attrib.get("mathvariant") != "normal"
        is_greek = bool(re.match("[\\u0391-\\u03a9]", e.text_content()))

        return len_1 and (not_roman or is_greek)

    if e_mltag.tag == "mi":
        not_roman = is_variable_for_mi(e_mltag)
    elif e_mltag[0].tag == "mi":
        not_roman = is_variable_for_mi(e_mltag[0])
    # TODO: <dirty> msub mover への対象方法 e.g. \dot{C}_{\mathrm{A}}
    elif (
        e_mltag.tag == "msub"
        and e_mltag[0].tag == "mover"
        and e_mltag[0][0].tag == "mi"
    ):
        not_roman = is_variable_for_mi(e_mltag[0][0])
    else:
        return False

    function_list = ["exp", "log", "ln", "sin", "cos", "tan", "sinh", "cosh", "tanh"]
    not_function = math_txt not in function_list
    return not_number and not_roman and not_function


def var_html_to_str(e_mltag: lxml.html.HtmlElement):
    mi_list = []
    if e_mltag.tag in ["mi", "mo", "mn"]:
        math_txt = e_mltag.text_content()
        mi_list = [math_txt]
    else:
        mi_list = [var_html_to_str(x)[0] for x in e_mltag]

        if e_mltag.tag == "mrow":
            math_txt = "".join(mi_list)
        elif e_mltag.tag == "msubsup":
            math_txt = mi_list[0] + "_" + mi_list[1] + "^" + mi_list[2]
        elif e_mltag.tag == "msub":
            math_txt = mi_list[0] + "_" + mi_list[1]
        elif e_mltag.tag == "msup":
            math_txt = mi_list[0] + "^" + mi_list[1]
        elif e_mltag.tag == "munderover":
            math_txt = (
                r"\overset{"
                + mi_list[2]
                + "}{"
                + r"\underset{"
                + mi_list[1]
                + "}{"
                + mi_list[0]
                + "}}"
            )
        elif e_mltag.tag == "mover":
            math_txt = r"\overset{" + mi_list[1] + "}{" + mi_list[0] + "}"
        elif e_mltag.tag == "munder":
            math_txt = r"\underset{" + mi_list[1] + "}{" + mi_list[0] + "}"
        else:
            math_txt = ""
            warnings.warn(f"unexpected tag: {e_mltag}")

    return math_txt, mi_list


def extract_ml_component(e_math, mltag, identifier_list, replaced_string_list):

    for e_mltag_ in e_math.cssselect(mltag):
        math_txt, mi_list_ = var_html_to_str(e_mltag_)
        # print('##########################')
        # print(math_txt)
        # print(mi_list_)
        mi_list = []
        # TODO: moverunderに対応する．
        for mi_ in mi_list_:
            mi_component = re.findall("(over|under)set{(.+)}{(.+)}", mi_)
            if mi_component:
                mi_list.extend([mi_component[0][1], mi_component[0][2]])
            else:
                mi_list.append(mi_)

        if is_identifier(e_mltag_):
            identifier = Identifier(
                text_tex=math_txt, text_html=e2htmltext(e_mltag_), mi_list=mi_list
            )
            if identifier not in identifier_list:
                identifier_list.append(identifier)
            # mi_list_の要素に<mrow>...</mrow>の式が含まれるとき，
            # その式に登場する変数を抽出できないので，変数以外の木構造は削除しないことで
            # 抽出可能にする（良い処理か不明）
            e_mltag_.drop_tree()
        # else:
        #     replaced_string_list.append(
        #         (math_txt, e2htmltext(e_mltag_), math_txt))

        # e_mltag_.drop_tree()

    return identifier_list, replaced_string_list


def sentence_segmentation(text):
    """extract sentences which contain the identifier from the text.
    sentences are segmented using stanza.

    Returns:
        sentences (list): sentences which contain the identifier the text.
    """
    nlp = stanza.Pipeline(lang="en", processors="tokenize")
    doc = nlp(text)
    # Each sentence should not include a line change.
    sentence_list = [sentence.text.replace("\n", " ") for sentence in doc.sentences]

    return sentence_list


def extract_symbols(e_math_list, identifier_list, replaced_string_list, symbol_type):

    if symbol_type == "serial":
        for e_math_ in e_math_list:
            # moタグ中のテキストが`&InvisibleTimes;`(`&#8290` or `&#x2062` or `,`)である場合
            # 一連の記号を1つの変数を表す記号とみなす．
            # e.g. MW_{c,p}という場合があるのでカンマを入れている
            # 変数記号リストに変数を追加し，抽出対象のHTMLファイルを更新する．
            e_mo_text_set = {e_mo_.text for e_mo_ in e_math_.cssselect("mo")}
            if not (
                e_mo_text_set <= {"\u2062", "&#8290", ","} and e_mo_text_set != set()
            ):
                continue

            if e_math_[0].tag == "mrow":
                e_math_text_html = re.findall(
                    r"<math.*?><mrow>(.*?)</mrow></math>", e2htmltext(e_math_)
                )[0]
                e_first_element = e_math_[0][0]
            else:
                e_math_text_html = re.findall(
                    r"<math.*?>(.*?)</math>", e2htmltext(e_math_)
                )[0]
                e_first_element = e_math_[0]

            # {3,4}のような記号や{}^{1}のような表記は削除する
            if e_first_element.tag == "mn" or e_first_element.text_content() == "":
                continue

            e_math_text_tex = e_math_.attrib.get("alttext")
            e_math_text_tex = e_math_text_tex.replace("\\displaystyle", "")
            identifier = Identifier(
                text_tex=e_math_text_tex, text_html=e_math_text_html
            )
            if identifier not in identifier_list:
                identifier_list.append(identifier)
            e_math_.drop_tree()


    elif symbol_type == "single":
        ml_tag_list = [
            "munderover",  # used for summation
            "msubsup",
            "msup",
            "msub",
            "munder",
            "mover",
            "mi",
        ]

        for ml_tag_ in ml_tag_list:
            for e_math_ in e_math_list:
                identifier_list, replaced_string_list = extract_ml_component(
                    e_math_, ml_tag_, identifier_list, replaced_string_list
                )
    else:
        warnings('Choose appropriate symbol type: "serial" or "single".')
        sys.exit(1)

    for i, identifier_ in enumerate(identifier_list):
        if identifier_.id == -1:
            replaced_string_list.append(
                (identifier_.text_tex, identifier_.text_html, f"MATH_{i:04d}")
            )
            identifier_list[i].id = i

    return identifier_list, replaced_string_list
