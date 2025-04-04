from __future__ import annotations
from collections.abc import Iterable
from typing import Self, Protocol, Literal
from dataclasses import dataclass
import itertools
import os
import os.path
from os import PathLike
import jsonc
import json
from abc import ABC, abstractmethod

import pokeapi_downloader
from input_filepaths import PokeapiFilepaths, NamesFilepaths, default_input_filepaths


class NameExtended[T]:
    def __init__(self, data: T, display_name: str, retrieval_names: Iterable[str]) -> None:
        """retrieval_names はmatch()に使われる。一時的に使うデータオブジェクトとしてretrieval_namesを()にするという用法がある。"""
        self.data = data
        self.display_name = display_name
        self.retrieval_names = retrieval_names

    def match(self, query: str) -> bool:
        for name in self.retrieval_names:
            if name.startswith(query):
                return True
        return False


def load_name_extended_data[T](
    names_filepath: PathLike | str, data_dict: dict[str, T], converter: Converter
) -> dict[str, NameExtended[T]]:
    with open(names_filepath, encoding="utf-8") as f:
        names_json: dict = jsonc.load(f)
    return {
        name: NameExtended(
            data_dict[name],
            names["display_name"],
            list(itertools.chain.from_iterable(converter.convert(n) for n in names["retrieval_names"])),
        )
        for name, names in names_json.items()
    }


def load_name_extended_other_data(
    names_filepath: PathLike | str, converter: Converter
) -> dict[str, NameExtended[OtherData]]:
    """OtherDataに必要なのはnameだけであり、これをnames_filepathのkeyから作成する。"""
    with open(names_filepath, encoding="utf-8") as f:
        names_json: dict = jsonc.load(f)
    data = {name: OtherData(name) for name in names_json}
    name_extended_data = load_name_extended_data(names_filepath, data, converter)
    return name_extended_data


def retrieve_data[T](data_dict: dict[str, NameExtended[T]], query: str) -> list[NameExtended[T]]:
    return [data for data in data_dict.values() if data.match(query)]


@dataclass
class Pokemon:
    """PokeAPIのPokemonFormとそこから辿れるPokemon, PokemonSpeciesを表す。 nameはPokemonForm.name"""

    # types, abilities, moves を str で持つのは、これらが指す対象を取得するのを遅延評価するためである。起動時に全ポケモンを読み込むが、その覚える技等の取得は、そのポケモンを計算に使うときだけでよい。
    name: str
    type_names: list[str]
    ability_names: list[str]
    stats: Stats
    move_names: list[str]

    @classmethod
    def from_pokeapi_pokemon_species(cls, pokeapi_pokemon_species: dict) -> list[Self]:
        """pokeapi_pokemon_speciesから辿れるすべてのpokemon_formから作成するPokemonのリストを返す。"""
        return [
            cls.from_pokeapi_pokemon_and_form(pokemon_species_variety["pokemon"], pokemon_form)
            for pokemon_species_variety in pokeapi_pokemon_species["varieties"]
            for pokemon_form in pokemon_species_variety["pokemon"]["forms"]
        ]

    @classmethod
    def from_pokeapi_pokemon_and_form(cls, pokeapi_pokemon: dict, pokeapi_pokemon_form: dict) -> Self:
        return cls(
            name=pokeapi_pokemon_form["name"],
            type_names=[type["type.name"] for type in pokeapi_pokemon_form["types"]],
            ability_names=[ability["ability.name"] for ability in pokeapi_pokemon["abilities"]],
            stats=Stats.from_pokeapi_stats(pokeapi_pokemon["stats"]),
            move_names=[move["move.name"] for move in pokeapi_pokemon["moves"]],
        )


@dataclass
class Stats:
    h: int
    a: int
    b: int
    c: int
    d: int
    s: int

    @classmethod
    def from_pokeapi_stats(cls, pokeapi_stats: list[dict]) -> Self:
        for stat in pokeapi_stats:
            match stat:
                case {"stat.name": "hp", "base_stat": h}:
                    pass
                case {"stat.name": "attack", "base_stat": a}:
                    pass
                case {"stat.name": "defense", "base_stat": b}:
                    pass
                case {"stat.name": "special-attack", "base_stat": c}:
                    pass
                case {"stat.name": "special-defense", "base_stat": d}:
                    pass
                case {"stat.name": "speed", "base_stat": s}:
                    pass
        return cls(h, a, b, c, d, s)

    def to_str(self):
        return f"{self.h}-{self.a}-{self.b}-{self.c}-{self.d}-{self.s}"


@dataclass
class Move:
    name: str
    power: int
    damage_class: Literal["status", "physical", "special"]
    target: Literal[
        "specific-move",
        "selected-pokemon-me-first",
        "ally",
        "users-field",
        "user-or-ally",
        "opponents-field",
        "user",
        "random-opponent",
        "all-other-pokemon",
        "selected-pokemon",
        "all-opponents",
        "entire-field",
        "user-and-allies",
        "all-pokemon",
        "all-allies",
        "fainting-pokemon",
    ]
    type_name: str

    @classmethod
    def from_pokeapi_move(cls, pokeapi_move: dict) -> Self:
        return cls(
            pokeapi_move["name"],
            pokeapi_move["power"],
            pokeapi_move["damage_class.name"],
            pokeapi_move["target.name"],
            pokeapi_move["type.name"],
        )


@dataclass
class Ability:
    name: str

    @classmethod
    def from_pokeapi_ability(cls, pokeapi_ability: dict) -> Self:
        return cls(pokeapi_ability["name"])


@dataclass
class Type:
    name: str
    no_damage_to: Iterable[str]
    half_damage_to: Iterable[str]
    double_damage_to: Iterable[str]

    @classmethod
    def from_pokeapi_type(cls, pokeapi_type: dict) -> Self:
        return cls(
            pokeapi_type["name"],
            pokeapi_type["damage_relations"]["no_damage_to"],
            pokeapi_type["damage_relations"]["half_damage_to"],
            pokeapi_type["damage_relations"]["double_damage_to"],
        )

    def damage_multiplier_to(self, type_names: Iterable[str]) -> float:
        damage_multiplier = 1
        for type_name in type_names:
            if type_name in self.no_damage_to:
                damage_multiplier *= 0
            elif type_name in self.half_damage_to:
                damage_multiplier /= 2
            elif type_name in self.double_damage_to:
                damage_multiplier *= 2
        return damage_multiplier


@dataclass
class OtherData:
    """PokeAPIから取得していないデータに対して使う。現状はどうぐと他の状態。"""

    name: str


type Item = OtherData
type State = OtherData


class Converter(ABC):
    @abstractmethod
    def convert(self, input_str: str) -> list[str]:
        raise NotImplementedError


class JpToRomaji(Converter):
    def __init__(self, replacement_filepath: PathLike | str = default_input_filepaths.replacement_filepath) -> None:
        self.replacement: dict[str, str | list[str]]
        self.max_key_length: int
        with open(replacement_filepath, encoding="utf-8") as f:
            self.set_replacement(jsonc.load(f))

    def set_replacement(self, replacement: dict[str, str | list[str]]) -> None:
        self.replacement = replacement
        self.max_key_length = max(map(len, replacement))

    def convert(self, input_str: str) -> list[str]:
        output_strs: list[str] = [""]
        current_position = 0
        while current_position < len(input_str):
            for s_length in range(min(self.max_key_length + 1, len(input_str) - current_position), 0, -1):
                s = input_str[current_position : current_position + s_length]
                if (replaced := self.replacement.get(s)) is not None:
                    if isinstance(replaced, str):
                        for i in range(len(output_strs)):
                            output_strs[i] += replaced
                    else:
                        output_strs = [o + r for o, r in itertools.product(output_strs, replaced)]
                    current_position += s_length
                    break
            else:
                raise Exception(f"Unexpected character {input_str[current_position]} is in {input_str}")
        return output_strs


def pokemon_with_initial_display_name(pokeapi_pokemon_species: dict) -> list[NameExtended[Pokemon]]:
    return [
        NameExtended(
            Pokemon.from_pokeapi_pokemon_and_form(pokemon_species_variety["pokemon"], pokemon_form),
            create_initial_pokemon_display_name(pokeapi_pokemon_species, pokemon_form),
            (),
        )
        for pokemon_species_variety in pokeapi_pokemon_species["varieties"]
        for pokemon_form in pokemon_species_variety["pokemon"]["forms"]
    ]


def move_with_initial_display_name(pokeapi_move: dict) -> NameExtended[Move]:
    return NameExtended(Move.from_pokeapi_move(pokeapi_move), pokeapi_move["jp_name"]["name"], ())


def ability_with_initial_display_name(pokeapi_ability: dict) -> NameExtended[Ability]:
    return NameExtended(Ability.from_pokeapi_ability(pokeapi_ability), pokeapi_ability["jp_name"]["name"], ())


def type_with_initial_display_name(pokeapi_type: dict) -> NameExtended[Type]:
    return NameExtended(Type.from_pokeapi_type(pokeapi_type), pokeapi_type["jp_name"]["name"], ())


def create_initial_pokemon_display_name(pokemon_species, pokemon_form) -> str:
    match pokemon_form:
        case {"jp_form_name": {"name": str(s)}} if s != "":
            pass
        case {"jp_name": {"name": str(s)}} if s != "":
            pass
        case {"form_name": str(s)} if s != "":
            pass
        case _:
            s = ""
    if s == "":
        return pokemon_species["jp_name"]["name"]
    else:
        return f"{pokemon_species['jp_name']['name']}（{s}）"


class HasName(Protocol):
    name: str
    """ PokeAPIのurlにも使われる文字列であり元データの時点で一意性が保証される """


class HasNameDisplayName[T: HasName](Protocol):
    data: T
    display_name: str
    """ 重複するdisplay_nameがあると、それを表示したときに識別できない。最終的には一意になるように変更する """


def change_duplicate_display_names[T: HasNameDisplayName](data: Iterable[T]) -> None:
    """pokemonsの中で重複しているdisplay_nameを "<display_name>（name）" にインプレースで置き換える"""
    display_name_to_element: dict[str, T] = {}
    for element in data:
        if element.display_name not in display_name_to_element:
            display_name_to_element[element.display_name] = element
        else:
            dup_element = display_name_to_element.pop(element.display_name)
            dup_element.display_name = f"{dup_element.display_name}（{dup_element.data.name}）"
            element.display_name = f"{element.display_name}（{element.data.name}）"
            display_name_to_element[dup_element.display_name] = dup_element
            display_name_to_element[element.display_name] = element


def check_duplicate_display_names[T: HasNameDisplayName](data_dict: dict[str, T]) -> None:
    display_name_to_data: dict[str, T] = {}
    for data in data_dict.values():
        if data.display_name not in display_name_to_data:
            display_name_to_data[data.display_name] = data
        else:
            print(
                f"duplicate: {data.display_name} ({display_name_to_data[data.display_name].data.name}, {data.data.name})"
            )


def generate_initial_names_file[T: HasNameDisplayName](
    data: Iterable[T], output_filepath: PathLike | str, indent=4
) -> None:
    """indentはjson.dump()の引数のindent。"""
    if os.path.exists(output_filepath):
        raise Exception(f"{output_filepath} exists.")
    output: dict = {}
    for element in data:
        output[element.data.name] = {"display_name": element.display_name, "retrieval_names": [element.display_name]}
    with open(output_filepath, encoding="utf-8", mode="w") as f:
        json.dump(output, f, ensure_ascii=False, indent=indent)


def generate_other_initial_names_file(output_names_filepaths: NamesFilepaths) -> None:
    """todo: 完成後のitem, stateの内容を反映していない。"""
    # https://latest.pokewiki.net/%E3%83%80%E3%83%A1%E3%83%BC%E3%82%B8%E8%A8%88%E7%AE%97%E5%BC%8F を上から見て必要なのを列挙する
    item_names = [
        "ちからのハチマキ",
        "ものしりメガネ",
        "パンチグローブ",
        "1.2倍アイテム",
        "ジュエル",
        "こだわりハチマキ",
        "こだわりメガネ",
        "ふといホネ",
        "しんかいのキバ",
        "しんかいのウロコ",
        "でんきだま",
        "しんかのきせき",
        "とつげきチョッキ",
        "メタルパウダー",
        "メトロノーム",
        "たつじんのおび",
        "いのちのたま",
        "半減実",
    ]
    # 技、道具、特性だけから判断できない要素はすべてstateにする
    # 特性の効果が、その特性を持っているだけで永続に必ず発動するなら、その発動をstate扱いする必要はない。そうでないなら、その特性を持っているポケモンについてダメージ計算をするときに、特性の発動/非発動の両方の計算ができなければならないため、その特性の発動をstateにする。（この発動stateをデフォルトで計算するかどうかは別のところに実装する。）場の状態以外で、その状態を攻撃側ポケモンが持っているときと防御側ポケモンが持っているときで計算が変化する場合、攻撃側の状態と防御側の状態を分離する。
    state_names = [
        "はれ",
        "あめ",
        "すなあらし",
        "ゆき",
        "エレキフィールド",
        "グラスフィールド",
        "ミストフィールド",
        "サイコフィールド",
        "壁",
        "とうそうしん弱化",
        "とうそうしん強化",
        "そうだいしょう1",
        "そうだいしょう2",
        "そうだいしょう3",
        "そうだいしょう4",
        "そうだいしょう5",
        "てだすけ",
        "はたきおとす持ち物あり",
        "じゅうでん",
        "からげんき状態異常",
        "しおみずHP半分以下",
        "かたきうち強化",
        "ブーストエナジー強化",
        "マルチスケイル等発動",
        "ちいさくなる",
        "あなをほる",
        "ダイビング",
    ]

    generate_initial_names_file(
        (NameExtended(data, data.name, ()) for data in map(OtherData, item_names)),
        output_names_filepaths.item_names_filepath,
    )
    generate_initial_names_file(
        (NameExtended(data, data.name, ()) for data in map(OtherData, state_names)),
        output_names_filepaths.state_names_filepath,
    )


def generate_initial_names_file_from_pokeapi_data(
    input_pokeapi_filepaths: PokeapiFilepaths, output_names_filepaths: NamesFilepaths
) -> None:
    pokeapi_pokemon_species = pokeapi_downloader.load_pokeapi_data_json(
        input_pokeapi_filepaths.pokeapi_pokemon_species_filepath
    )
    pokeapi_moves = pokeapi_downloader.load_pokeapi_data_json(input_pokeapi_filepaths.pokeapi_moves_filepath)
    pokeapi_abilities = pokeapi_downloader.load_pokeapi_data_json(input_pokeapi_filepaths.pokeapi_abilities_filepath)
    pokeapi_types = pokeapi_downloader.load_pokeapi_data_json(input_pokeapi_filepaths.pokeapi_types_filepath)

    names_added_pokemons = list(
        itertools.chain.from_iterable(map(pokemon_with_initial_display_name, pokeapi_pokemon_species))
    )
    names_added_moves = list(map(move_with_initial_display_name, pokeapi_moves))
    names_added_abilities = list(
        map(ability_with_initial_display_name, [e for e in pokeapi_abilities if e["id"] < 10000])
    )
    names_added_types = list(map(type_with_initial_display_name, [e for e in pokeapi_types if e["id"] < 10000]))

    change_duplicate_display_names(names_added_pokemons)
    change_duplicate_display_names(names_added_moves)
    change_duplicate_display_names(names_added_abilities)
    change_duplicate_display_names(names_added_types)

    generate_initial_names_file(names_added_pokemons, output_names_filepaths.pokemon_names_filepath)
    generate_initial_names_file(names_added_moves, output_names_filepaths.move_names_filepath)
    generate_initial_names_file(names_added_abilities, output_names_filepaths.ability_names_filepath)
    generate_initial_names_file(names_added_types, output_names_filepaths.type_names_filepath)


def load_pokeapi_data(
    pokeapi_filepaths: PokeapiFilepaths,
) -> tuple[dict[str, Pokemon], dict[str, Move], dict[str, Ability], dict[str, Type]]:
    pokeapi_pokemon_species = pokeapi_downloader.load_pokeapi_data_json(
        pokeapi_filepaths.pokeapi_pokemon_species_filepath
    )
    pokeapi_moves = pokeapi_downloader.load_pokeapi_data_json(pokeapi_filepaths.pokeapi_moves_filepath)
    pokeapi_abilities = pokeapi_downloader.load_pokeapi_data_json(pokeapi_filepaths.pokeapi_abilities_filepath)
    pokeapi_types = pokeapi_downloader.load_pokeapi_data_json(pokeapi_filepaths.pokeapi_types_filepath)

    pokemon_data = {
        pokemon.name: pokemon
        for pokemon in itertools.chain.from_iterable(map(Pokemon.from_pokeapi_pokemon_species, pokeapi_pokemon_species))
    }
    move_data = {move.name: move for move in map(Move.from_pokeapi_move, pokeapi_moves)}
    ability_data = {
        ability.name: ability
        for ability in map(Ability.from_pokeapi_ability, [e for e in pokeapi_abilities if e["id"] < 10000])
    }
    type_data = {type.name: type for type in map(Type.from_pokeapi_type, [e for e in pokeapi_types if e["id"] < 10000])}

    return pokemon_data, move_data, ability_data, type_data


@dataclass(eq=False)
class AllData:
    pokemons: dict[str, NameExtended[Pokemon]]
    moves: dict[str, NameExtended[Move]]
    abilities: dict[str, NameExtended[Ability]]
    types: dict[str, NameExtended[Type]]
    items: dict[str, NameExtended[Item]]
    states: dict[str, NameExtended[State]]


def load_all_data(
    pokeapi_filepaths: PokeapiFilepaths, names_filepaths: NamesFilepaths, converter: Converter
) -> AllData:
    pokemon_data, move_data, ability_data, type_data = load_pokeapi_data(pokeapi_filepaths)
    pokemons = load_name_extended_data(names_filepaths.pokemon_names_filepath, pokemon_data, converter)
    moves = load_name_extended_data(names_filepaths.move_names_filepath, move_data, converter)
    abilities = load_name_extended_data(names_filepaths.ability_names_filepath, ability_data, converter)
    types = load_name_extended_data(names_filepaths.type_names_filepath, type_data, converter)

    items = load_name_extended_other_data(names_filepaths.item_names_filepath, converter)
    states = load_name_extended_other_data(names_filepaths.state_names_filepath, converter)

    for data in [pokemons, moves, abilities, types, items, states]:
        check_duplicate_display_names(data)

    return AllData(pokemons, moves, abilities, types, items, states)


def main() -> None:
    generate_initial_names_file_from_pokeapi_data(
        default_input_filepaths.pokeapi_filepaths, default_input_filepaths.names_filepaths
    )
    generate_other_initial_names_file(default_input_filepaths.names_filepaths)


if __name__ == "__main__":
    main()
