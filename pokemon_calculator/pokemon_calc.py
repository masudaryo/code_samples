from __future__ import annotations
from dataclasses import dataclass, field
from pokemon_data import Pokemon, Move, Ability, Type, Item, State, NameExtended, AllData, Stats
from typing import Iterable, Self, Literal, Protocol
import math
import copy

import pokemon_data
import input_processor
from input_filepaths import default_input_filepaths, InputFilepaths


@dataclass(eq=False)
class BattlePokemon:
    pokemon: NameExtended[Pokemon]
    ability: NameExtended[Ability]
    doryokuchi: int
    kotaichi: int
    seikaku_hosei: float
    item: NameExtended[Item] | None
    rank: int
    terasu_type: NameExtended[Type] | None
    level: int = 50
    all_doryokuchi: Stats | None = None
    all_kotaichi: Stats | None = None
    seikaku_hosei_up_down: (
        tuple[Literal["a", "b", "c", "d", "s", "*"], Literal["a", "b", "c", "d", "s", "*"]] | None
    ) = None


@dataclass(eq=False)
class Input:
    attacker: BattlePokemon
    defender: BattlePokemon
    move: NameExtended[Move]
    states: list[NameExtended[State]]
    hp_doryokuchi: int
    hp_kotaichi: int


@dataclass(eq=False)
class BattlePokemonArgs:
    # 無入力のときの値が一つに固定されるものは初期値として書いて良い
    # 現状はattackerとdefenderで初期値等が同じなので分けてていない。もし何かが異なるなら分けることになるだろう。
    pokemon: NameExtended[Pokemon] | None = None
    ability: NameExtended[Ability] | None = None
    doryokuchi: int | None = None
    kotaichi: int = 31
    seikaku_hosei: float = 1
    item: NameExtended[Item] | None = None
    rank: int = 0
    terasu_type: NameExtended[Type] | None = None
    level: int = 50
    all_doryokuchi: Stats | None = None
    all_kotaichi: Stats | None = None
    seikaku_hosei_up_down: (
        tuple[Literal["a", "b", "c", "d", "s", "*"], Literal["a", "b", "c", "d", "s", "*"]] | None
    ) = None

    def make_battle_pokemon(self) -> BattlePokemon:
        if self.pokemon is not None and self.ability is not None and self.doryokuchi is not None:
            return BattlePokemon(
                self.pokemon,
                self.ability,
                self.doryokuchi,
                self.kotaichi,
                self.seikaku_hosei,
                self.item,
                self.rank,
                self.terasu_type,
                self.level,
                self.all_doryokuchi,
                self.all_kotaichi,
                self.seikaku_hosei_up_down,
            )
        else:
            raise Exception("pokemon, ability, or doryokuchi is None")

    def copy(self) -> Self:
        """shallow copy"""
        copied = copy.copy(self)
        copied.all_doryokuchi = copy.copy(self.all_doryokuchi)
        copied.all_kotaichi = copy.copy(self.all_kotaichi)
        return copied


@dataclass(eq=False)
class InputArgs:
    # 無入力のときの値が一つに固定されるものは初期値として書いて良い
    attacker: BattlePokemonArgs = field(default_factory=BattlePokemonArgs)
    defender: BattlePokemonArgs = field(default_factory=BattlePokemonArgs)
    move: NameExtended[Move] | None = None
    states: list[NameExtended[State]] = field(default_factory=list)
    hp_doryokuchi: int | None = None
    hp_kotaichi: int = 31

    def copy(self) -> Self:
        """shallow copy"""
        copied = copy.copy(self)
        copied.attacker = self.attacker.copy()
        copied.defender = self.defender.copy()
        copied.states = copy.copy(self.states)
        return copied

    def make_input(self) -> Input:
        if self.move is not None and self.hp_doryokuchi is not None:
            return Input(
                self.attacker.make_battle_pokemon(),
                self.defender.make_battle_pokemon(),
                self.move,
                self.states,
                self.hp_doryokuchi,
                self.hp_kotaichi,
            )
        else:
            raise Exception("move or hp_doryokuchi is None")


class Damage:
    def __init__(self, damages: Iterable[int]) -> None:
        self.damages: list[int] = list(damages)
        self.min: int = self.damages[0]
        self.max: int = self.damages[-1]
        self.average: float = sum(self.damages) / len(self.damages)


class Output:
    def __init__(
        self,
        damage: Damage,
        attacker_attack: int,
        attacker_doryokuchi: int,
        attacker_kotaichi: int,
        attacker_seikaku_hosei: float,
        defender_defense: int,
        defender_doryokuchi: int,
        defender_kotaichi: int,
        defender_seikaku_hosei: float,
        defender_hp: int,
        defender_hp_doryokuchi: int,
        defender_hp_kotaichi: int,
        input: Input,
    ) -> None:
        self.damage: Damage = damage
        self.attacker_attack: int = attacker_attack
        self.attacker_doryokuchi: int = attacker_doryokuchi
        self.attacker_kotaichi: int = attacker_kotaichi
        self.attacker_seikaku_hosei: float = attacker_seikaku_hosei
        self.defender_defense: int = defender_defense
        self.defender_doryokuchi: int = defender_doryokuchi
        self.defender_kotaichi: int = defender_kotaichi
        self.defender_seikaku_hosei: float = defender_seikaku_hosei
        self.defender_hp: int = defender_hp
        self.defender_hp_doryokuchi: int = defender_hp_doryokuchi
        self.defender_hp_kotaichi: int = defender_hp_kotaichi
        self.min_damage_ratio: float = self.damage.min / self.defender_hp
        self.max_damage_ratio: float = self.damage.max / self.defender_hp
        self.average_damage_ratio: float = self.damage.average / self.defender_hp
        self.input: Input = input

    def _seikaku_hosei_to_sign(self, seikaku_hosei: float) -> str:
        if seikaku_hosei == 1.1:
            return "+"
        elif seikaku_hosei == 0.9:
            return "-"
        else:
            return "."

    def to_str(self) -> str:
        return " ".join(
            [
                f"{self.attacker_attack:>3d}({self.attacker_doryokuchi:>3d}{self._seikaku_hosei_to_sign(self.attacker_seikaku_hosei)})",
                f"{self.defender_hp:>3d}({self.defender_hp_doryokuchi:>3d})",
                f"{self.defender_defense:>3d}({self.defender_doryokuchi:>3d}{self._seikaku_hosei_to_sign(self.defender_seikaku_hosei)})",
                *(f"{damage:>3d}" for damage in reversed(self.damage.damages)),
                f"{self.max_damage_ratio * 100:>5.1f}~{self.min_damage_ratio * 100:>5.1f}%",
                f"{self.input.attacker.ability.display_name}@{self.input.attacker.item.display_name if self.input.attacker.item is not None else '*'}{self.input.attacker.rank:>+2d}t{t.display_name if (t := self.input.attacker.terasu_type) is not None else '*'}",
                f"{self.input.defender.ability.display_name}@{self.input.defender.item.display_name if self.input.defender.item is not None else '*'}{self.input.defender.rank:>+2d}t{t.display_name if (t := self.input.defender.terasu_type) is not None else '*'}",
                *(f"{state.display_name}" for state in self.input.states),
            ]
        )

    def hp_bar_str(self) -> str:
        min_damage_percent = self.min_damage_ratio * 100
        max_damage_percent = self.max_damage_ratio * 100
        line_change_points: list[float] = [-1, -1]
        line_change_points[0] = 100 - max_damage_percent if max_damage_percent < 100 else 0
        line_change_points[1] = 100 - min_damage_percent if min_damage_percent < 100 else 0
        line_change_len: list[int] = [
            round_5_to_up(1 if 0 < point < 1 else point) for point in line_change_points
        ]  # round_5_to_upはdownよりもダメージを少なく見積もる
        return (
            " " * 49
            + "=" * line_change_len[0]
            + "-" * (line_change_len[1] - line_change_len[0])
            + "_" * (100 - line_change_len[1])
        )

    def header_str(self) -> str:
        return " ".join(
            [
                f"{'a':^9}",
                f"{'h':^8}",
                f"{'b':^9}",
                "".join((f"{i / 16 * 1000:>4.0f}" for i in range(1, 16))) + "  1",
                f"{self.input.attacker.pokemon.display_name}({self.input.attacker.pokemon.data.stats.to_str()})",
                self.input.move.display_name,
                f"{self.input.defender.pokemon.display_name}({self.input.defender.pokemon.data.stats.to_str()})",
            ]
        )


def calc_nouryokuchi(shuzokuchi: int, doryokuchi: int, kotaichi: int, seikaku_hosei: float, level: int) -> int:
    return math.floor(
        math.floor(math.floor(shuzokuchi * 2 + kotaichi + doryokuchi / 4) * level / 100 + 5) * seikaku_hosei
    )


def calc_hp(shuzokuchi: int, doryokuchi: int, kotaichi: int, level: int) -> int:
    return math.floor(math.floor(shuzokuchi * 2 + kotaichi + doryokuchi / 4) * level / 100 + level + 10)


class InputStats(Protocol):
    pokemon: NameExtended[Pokemon]
    level: int
    all_doryokuchi: Stats | None
    all_kotaichi: Stats | None
    seikaku_hosei_up_down: tuple[Literal["a", "b", "c", "d", "s", "*"], Literal["a", "b", "c", "d", "s", "*"]] | None


def calc_stat(input_stats: InputStats, stat_str: Literal["h", "a", "b", "c", "d", "s"]) -> int:
    """all_doryokuchi, all_kotaichiを使って能力値を計算する。 all_kotaichiがNoneのとき、個体値31を仮定する。"""
    if input_stats.all_doryokuchi is None:
        raise Exception("pokemon_stats.all_doryokuchi is None")
    all_kotaichi = input_stats.all_kotaichi if input_stats.all_kotaichi is not None else Stats(31, 31, 31, 31, 31, 31)
    if stat_str == "h":
        return calc_hp(
            input_stats.pokemon.data.stats.h, input_stats.all_doryokuchi.h, all_kotaichi.h, input_stats.level
        )
    elif stat_str == "a":
        return calc_nouryokuchi(
            input_stats.pokemon.data.stats.a,
            input_stats.all_doryokuchi.a,
            all_kotaichi.a,
            get_seikaku_hosei(input_stats, "a"),
            input_stats.level,
        )
    elif stat_str == "b":
        return calc_nouryokuchi(
            input_stats.pokemon.data.stats.b,
            input_stats.all_doryokuchi.b,
            all_kotaichi.b,
            get_seikaku_hosei(input_stats, "b"),
            input_stats.level,
        )
    elif stat_str == "c":
        return calc_nouryokuchi(
            input_stats.pokemon.data.stats.c,
            input_stats.all_doryokuchi.c,
            all_kotaichi.c,
            get_seikaku_hosei(input_stats, "c"),
            input_stats.level,
        )
    elif stat_str == "d":
        return calc_nouryokuchi(
            input_stats.pokemon.data.stats.d,
            input_stats.all_doryokuchi.d,
            all_kotaichi.d,
            get_seikaku_hosei(input_stats, "d"),
            input_stats.level,
        )
    elif stat_str == "s":
        return calc_nouryokuchi(
            input_stats.pokemon.data.stats.s,
            input_stats.all_doryokuchi.s,
            all_kotaichi.s,
            get_seikaku_hosei(input_stats, "s"),
            input_stats.level,
        )


class SeikakuHosei(Protocol):
    seikaku_hosei_up_down: tuple[Literal["a", "b", "c", "d", "s", "*"], Literal["a", "b", "c", "d", "s", "*"]] | None


def get_seikaku_hosei(seikaku_hosei: SeikakuHosei, stat_str: Literal["a", "b", "c", "d", "s"]) -> float:
    if seikaku_hosei.seikaku_hosei_up_down is None:
        raise Exception("pokemon_stats.seikaku_hosei_up_down is None")
    if stat_str == seikaku_hosei.seikaku_hosei_up_down[0]:
        return 1.1
    elif stat_str == seikaku_hosei.seikaku_hosei_up_down[1]:
        return 0.9
    else:
        return 1


# fmt: off
def calc_damage(input: Input, all_data: AllData) -> Output:
    # この関数は以下のページの計算の再現である。ページの内容との対応関係を明確にする、かつ、計算の自由度を最大限に保つ（例えば、防御側のこうげき値を使ってダメージを計算する技、イカサマがある）ため、意図的に関数への分離や抽象化を行っていない。
    # https://latest.pokewiki.net/%E3%83%80%E3%83%A1%E3%83%BC%E3%82%B8%E8%A8%88%E7%AE%97%E5%BC%8F

    attacker: BattlePokemon = input.attacker
    defender: BattlePokemon = input.defender
    move: Move = input.move.data

    state_names: list[str] = [state.data.name for state in input.states]

    attacker_ability_name: str = attacker.ability.data.name
    defender_ability_name: str = defender.ability.data.name

    # ステラタイプはポケモンのtype_nameにはしないが、技（テラバースト/テラクラスター）のtype_nameにはする。これが計算上扱いやすい
    attacker_type_names: list[str] = attacker.pokemon.data.type_names if attacker.terasu_type is None or attacker.terasu_type == "stellar" else [attacker.terasu_type.data.name]
    defender_type_names: list[str] = defender.pokemon.data.type_names if defender.terasu_type is None or attacker.terasu_type == "stellar" else [defender.terasu_type.data.name]

    attacker_item_name: str = attacker.item.data.name if attacker.item is not None else ""
    defender_item_name: str = defender.item.data.name if defender.item is not None else ""

    move_name: str = move.name
    move_power: int = move.power
    move_type_name: str = move.type_name
    move_damage_class: Literal["status", "physical", "special"] = move.damage_class
    if move_name == "tera-blast" and attacker.terasu_type is not None:
        move_type_name = attacker.terasu_type.data.name
        if "物理" in state_names:
            move_damage_class = "physical"
        if attacker.terasu_type.data.name == "stellar":
            move_power = 100
    if attacker_ability_name in ["pixilate", "galvanize"]: # フェアリースキン, エレキスキン
        if move_type_name == "normal" and not (move_name == "tera-blast" and attacker.terasu_type is not None):
            if attacker_ability_name == "pixilate":
                move_type_name = "fairy"
            else: # "galvanize"
                move_type_name = "electric"
    if move_name == "ivy-cudgel":
        if attacker.pokemon.data.name == "ogerpon-wellspring-mask":
            move_type_name = "water"
        elif attacker.pokemon.data.name == "ogerpon-hearthflame-mask":
            move_type_name = "fire"
        elif attacker.pokemon.data.name == "ogerpon-cornerstone-mask":
            move_type_name = "rock"

    if not (move_type_name == "stellar" and defender.terasu_type is not None):
        move_type_damgage_multiplier: float = all_data.types[move_type_name].data.damage_multiplier_to(defender_type_names)
    else:
        move_type_damgage_multiplier: float = 2

    if move_name == "psyshock": # サイコショック
        attacker_shuzokuchi = attacker.pokemon.data.stats.c
        attacker_doryokuchi = attacker.doryokuchi if attacker.all_doryokuchi is None else attacker.all_doryokuchi.c
        attacker_kotaichi = attacker.kotaichi if attacker.all_kotaichi is None else attacker.all_kotaichi.c
        attacker_seikaku_hosei = attacker.seikaku_hosei if attacker.seikaku_hosei_up_down is None else get_seikaku_hosei(attacker, "c")
        defender_shuzokuchi = defender.pokemon.data.stats.b
        defender_doryokuchi = defender.doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.b
        defender_kotaichi = defender.kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.b
        defender_seikaku_hosei = defender.seikaku_hosei if defender.seikaku_hosei_up_down is None else get_seikaku_hosei(defender, "b")
    elif move_name == "body-press": # ボディプレス
        attacker_shuzokuchi = attacker.pokemon.data.stats.b
        attacker_doryokuchi = attacker.doryokuchi if attacker.all_doryokuchi is None else attacker.all_doryokuchi.b
        attacker_kotaichi = attacker.kotaichi if attacker.all_kotaichi is None else attacker.all_kotaichi.b
        attacker_seikaku_hosei = attacker.seikaku_hosei if attacker.seikaku_hosei_up_down is None else get_seikaku_hosei(attacker, "b")
        defender_shuzokuchi = defender.pokemon.data.stats.b
        defender_doryokuchi = defender.doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.b
        defender_kotaichi = defender.kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.b
        defender_seikaku_hosei = defender.seikaku_hosei if defender.seikaku_hosei_up_down is None else get_seikaku_hosei(defender, "b")
    elif move_name == "foul-play": # イカサマ attackerとdefenderの使う値に注意
        attacker_shuzokuchi = defender.pokemon.data.stats.a
        attacker_doryokuchi = attacker.doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.a
        attacker_kotaichi = attacker.kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.a
        attacker_seikaku_hosei = attacker.seikaku_hosei if defender.seikaku_hosei_up_down is None else get_seikaku_hosei(defender, "a")
        defender_shuzokuchi = defender.pokemon.data.stats.b
        defender_doryokuchi = defender.doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.b
        defender_kotaichi = defender.kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.b
        defender_seikaku_hosei = defender.seikaku_hosei if defender.seikaku_hosei_up_down is None else get_seikaku_hosei(defender, "b")
    elif "物理" in state_names or move_damage_class == "physical":
        attacker_shuzokuchi = attacker.pokemon.data.stats.a
        attacker_doryokuchi = attacker.doryokuchi if attacker.all_doryokuchi is None else attacker.all_doryokuchi.a
        attacker_kotaichi = attacker.kotaichi if attacker.all_kotaichi is None else attacker.all_kotaichi.a
        attacker_seikaku_hosei = attacker.seikaku_hosei if attacker.seikaku_hosei_up_down is None else get_seikaku_hosei(attacker, "a")
        defender_shuzokuchi = defender.pokemon.data.stats.b
        defender_doryokuchi = defender.doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.b
        defender_kotaichi = defender.kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.b
        defender_seikaku_hosei = defender.seikaku_hosei if defender.seikaku_hosei_up_down is None else get_seikaku_hosei(defender, "b")
    elif "特殊" in state_names or move_damage_class == "special":
        attacker_shuzokuchi = attacker.pokemon.data.stats.c
        attacker_doryokuchi = attacker.doryokuchi if attacker.all_doryokuchi is None else attacker.all_doryokuchi.c
        attacker_kotaichi = attacker.kotaichi if attacker.all_kotaichi is None else attacker.all_kotaichi.c
        attacker_seikaku_hosei = attacker.seikaku_hosei if attacker.seikaku_hosei_up_down is None else get_seikaku_hosei(attacker, "c")
        defender_shuzokuchi = defender.pokemon.data.stats.d
        defender_doryokuchi = defender.doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.d
        defender_kotaichi = defender.kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.d
        defender_seikaku_hosei = defender.seikaku_hosei if defender.seikaku_hosei_up_down is None else get_seikaku_hosei(defender, "d")
    else:
        raise Exception(f"Invalid damage_class: {move_damage_class}")
    attacker_attack: int = calc_nouryokuchi(attacker_shuzokuchi, attacker_doryokuchi, attacker_kotaichi, attacker_seikaku_hosei, attacker.level)
    defender_defense: int = calc_nouryokuchi(defender_shuzokuchi, defender_doryokuchi, defender_kotaichi, defender_seikaku_hosei, defender.level)

    iryoku_hoseichi = Hoseichi()
    if defender_ability_name == "aura-break" and attacker_ability_name == "dark-aura" and move_type_name == "dark": # オーラブレイク
        iryoku_hoseichi.hosei(3072)
    if defender_ability_name == "aura-break" and attacker_ability_name == "fairy-aura" and move_type_name == "fairy": # オーラブレイク
        iryoku_hoseichi.hosei(3072)
    if "とうそうしん弱化" in state_names and attacker_ability_name == "rivalry":
        iryoku_hoseichi.hosei(3072)
    if "そうだいしょう1" in state_names and attacker_ability_name == "supreme-overlord":
        iryoku_hoseichi.hosei(4506)
    if attacker_ability_name in ["pixilate", "galvanize"]: # フェアリースキン, エレキスキン
        if move.type_name == "normal" and not (move_name == "tera-blast" and attacker.terasu_type is not None): # ここはmove.type_nameで判定する
            iryoku_hoseichi.hosei(4915)
    if attacker_ability_name == "iron-fist" and is_punch(move): # てつのこぶし
        iryoku_hoseichi.hosei(4915)
    if attacker_ability_name == "reckless" and is_handou(move): # すてみ
        iryoku_hoseichi.hosei(4915)
    if "そうだいしょう2" in state_names and attacker_ability_name == "supreme-overlord":
        iryoku_hoseichi.hosei(4915)
    if "とうそうしん強化" in state_names and attacker_ability_name == "rivalry":
        iryoku_hoseichi.hosei(5120)
    # バッテリー ダブル専用
    if attacker_ability_name == "sheer-force" and is_chikarazuku_applicable(move): # ちからずく
        iryoku_hoseichi.hosei(5325)
    if attacker_ability_name == "sand-force" and "すなあらし" in state_names and move_type_name in ["rock", "ground", "steel"]: # すなのちから
        iryoku_hoseichi.hosei(5325)
    if "アナライズ発動" in state_names and attacker_ability_name == "analytic":
        iryoku_hoseichi.hosei(5325)
    if attacker_ability_name == "tough-claws" and is_chokusetsu(move) and attacker_item_name != "パンチグローブ": # かたいツメ
        iryoku_hoseichi.hosei(5325)
    if "そうだいしょう3" in state_names and attacker_ability_name == "supreme-overlord":
        iryoku_hoseichi.hosei(5325)
    if attacker_ability_name == "punk-rock" and is_oto(move): # パンクロック
        iryoku_hoseichi.hosei(5325)
    # パワースポット ダブル専用
    if attacker_ability_name == "fairy-aura" and move_type_name == "fairy" and defender_ability_name != "aura-break": # フェアリーオーラ
        iryoku_hoseichi.hosei(5448)
    if attacker_ability_name == "dark-aura" and move_type_name == "dark" and defender_ability_name != "aura-break": # ダークオーラ
        iryoku_hoseichi.hosei(5448)
    if "そうだいしょう4" in state_names and attacker_ability_name == "supreme-overlord":
        iryoku_hoseichi.hosei(5734)
    if attacker_ability_name == "sharpness" and is_cutting(move):
        iryoku_hoseichi.hosei(6144)
    if attacker_ability_name == "technician" and move_power <= 60: # テクニシャン
        iryoku_hoseichi.hosei(6144)
    if attacker_ability_name == "flare-boost" and "ねつぼうそう発動" in state_names and move_damage_class == "special": # ねつぼうそう
        iryoku_hoseichi.hosei(6144)
    if attacker_ability_name == "toxic-boost" and "どくぼうそう発動" in state_names and move_damage_class == "physical": # どくぼうそう
        iryoku_hoseichi.hosei(6144)
    if attacker_ability_name == "strong-jaw" and is_kamitsuki(move): # がんじょうあご
        iryoku_hoseichi.hosei(6144)
    if attacker_ability_name == "mega-launcher" and is_hadou(move): # メガランチャー
        iryoku_hoseichi.hosei(6144)
    if attacker_ability_name == "steely-spirit" and move_type_name == "steel": # はがねのせいしん
        iryoku_hoseichi.hosei(6144)
    if "そうだいしょう5" in state_names and attacker_ability_name == "supreme-overlord":
        iryoku_hoseichi.hosei(6144)
    if move_name == "psyblade" and "エレキフィールド" in state_names:
        iryoku_hoseichi.hosei(6144)
    if defender_ability_name == "dry-skin" and move_type_name == "fire": # かんそうはだ
        iryoku_hoseichi.hosei(5120)
    if attacker_item_name == "ちからのハチマキ" and move_damage_class == "physical":
        iryoku_hoseichi.hosei(4505)
    if attacker_item_name == "ものしりメガネ" and move_damage_class == "special":
        iryoku_hoseichi.hosei(4505)
    if attacker_item_name == "パンチグローブ" and is_punch(move):
        iryoku_hoseichi.hosei(4506)
    if (attacker_item_name == "1.2倍アイテム"
        or attacker_item_name == "ノーマル1.2倍" and move_type_name == "normal"
        or attacker_item_name == "かくとう1.2倍" and move_type_name == "fighting"
        or attacker_item_name == "ひこう1.2倍" and move_type_name == "flying"
        or attacker_item_name == "どく1.2倍" and move_type_name == "poison"
        or attacker_item_name == "じめん1.2倍" and move_type_name == "ground"
        or attacker_item_name == "いわ1.2倍" and move_type_name == "rock"
        or attacker_item_name == "むし1.2倍" and move_type_name == "bug"
        or attacker_item_name == "ゴースト1.2倍" and move_type_name == "ghost"
        or attacker_item_name == "はがね1.2倍" and move_type_name == "steel"
        or attacker_item_name == "ほのお1.2倍" and move_type_name == "fire"
        or attacker_item_name == "みず1.2倍" and move_type_name == "water"
        or attacker_item_name == "くさ1.2倍" and move_type_name == "grass"
        or attacker_item_name == "でんき1.2倍" and move_type_name == "electric"
        or attacker_item_name == "エスパー1.2倍" and move_type_name == "psychic"
        or attacker_item_name == "こおり1.2倍" and move_type_name == "ice"
        or attacker_item_name == "ドラゴン1.2倍" and move_type_name == "dragon"
        or attacker_item_name == "あく1.2倍" and move_type_name == "dark"
        or attacker_item_name == "フェアリー1.2倍" and move_type_name == "fairy"
        or attacker_item_name == "こんごうだま" and move_type_name in ["dragon", "steel"]
        or attacker_item_name == "しらたま" and move_type_name in ["water", "dragon"]
        or attacker_item_name == "はっきんだま" and move_type_name in ["dragon", "ghost"]
        or attacker_item_name == "こころのしずく" and move_type_name in ["psychic", "dragon"]
        or attacker_item_name == "オーガポン仮面"
    ):
        iryoku_hoseichi.hosei(4915)
    if attacker_item_name == "ノーマルジュエル" and move_type_name == "normal":
        iryoku_hoseichi.hosei(5325)
    if move_name == "solar-beam" and {"あめ", "すなあらし", "ゆき"}.isdisjoint(set(state_names)): # ソーラービーム悪天候
        iryoku_hoseichi.hosei(2048)
    if move_name == "solar-blade" and {"あめ", "すなあらし", "ゆき"}.isdisjoint(set(state_names)): # ソーラーブレード悪天候
        iryoku_hoseichi.hosei(2048)
    # さきどり SV未実装
    if "はたきおとす持ち物あり" in state_names:
        iryoku_hoseichi.hosei(6144)
    # てだすけ ダブル専用
    if move_name == "grav-apple" and "じゅうりょく" in state_names: # Gのちから
        iryoku_hoseichi.hosei(6144)
    if move_name == "expanding-force" and "サイコフィールド" in state_names: # ワイドフォース
        iryoku_hoseichi.hosei(6144)
    if "じゅうでん" in state_names and move_type_name == "electric":
        iryoku_hoseichi.hosei(8192)
    if "しおみずHP半分以下" in state_names and move_name == "brine":
        iryoku_hoseichi.hosei(8192)
    if "からげんき状態異常" in state_names and move_name == "facade":
        iryoku_hoseichi.hosei(8192)
    if move_name == "venoshock" and "ベノムショック強化" in state_names:
        iryoku_hoseichi.hosei(8192)
    if move_name == "retaliate" and "かたきうち強化" in state_names:
        iryoku_hoseichi.hosei(8192)
    if move_name in ["fusion-bolt", "fusion-flare"] and "クロスサンダー/フレイム強化" in state_names: # クロスサンダーの後にクロスフレイム、またはその逆
        iryoku_hoseichi.hosei(8192)
    if move_name == "rising-voltage" and "エレキフィールド" in state_names:
        iryoku_hoseichi.hosei(8192)
    if ("グラスフィールド" in state_names and move_name in ["earthquake", "bulldoze"]
        or "ミストフィールド" in state_names and move_type_name == "dragon"):
        iryoku_hoseichi.hosei(2048)
    if ("エレキフィールド" in state_names and move_type_name == "electric"
        or "グラスフィールド" in state_names and move_type_name == "grass"
        or "サイコフィールド" in state_names and move_type_name == "psychic"):
        iryoku_hoseichi.hosei(5325)
    # みずあそび SV未実装
    # どろあそび SV未実装

    if move_name == "acrobatics" and "アクロバット持ち物なし" in state_names:
        move_power *= 2
    if move_name == "fishious-rend" and "エラがみ強化" in state_names:
        move_power *= 2
    if move_name == "bolt-beak" and "でんげきくちばし強化" in state_names:
        move_power *= 2
    if move_name == "assurance" and "ダメおし強化" in state_names:
        move_power *= 2
    if move_name == "hex" and "たたりめ強化" in state_names: # たたりめはwikiに記述がなく正しいかどうか不明
        move_power *= 2
    if move_name == "infernal-parade" and "ひゃっきやこう強化" in state_names: # ひゃっきやこうもwikiに記載なし
        move_power *= 2

    final_iryoku = round_5_to_down(move_power * iryoku_hoseichi.hoseichi / 4096)
    if final_iryoku < 1:
        final_iryoku = 1
    # テラスタル時の威力60未満補正が適用されない技は、連続技と元から優先度が1以上の技（らしい）。これを実装するにはmove["meta"]の不足分の追記と優先度のデータ取得が必要。

    attack_hoseichi = Hoseichi()
    if attacker_ability_name == "slow-start" and "スロースタート中" in state_names and move_damage_class == "physical":
        attack_hoseichi.hosei(2048)
    if attacker_ability_name == "defeatist" and "よわきHP半分以下" in state_names:
        attack_hoseichi.hosei(2048)
    if defender_ability_name == "vessel-of-ruin" and move_damage_class == "special": # わざわいのうつわ
        attack_hoseichi.hosei(3072)
    if defender_ability_name == "tablets-of-ruin" and move_damage_class == "physical": # わざわいのおふだ
        attack_hoseichi.hosei(3072)
    if "ブーストエナジー等攻撃強化" in state_names and attacker_ability_name in ["quark-drive", "protosynthesis"]: # クォークチャージ、こだいかっせい
        attack_hoseichi.hosei(5325)
    if attacker_ability_name == "transistor" and move_type_name == "electric": # トランジスタ
        attack_hoseichi.hosei(5325)
    if attacker_ability_name == "hadron-engine" and "エレキフィールド" in state_names and move_damage_class == "special": # ハドロンエンジン
        attack_hoseichi.hosei(5461)
    if attacker_ability_name == "orichalcum-pulse" and "にほんばれ" in state_names and move_damage_class == "physical": # ひひいろのこどう
        attack_hoseichi.hosei(5461)
    if attacker_ability_name == "flower-gift" and "にほんばれ" in state_names: # フラワーギフト
        attack_hoseichi.hosei(6144)
    if "こんじょう発動" in state_names:
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "overgrow" and "しんりょく発動" in state_names and move_type_name == "grass":
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "blaze" and "もうか発動" in state_names and move_type_name == "fire":
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "torrent" and "げきりゅう発動" in state_names and move_type_name == "water":
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "swarm" and "むしのしらせ発動" in state_names and move_type_name == "bug":
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "flash-fire" and "もらいび発動" in state_names and move_type_name == "fire":
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "solar-power" and "にほんばれ" in state_names and move_damage_class == "special": # サンパワー
        attack_hoseichi.hosei(6144)
    # プラス ダブル専用
    # マイナス ダブル専用
    if attacker_ability_name == "rocky-payload" and move_type_name == "rock": # いわはこび
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "steelworker" and move_type_name == "steel": # はがねつかい
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "gorilla-tactics" and move_damage_class == "physical": # ごりむちゅう
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "dragons-maw" and move_type_name == "dragon": # りゅうのあぎと
        attack_hoseichi.hosei(6144)
    if attacker_ability_name == "huge-power" and move_damage_class == "physical": # ちからもち
        attack_hoseichi.hosei(8192)
    if attacker_ability_name == "pure-power" and move_damage_class == "physical": # ヨガパワー
        attack_hoseichi.hosei(8192)
    if attacker_ability_name == "water-bubble" and move_type_name == "water": # すいほう 水攻撃
        attack_hoseichi.hosei(8192)
    if attacker_ability_name == "stakeout" and "はりこみ発動" in state_names:
        attack_hoseichi.hosei(8192)
    if defender_ability_name == "thick-fat" and move_type_name in ["fire", "ice"]: # あついしぼう
        attack_hoseichi.hosei(2048)
    if defender_ability_name == "heatproof" and move_type_name == "fire": # たいねつ
        attack_hoseichi.hosei(2048)
    if defender_ability_name == "water-bubble" and move_type_name == "fire": # すいほう 炎受け
        attack_hoseichi.hosei(2048)
    if defender_ability_name == "purifying-salt" and move_type_name == "ghost": # きよめのしお
        attack_hoseichi.hosei(2048)
    if attacker_item_name == "こだわり":
        attack_hoseichi.hosei(6144)
    if attacker_item_name == "こだわりハチマキ" and move_damage_class == "physical":
        attack_hoseichi.hosei(6144)
    if attacker_item_name == "こだわりメガネ" and move_damage_class == "special":
        attack_hoseichi.hosei(6144)
    if attacker_item_name == "ふといホネ" and move_damage_class == "physical":
        attack_hoseichi.hosei(8192)
    if attacker_item_name == "しんかいのキバ" and move_damage_class == "special":
        attack_hoseichi.hosei(8192)
    if attacker_item_name == "でんきだま":
        attack_hoseichi.hosei(8192)

    final_attack = math.floor(attacker_attack * rank_multiplier(attacker.rank))
    if attacker_ability_name == "hustle": # はりきり
        final_attack = math.floor(final_attack * 6144 / 4096)
    final_attack = round_5_to_down(final_attack * attack_hoseichi.hoseichi / 4096)
    if final_attack < 1:
        final_attack = 1

    defense_hoseichi = Hoseichi()
    if attacker_ability_name == "beads-of-ruin" and move_damage_class == "special" and move_name != "psyshock": # わざわいのたま
        defense_hoseichi.hosei(3072)
    if attacker_ability_name == "sword-of-ruin" and move_damage_class == "physical" or move_name == "psyshock": # わざわいのつるぎ
        defense_hoseichi.hosei(3072)
    if "ブーストエナジー等耐久強化" in state_names and defender_ability_name in ["quark-drive", "protosynthesis"]: # クォークチャージ、こだいかっせい
        defense_hoseichi.hosei(5325)
    if defender_ability_name == "flower-gift" and "にほんばれ"in state_names and move_damage_class == "special": # フラワーギフト
        defense_hoseichi.hosei(6144)
    if defender_ability_name == "marvel-scale" and "ふしぎなうろこ発動" in state_names and move_damage_class == "physical":
        defense_hoseichi.hosei(6144)
    if defender_ability_name == "grass-pelt" and "グラスフィールド" in state_names and move_damage_class == "physical":
        defense_hoseichi.hosei(6144)
    if defender_ability_name == "fur-coat" and move_damage_class == "physical":
        defense_hoseichi.hosei(8192)
    if defender_item_name == "しんかのきせき":
        defense_hoseichi.hosei(6144)
    if defender_item_name == "とつげきチョッキ" and move_damage_class == "special" and move_name != "psyshock":
        defense_hoseichi.hosei(6144)
    if defender_item_name == "しんかいのウロコ" and move_damage_class == "special":
        defense_hoseichi.hosei(8192)
    if defender_item_name == "メタルパウダー" and move_damage_class == "physical":
        defense_hoseichi.hosei(8192)

    final_defense = math.floor(defender_defense * rank_multiplier(defender.rank))
    if "すなあらし" in state_names and "rock" in defender_type_names and move_damage_class == "special" and move_name != "psyshock":
        final_defense = math.floor(final_defense * 6144 / 4096)
    if "ゆき" in state_names and "ice" in defender_type_names and move_damage_class == "physical":
        final_defense = math.floor(final_defense * 6144 / 4096)
    final_defense = round_5_to_down(final_defense * defense_hoseichi.hoseichi / 4096)
    if final_defense < 1:
        final_defense = 1

    damage_hoseichi = Hoseichi()
    if "壁" in state_names:
        if "ダブルバトル" in state_names and move.target in ["all-other-pokemon", "all-opponents"]:
            damage_hoseichi.hosei(2732)
        else:
            damage_hoseichi.hosei(2048)
    if attacker_ability_name == "neuroforce" and move_type_damgage_multiplier >= 2: # ブレインフォース抜群
        damage_hoseichi.hosei(5120)
    if move_name == "collision-course" and move_type_damgage_multiplier >= 2: # アクセルブレイク抜群
        damage_hoseichi.hosei(5461)
    if move_name == "electro-drift" and move_type_damgage_multiplier >= 2: # イナズマドライブ抜群
        damage_hoseichi.hosei(5461)
    if attacker_ability_name == "sniper" and "きゅうしょ" in state_names: # スナイパー
        damage_hoseichi.hosei(6144)
    if attacker_ability_name == "tinted-lens" and move_type_damgage_multiplier <= 1/2: # いろめがね
        damage_hoseichi.hosei(8192)
    if defender_ability_name == "fluffy" and move_type_name == "fire": # もふもふ炎受け
        damage_hoseichi.hosei(8192)
    if "マルチスケイル発動" in state_names and defender_ability_name == "multiscale":
        damage_hoseichi.hosei(2048)
    if "ファントムガード発動" in state_names and defender_ability_name == "shadow-shield":
        damage_hoseichi.hosei(2048)
    if defender_ability_name == "fluffy" and is_chokusetsu(move): # もふもふ直接攻撃受け
        damage_hoseichi.hosei(2048)
    if defender_ability_name == "punk-rock" and is_oto(move): # パンクロック音技受け
        damage_hoseichi.hosei(2048)
    if defender_ability_name == "ice-scales" and move_damage_class == "special": # こおりのりんぷん
        damage_hoseichi.hosei(2048)
    # フレンドガード ダブル専用
    if defender_ability_name == "solid-rock" and move_type_damgage_multiplier >= 2: # ハードロック
        damage_hoseichi.hosei(3072)
    if defender_ability_name == "filter" and move_type_damgage_multiplier >= 2: # フィルター
        damage_hoseichi.hosei(3072)
    if defender_ability_name == "prism-armor" and move_type_damgage_multiplier >= 2: # プリズムアーマー todo:?ハードロック、フィルターと異なりかたやぶりに無効化されないらしい
        damage_hoseichi.hosei(3072)
    if attacker_item_name == "メトロノーム":
        if "メトロノーム2発目" in state_names:
            damage_hoseichi.hosei(4915)
        if "メトロノーム3発目" in state_names:
            damage_hoseichi.hosei(5734)
        if "メトロノーム4発目" in state_names:
            damage_hoseichi.hosei(6553)
        if "メトロノーム5発目" in state_names:
            damage_hoseichi.hosei(7372)
        if "メトロノーム6発目" in state_names:
            damage_hoseichi.hosei(8192)
    if attacker_item_name == "たつじんのおび" and move_type_damgage_multiplier >= 2:
        damage_hoseichi.hosei(4915)
    if attacker_item_name == "いのちのたま":
        damage_hoseichi.hosei(5324)
    if (defender_item_name == "半減実" and move_type_damgage_multiplier >= 2
        or defender_item_name == "ノーマル半減実" and move_type_name == "normal"):
        damage_hoseichi.hosei(2048)
    if "ちいさくなる" in state_names and move_name in ['stomp', 'steamroller', 'dragon-rush', 'heat-crash', 'flying-press', 'body-slam', 'heavy-slam']:
        damage_hoseichi.hosei(8192)
    if "あなをほる" in state_names and move_name in ['earthquake', 'magnitude']:
        damage_hoseichi.hosei(8192)
    if "ダイビング" in state_names and move_name == "surf":
        damage_hoseichi.hosei(8192)

    final_damage = math.floor(attacker.level * 2 / 5 + 2)
    final_damage = math.floor(final_damage * final_iryoku * final_attack / final_defense)
    final_damage = math.floor(final_damage / 50 + 2)
    final_damage_calc = FinalDamageCalc(final_damage)
    if "ダブルバトル" in state_names and move.target in ["all-other-pokemon", "all-opponents"]:
        final_damage_calc.hosei(3072)
    if ("にほんばれ" in state_names and move_type_name == "water"
        or "あめ" in state_names and move_type_name == "fire"):
        final_damage_calc.hosei(2048)
    if ("にほんばれ" in state_names and move_type_name == "fire"
        or "あめ" in state_names and move_type_name == "water"):
        final_damage_calc.hosei(6144)
    if "きょけんとつげき後" in state_names:
        final_damage_calc.hosei(8192)
    if "きゅうしょ" in state_names:
        final_damage_calc.hosei(6144)
    final_damage_calc.ransuu()
    if attacker_ability_name != "adaptability":
        if attacker.terasu_type is None:
            if move_type_name in attacker_type_names:
                # テラスなしタイプ一致
                final_damage_calc.hosei(6144)
        elif attacker.terasu_type == "stellar":
            # ステラ補正はテラパゴス以外タイプごとに1度のみ。2度目以降はテラスタルなしと同じ
            if move_type_name in attacker_type_names:
                # ステラタイプ一致
                final_damage_calc.hosei(8192)
            else:
                # ステラタイプ不一致
                # ステラタイプ技=ステラテラスのテラバースト/テラクラスター に対して元タイプがステラのポケモンは存在しない（ステラパゴスも）ので、結果的にこちらに該当する。
                final_damage_calc.hosei(4915)
        else:
            if move_type_name == attacker.terasu_type.data.name and move_type_name in attacker.pokemon.data.type_names:
                # 技のタイプがテラスタイプかつ元のタイプに含まれる
                final_damage_calc.hosei(8192)
            elif move_type_name == attacker.terasu_type.data.name and move_type_name not in attacker.pokemon.data.type_names:
                # 技のタイプがテラスタイプだが元のタイプに含まれない
                final_damage_calc.hosei(6144)
            elif move_type_name != attacker.terasu_type.data.name and move_type_name in attacker.pokemon.data.type_names:
                # 技のタイプがテラスタイプではないが元のタイプに含まれる
                final_damage_calc.hosei(6144)
    else: # てきおうりょく
        if attacker.terasu_type is None:
            if move_type_name in attacker_type_names:
                # テラスなしタイプ一致
                final_damage_calc.hosei(8192)
        elif attacker.terasu_type == "stellar":
            # てきおうりょく+ステラはてきおうりょくではない場合と全く同じ。2度目以降は**てきおうりょくなしと同じ**
            if move_type_name in attacker_type_names:
                # ステラタイプ一致
                final_damage_calc.hosei(8192)
            else:
                # ステラタイプ不一致
                final_damage_calc.hosei(4915)
        else:
            # テラス+てきおうりょくは、テラス後のタイプと技のタイプが一致するときに、ダメージがてきおうりょくではない場合よりもふえる。逆にテラス前のタイプにはてきおうりょく補正はかからなくなるが、通常のタイプ一致補正はある。
            if move_type_name == attacker.terasu_type.data.name and move_type_name in attacker.pokemon.data.type_names:
                # 技のタイプがテラスタイプかつ元のタイプに含まれる
                final_damage_calc.hosei(9216)
            elif move_type_name == attacker.terasu_type.data.name and move_type_name not in attacker.pokemon.data.type_names:
                # 技のタイプがテラスタイプだが元のタイプに含まれない
                final_damage_calc.hosei(8192)
            elif move_type_name != attacker.terasu_type.data.name and move_type_name in attacker.pokemon.data.type_names:
                # 技のタイプがテラスタイプではないが元のタイプに含まれる
                final_damage_calc.hosei(6144)
    final_damage_calc.damage = [math.floor(d * move_type_damgage_multiplier) for d in final_damage_calc.get_damages()]
    if "やけど" in state_names and move_damage_class == "physical" and attacker_ability_name != "guts" and move_name != "facade":
        final_damage_calc.hosei(2048)
    final_damage_calc.hosei(damage_hoseichi.hoseichi)
    final_damages = final_damage_calc.damage
    if move_type_damgage_multiplier != 0:
        final_damages = [
            1 if damage < 1 else damage
            for damage in final_damages
        ]


    defender_hp_doryokuchi = input.hp_doryokuchi if defender.all_doryokuchi is None else defender.all_doryokuchi.h
    defender_hp_kotaichi = input.hp_kotaichi if defender.all_kotaichi is None else defender.all_kotaichi.h
    defender_hp = calc_hp(defender.pokemon.data.stats.h, defender_hp_doryokuchi, defender_hp_kotaichi, defender.level)
    return Output(Damage(final_damages), attacker_attack, attacker_doryokuchi, attacker_kotaichi, attacker_seikaku_hosei, defender_defense, defender_doryokuchi, defender_kotaichi, defender_seikaku_hosei, defender_hp, defender_hp_doryokuchi, defender_hp_kotaichi, input)

# fmt: on


def rank_multiplier(rank: int) -> float:
    if rank >= 0:
        return (2 + rank) / 2
    else:
        return 2 / (2 - rank)


def is_punch(move: Move) -> bool:
    return move.name in [
        "mega-punch",
        "fire-punch",
        "ice-punch",
        "thunder-punch",
        "dizzy-punch",
        "mach-punch",
        "dynamic-punch",
        "focus-punch",
        "meteor-mash",
        "shadow-punch",
        "hammer-arm",
        "ice-hammer",
        "bullet-punch",
        "drain-punch",
        "plasma-fists",
        "wicked-blow",
        "surging-strikes",
    ]


def is_handou(move: Move) -> bool:
    return move.name in [
        "double-edge",
        "wood-hammer",
        "brave-bird",
        "take-down",
        "submission",
        "volt-tackle",
        "flare-blitz",
        "head-smash",
        "high-jump-kick",
        "head-charge",
        "wild-charge",
    ]


def is_chokusetsu(move: Move) -> bool:
    # https://wiki.xn--rckteqa2e.com/wiki/%E7%9B%B4%E6%8E%A5%E6%94%BB%E6%92%83
    return (
        move.damage_class == "physical"
        and move.name
        not in [
            "triple-arrows",
            "grav-apple",
            "aqua-cutter",
            "hyperspace-fury",
            "order-up",
            "rock-throw",
            "rock-slide",
            "smack-down",
            "aura-wheel",
            "last-respects",
            "pyro-ball",
            "spirit-shackle",
            "rock-tomb",
            "rock-wrecker",
            "lands-wrath",
            "fusion-bolt",
            "attack-order",
            "ice-shard",
            "sky-attack",
            "leafage",
            "psycho-cut",
            "thousand-arrows",
            "thousand-waves",
            "salt-cure",
            "earthquake",
            "natural-gift",
            "bulldoze",
            "self-destruct",
            "shadow-bone",
            "fissure",
            "scale-shot",
            "meteor-assault",
            "stone-edge",
            "sand-tomb",
            "sacred-fire",
            "wicked-torque",
            "explosion",
            "raging-fury",
            "diamond-storm",
            "gunk-shot",
            "seed-bomb",
            "bullet-seed",
            "twineedle",
            "egg-bomb",
            "barrage",
            "precipice-blades",
            "ivy-cudgel",
            "icicle-crash",
            "icicle-spear",
            "gigaton-hammer",
            "tera-starstorm",
            "tera-blast",
            "poison-sting",
            "barb-barrage",
            "spike-cannon",
            "dragon-darts",
            "drum-beating",
            "flower-trick",
            "fling",
            "pay-day",
            "blazing-torque",
            "razor-leaf",
            "petal-blizzard",
            "secret-power",
            "mountain-gale",
            "combat-torque",
            "feint",
            "photon-geyser",
            "beat-up",
            "freeze-shock",
            "glacial-lance",
            "present",
            "bone-rush",
            "noxious-torque",
            "poltergeist",
            "bone-club",
            "bonemerang",
            "magical-torque",
            "magnitude",
            "magnet-bomb",
            "pin-missile",
            "metal-burst",
            "rock-blast",
        ]
    ) or (
        move.damage_class == "special"
        and move.name
        in ["electro-drift", "trump-card", "grass-knot", "wring-out", "draining-kiss", "petal-dance", "infestation"]
    )


def is_oto(move: Move) -> bool:
    return move.name in [
        "relic-song",
        "snore",
        "heal-bell",
        "screech",
        "sing",
        "sparkling-aria",
        "echoed-voice",
        "overdrive",
        "chatter",
        "noble-roar",
        "metal-sound",
        "grass-whistle",
        "psychic-noise",
        "uproar",
        "clanging-scales",
        "parting-shot",
        "clangorous-soul",
        "shadow-panic",
        "disarming-voice",
        "supersonic",
        "howl",
        "confide",
        "growl",
        "snarl",
        "hyper-voice",
        "boomburst",
        "eerie-spell",
        "torch-song",
        "clangorous-soulblaze",
        "roar",
        "perish-song",
        "alluring-voice",
        "bug-buzz",
        "round",
    ]


def is_chikarazuku_applicable(move: Move) -> bool:
    return move.name in [
        "poison-sting",
        "smog",
        "poison-tail",
        "cross-poison",
        "sludge",
        "poison-jab",
        "sludge-bomb",
        "shell-side-arm",
        "sludge-wave",
        "gunk-shot",
        "poison-fang",
        "ember",
        "flame-wheel",
        "fire-punch",
        "burning-jealousy",
        "lava-plume",
        "blaze-kick",
        "flamethrower",
        "heat-wave",
        "inferno",
        "sacred-fire",
        "searing-shot",
        "fire-blast",
        "flare-blitz",
        "blue-flare",
        "scald",
        "steam-eruption",
        "ice-burn",
        "scorching-sands",
        "powder-snow",
        "ice-punch",
        "freeze-dry",
        "ice-beam",
        "blizzard",
        "freezing-glare",
        "body-slam",
        "nuzzle",
        "thunder-shock",
        "spark",
        "thunder-punch",
        "discharge",
        "thunderbolt",
        "thunder",
        "zap-cannon",
        "volt-tackle",
        "bolt-strike",
        "freeze-shock",
        "force-palm",
        "bounce",
        "lick",
        "dragon-breath",
        "tri-attack",
        "water-pulse",
        "dynamic-punch",
        "chatter",
        "hurricane",
        "confusion",
        "psybeam",
        "strange-steam",
        "fake-out",
        "snore",
        "stomp",
        "headbutt",
        "waterfall",
        "zing-zap",
        "icicle-crash",
        "air-slash",
        "sky-attack",
        "heart-stamp",
        "zen-headbutt",
        "extrasensory",
        "rock-slide",
        "astonish",
        "twister",
        "dragon-rush",
        "bite",
        "dark-pulse",
        "fiery-wrath",
        "double-iron-bash",
        "iron-head",
        "fire-fang",
        "thunder-fang",
        "ice-fang",
        "trop-kick",
        "aurora-beam",
        "lunge",
        "breaking-swipe",
        "play-rough",
        "crush-claw",
        "fire-lash",
        "razor-shell",
        "liquidation",
        "grav-apple",
        "rock-smash",
        "thunderous-kick",
        "shadow-bone",
        "crunch",
        "iron-tail",
        "mystical-fire",
        "mist-ball",
        "struggle-bug",
        "skitter-smack",
        "snarl",
        "spirit-break",
        "moonblast",
        "energy-ball",
        "seed-flare",
        "apple-acid",
        "focus-blast",
        "acid",
        "acid-spray",
        "earth-power",
        "luster-purge",
        "psychic",
        "bug-buzz",
        "shadow-ball",
        "flash-cannon",
        "bubble-beam",
        "electroweb",
        "drum-beating",
        "icy-wind",
        "glaciate",
        "low-sweep",
        "mud-shot",
        "bulldoze",
        "rock-tomb",
        "octazooka",
        "muddy-water",
        "leaf-tornado",
        "mud-slap",
        "night-daze",
        "power-up-punch",
        "metal-claw",
        "meteor-mash",
        "diamond-storm",
        "steel-wing",
        "fiery-dance",
        "charge-beam",
        "rapid-spin",
        "flame-charge",
        "aura-wheel",
        "ancient-power",
        "secret-power",
        "spirit-shackle",
        "anchor-shot",
        "throat-chop",
        "sparkling-aria",
        "eerie-spell",
    ]


def is_cutting(move: Move) -> bool:
    return move.name in [
        "aqua-cutter",
        "cut",
        "air-cutter",
        "air-slash",
        "stone-axe",
        "behemoth-blade",
        "slash",
        "cross-poison",
        "psycho-cut",
        "psyblade",
        "razor-shell",
        "x-scissor",
        "secret-sword",
        "sacred-sword",
        "solar-blade",
        "tachyon-cutter",
        "night-slash",
        "aerial-ace",
        "kowtow-cleave",
        "population-bomb",
        "razor-leaf",
        "mighty-cleave",
        "ceaseless-edge",
        "bitter-blade",
        "leaf-blade",
        "fury-cutter",
    ]


def is_kamitsuki(move: Move) -> bool:
    return move.name in [
        "fishious-rend",
        "crunch",
        "bite",
        "thunder-fang",
        "jaw-lock",
        "ice-fang",
        "psychic-fangs",
        "poison-fang",
        "hyper-fang",
        "fire-fang",
    ]


def is_hadou(move: Move) -> bool:
    return move.name in ["dark-pulse", "origin-pulse", "terrain-pulse", "aura-sphere", "water-pulse", "dragon-pulse"]


@dataclass
class Hoseichi:
    hoseichi: int = 4096

    def hosei(self, value) -> None:
        self.hoseichi = round_5_to_up(self.hoseichi * value / 4096)


@dataclass
class FinalDamageCalc:
    damage: int | list[int]

    def hosei(self, value: int) -> None:
        if isinstance(self.damage, int):
            self.damage = round_5_to_down(self.damage * value / 4096)
        else:
            self.damage = [round_5_to_down(damage * value / 4096) for damage in self.damage]

    def ransuu(self) -> None:
        if isinstance(self.damage, int):
            self.damage = [math.floor(self.damage * r / 100) for r in range(85, 101)]
        else:
            raise Exception

    def get_damages(self) -> list[int]:
        if isinstance(self.damage, int):
            raise Exception
        else:
            return self.damage


def round_5_to_up(x) -> int:
    floor_x = math.floor(x)
    if x - floor_x < 0.5:
        return floor_x
    else:
        return floor_x + 1


def round_5_to_down(x) -> int:
    floor_x = math.floor(x)
    if x - floor_x <= 0.5:
        return floor_x
    else:
        return floor_x + 1


def main(input_filepaths: InputFilepaths) -> None:
    all_data = pokemon_data.load_all_data(
        input_filepaths.pokeapi_filepaths,
        input_filepaths.names_filepaths,
        pokemon_data.JpToRomaji(input_filepaths.replacement_filepath),
    )
    while True:
        try:
            inputs = input_processor.get_inputs_to_calculate(all_data, input_filepaths.preset_filepath)
            if inputs is None:
                continue
        except input_processor.InvalidInput as e:
            print(e)
            continue
        outputs = [calc_damage(e, all_data) for e in inputs]
        print(outputs[0].header_str())
        for output in outputs:
            print(output.to_str())
            print(output.hp_bar_str())


if __name__ == "__main__":
    main(default_input_filepaths)
