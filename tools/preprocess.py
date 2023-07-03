import re
import sys
import warnings

import lxml.html

from lib.util import e2htmltext


def is_power(e):
    # 上付き文字の部分が以下の条件のいずれかの場合 （情報を表す場合）以外，累乗とみなす
    # 1. タグがmiで(miの中身が1文字で立体 or mi の中身が2文字以上）ではない
    # 2. moではない
    if e.tag == "mi":
        if len(e.text_content()) == 1:
            is_power = e.attrib.get("mathvariant") != "normal"
        else:
            is_power = False
    elif e.tag == "mo":
        is_power = False
    else:
        is_power = True
    return is_power


def replace_power(e_child, doc):
    if e_child.tag == "mmultiscripts":
        # this is for "Faes_et_al_2019"
        if is_power(e_child[-1]):
            text_before_replaced = e2htmltext(e_child)

            e_child_child_list = [e2htmltext(e_) for e_ in e_child]
            if e_child[1].tag == "none":
                text_after_replaced = (
                    r"<msup>"
                    + e_child_child_list[0]
                    + e_child_child_list[2]
                    + r"</msup>^"
                    + e_child_child_list[-1]
                )
            elif e_child[2].tag == "none":
                text_after_replaced = (
                    r"<msub>"
                    + e_child_child_list[0]
                    + e_child_child_list[1]
                    + r"</msub>^"
                    + e_child_child_list[-1]
                )
            else:
                text_after_replaced = (
                    r"<msubsup>"
                    + "".join(e_child_child_list[0:3])
                    + r"</msubsup>^"
                    + e_child_child_list[-1]
                )
            doc = doc.replace(text_before_replaced, text_after_replaced)

    if e_child.tag == "msubsup":
        if is_power(e_child[2]):
            text_before_replaced = e2htmltext(e_child)
            text_after_replaced = (
                r"<msub>"
                + e2htmltext(e_child[0])
                + e2htmltext(e_child[1])
                + r"</msub>^"
                + e2htmltext(e_child[2])
            )
            doc = doc.replace(text_before_replaced, text_after_replaced)

    if e_child.tag == "msup":
        if is_power(e_child[1]):
            text_before_replaced = e2htmltext(e_child)
            text_after_replaced = e2htmltext(e_child[0]) + r"^" + e2htmltext(e_child[1])
            doc = doc.replace(text_before_replaced, text_after_replaced)

    for e_child_ in e_child.getchildren():
        doc = replace_power(e_child_, doc)

    return doc


def main():
    args = sys.argv
    filepath = args[1]
    if filepath[-5:] != ".html":
        warnings.warn("input should be html format.")
        return -1

    print(f"preprocess {filepath}")

    # preprocess
    with open(filepath, "r") as f:
        doc = f.read()

    tree = lxml.html.parse(str(filepath))
    root = tree.getroot()

    for e_math_ in root.cssselect("math"):

        for e_child_ in e_math_.getchildren():
            doc = replace_power(e_child_, doc)

    # mathsize="142%"の記述を削除する
    # e.g.
    # <munderover accent="true" accentunder="true"><mo>⇆</mo><msub><mi
    # mathsize="142%">k</mi><mn
    # mathsize="140%">2</mn></msub><msub><mi>k</mi><mn>1</mn></msub></munderover>
    doc = re.sub(r'[\s]mathsize="[0-9]+%"', "", doc)
    saved_filepath = filepath.rstrip(".html") + "_preprocessed.html"
    with open(saved_filepath, "w") as f:
        f.write(doc)
        print(f"save {saved_filepath}")


if __name__ == "__main__":
    main()
