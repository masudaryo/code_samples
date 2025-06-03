# 以下のパッケージが必要(Pygmentsがないとcodehilite extensionは機能しない(cssだけではダメ))
# pip install markdown Pygments
from itertools import chain, zip_longest
import markdown
import re
import os
from os import PathLike
import os.path
from abc import ABC, abstractmethod
import argparse
from pathlib import Path
from collections.abc import Generator


def get_command_line_args() -> argparse.Namespace:
    # このmy_markdown_paresr.pyが存在するディレクトリにあるheader_str.html, footer_str.htmlを使って、input_filepathをhtmlに変換してoutput_filepathに保存する。
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_filepath", required=True)
    parser.add_argument(
        "-o",
        "--output_filepath",
        help=r"指定しない場合、my_markdown_parser.pyがあるディレクトリ上のmarkdown_preview.html に出力される。",
    )
    parser.add_argument("-t", "--page_title", help="指定しない場合、出力ファイル名がページタイトルになる")
    return parser.parse_args()


class MathEquationExtractor:
    def __init__(self, markdown_str: str) -> None:
        self.markdown_str: str = markdown_str
        self.markdown_str_len: int = len(self.markdown_str)
        self.other_strings: list[str] = []
        self.math_equations: list[str] = []
        self.equation_start_index: int | None = None
        self.equation_end_index: int = 0
        self.markdown_str_enumerator: enumerate[str] = enumerate(self.markdown_str)
        self.states: States = States(self)
        self.state: State = self.states.usual

    def extract(self) -> tuple[list[str], list[str]]:
        for i, char in self.markdown_str_enumerator:
            self.state.consume(i, char)
        self.other_strings.append(self.markdown_str[self.equation_end_index :])
        return self.math_equations, self.other_strings

    def set_equation_start(self, i: int) -> None:
        self.equation_start_index = i
        self.other_strings.append(self.markdown_str[self.equation_end_index : self.equation_start_index])

    def set_equation_end(self, i: int) -> None:
        self.equation_end_index = i
        self.math_equations.append(self.markdown_str[self.equation_start_index : self.equation_end_index])


class States:
    def __init__(self, mee: MathEquationExtractor) -> None:
        self.usual = Usual(mee)
        self.inline_math_equation = InlineMathEquation(mee)
        self.display_math_equation = DisplayMathEquation(mee)
        self.single_backtick = SingleBacktick(mee)
        self.double_backtick = DoubleBacktick(mee)
        self.triple_backtick = TripleBacktick(mee)


class State(ABC):
    def __init__(self, mee: MathEquationExtractor) -> None:
        self.mee = mee

    @abstractmethod
    def consume(self, i: int, char: str) -> None:
        pass


class Usual(State):
    def __init__(self, mee: MathEquationExtractor) -> None:
        super().__init__(mee)

    def consume(self, i: int, char: str) -> None:
        if char == "$":
            if i != 0 and self.mee.markdown_str[i - 1] == "\\":
                pass
            elif i + 1 < self.mee.markdown_str_len and self.mee.markdown_str[i + 1] == "$":
                self.mee.set_equation_start(i)
                next(self.mee.markdown_str_enumerator)
                self.mee.state = self.mee.states.display_math_equation
            else:
                self.mee.set_equation_start(i)
                self.mee.state = self.mee.states.inline_math_equation
        elif char == "`":
            if i != 0 and self.mee.markdown_str[i - 1] == "\\":
                pass
            elif i + 2 < self.mee.markdown_str_len and self.mee.markdown_str[i + 1 : i + 3] == "``":
                next(self.mee.markdown_str_enumerator)
                next(self.mee.markdown_str_enumerator)
                self.mee.state = self.mee.states.triple_backtick
            elif i + 1 < self.mee.markdown_str_len and self.mee.markdown_str[i + 1] == "`":
                next(self.mee.markdown_str_enumerator)
                self.mee.state = self.mee.states.double_backtick
            else:
                self.mee.state = self.mee.states.single_backtick
        else:
            pass


class InlineMathEquation(State):
    def __init__(self, mee: MathEquationExtractor) -> None:
        super().__init__(mee)

    def consume(self, i: int, char: str) -> None:
        if char == "$":
            if i != 0 and self.mee.markdown_str[i - 1] == "\\":
                pass
            else:
                self.mee.set_equation_end(i + 1)
                self.mee.state = self.mee.states.usual
        else:
            pass


class DisplayMathEquation(State):
    def __init__(self, mee: MathEquationExtractor) -> None:
        super().__init__(mee)

    def consume(self, i: int, char: str) -> None:
        if char == "$":
            if i != 0 and self.mee.markdown_str[i - 1] == "\\":
                pass
            elif i + 1 < self.mee.markdown_str_len and self.mee.markdown_str[i + 1] == "$":
                self.mee.set_equation_end(i + 2)
                next(self.mee.markdown_str_enumerator)
                self.mee.state = self.mee.states.usual
        else:
            pass


class SingleBacktick(State):
    def __init__(self, mee: MathEquationExtractor) -> None:
        super().__init__(mee)

    def consume(self, i: int, char: str) -> None:
        if char == "`":
            self.mee.state = self.mee.states.usual
        else:
            pass


class DoubleBacktick(State):
    def __init__(self, mee: MathEquationExtractor) -> None:
        super().__init__(mee)

    def consume(self, i: int, char: str) -> None:
        if i + 1 < self.mee.markdown_str_len and self.mee.markdown_str[i : i + 2] == "``":
            next(self.mee.markdown_str_enumerator)
            self.mee.state = self.mee.states.usual
        else:
            pass


class TripleBacktick(State):
    def __init__(self, mee: MathEquationExtractor) -> None:
        super().__init__(mee)

    def consume(self, i: int, char: str) -> None:
        if i + 2 < self.mee.markdown_str_len and self.mee.markdown_str[i : i + 3] == "```":
            next(self.mee.markdown_str_enumerator)
            next(self.mee.markdown_str_enumerator)
            self.mee.state = self.mee.states.usual
        else:
            pass


class MathEquationPlaceholer:
    """abstract classにしていないがplaceholder_regexとplaceholder_generatorを実装すればMyMarkdownParser()の引数に使える
    TOCがsection名の文字列のみを取り出してhtmlタグを破棄してしまうため<math_equation>のようなものは使えない。
    """

    placeholder = ("!!!me", "!!!")
    placeholder_regex = re.compile(r"!!!me([0-9]+)!!!")

    @classmethod
    def placeholder_generator(cls, length: int) -> Generator[str]:
        for i in range(length):
            yield str(i).join(cls.placeholder)


class MyMarkdownParser:
    def __init__(
        self,
        md_filepath: PathLike | str,
        header_str_filepath: PathLike | str,
        footer_str_filepath: PathLike | str,
        output_filepath: PathLike | str,
        math_equation_placeholder_class: type[MathEquationPlaceholer] = MathEquationPlaceholer,
        page_title: str | None = None,
    ) -> None:
        self.math_equation_placeholder_class: type[MathEquationPlaceholer] = math_equation_placeholder_class
        self.output_filepath: PathLike | str = output_filepath
        self.page_title: str = os.path.basename(self.output_filepath) if page_title is None else page_title

        with open(header_str_filepath, encoding="utf-8") as f:
            self.header_str: str = f.read()
        self.set_page_title()

        with open(footer_str_filepath, encoding="utf-8") as f:
            self.footer_str: str = f.read()

        with open(md_filepath, encoding="utf-8") as f:
            self.being_processed_str: str = f.read()

        self.math_equations: list

    def set_page_title(self) -> None:
        self.header_str = re.sub("(?<=<title>).*?(?=</title>)", self.page_title, self.header_str)

    def math_equations_to_tags(self) -> None:
        self.math_equations, other_strings = MathEquationExtractor(self.being_processed_str).extract()
        self.being_processed_str = "".join(
            chain.from_iterable(
                zip_longest(
                    other_strings,
                    self.math_equation_placeholder_class.placeholder_generator(len(self.math_equations)),
                    fillvalue="",
                )
            )
        )

    def tags_to_math_equations(self) -> None:
        split_strings = self.math_equation_placeholder_class.placeholder_regex.split(self.being_processed_str)
        # re.splitの返り値は最初と最後はsub string(空文字列を含む)でmatch要素とsub stringが必ず交互に表れる
        for i in range(1, len(split_strings), 2):
            split_strings[i] = self.math_equations[int(split_strings[i])]
        self.being_processed_str = "".join(split_strings)

    def add_header_and_footer(self) -> None:
        self.being_processed_str = "".join([self.header_str, self.being_processed_str, self.footer_str])

    def md_to_html(self) -> None:
        self.being_processed_str = markdown.markdown(
            self.being_processed_str, extensions=["nl2br", "tables", "fenced_code", "codehilite", "toc"]
        )

    def process(self) -> None:
        self.math_equations_to_tags()
        self.md_to_html()
        self.tags_to_math_equations()
        self.add_header_and_footer()

    def save(self) -> None:
        with open(self.output_filepath, encoding="utf-8", mode="w", newline="\r\n") as f:
            print(self.being_processed_str, file=f, end="")

    def run(self) -> None:
        self.process()
        self.save()


def run_parser(input_filepath: PathLike | str, output_filepath: PathLike | str, page_title: str | None = None) -> None:
    """このmy_markdown_paresr.pyが存在するディレクトリにあるheader_str.html, footer_str.htmlを使って、input_filepathをhtmlに変換してoutput_filepathに保存する。page_titleがNoneのとき出力ファイル名がページタイトルになる")"""
    dirpath_of_this_file = Path(__file__).resolve().parent
    header_str_filepath = dirpath_of_this_file / "header_str.html"
    footer_str_filepath = dirpath_of_this_file / "footer_str.html"
    MyMarkdownParser(
        md_filepath=input_filepath,
        header_str_filepath=header_str_filepath,
        footer_str_filepath=footer_str_filepath,
        output_filepath=output_filepath,
        page_title=page_title,
    ).run()


def main() -> None:
    args = get_command_line_args()
    if args.output_filepath is None:
        output_filepath = Path(__file__).resolve().parent / "markdown_preview.html"
    else:
        output_filepath = args.output_filepath
    run_parser(args.input_filepath, output_filepath, args.page_title)


if __name__ == "__main__":
    main()
