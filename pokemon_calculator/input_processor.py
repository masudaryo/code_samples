from typing import Iterable
import sys
from os import PathLike
import jsonc

import pokemon_data
from pokemon_data import NameExtended, AllData, Stats
from pokemon_calc import InputArgs, Input


class InvalidInput(Exception):
    pass


def get_input(prompt_str: str = ">>>") -> str:
    input_str = input(prompt_str)
    if input_str == "e":
        sys.exit()
    return input_str


def retrieve_one_data[T](
    data_dict: dict[str, NameExtended[T]], query: str, restriction: Iterable[str] | None = None
) -> NameExtended[T]:
    if restriction is not None:
        data_dict_to_retrieve = {name: data_dict[name] for name in restriction if name in data_dict}
    else:
        data_dict_to_retrieve = data_dict
    result = pokemon_data.retrieve_data(data_dict_to_retrieve, query)
    length = len(result)
    if length == 0:
        raise InvalidInput(f"Invalid input: {query}")
    if length == 1:
        return result[0]

    if length == 2:
        keys = ("f", "j")
    elif length == 3:
        keys = ("d", "f", "j")
    elif length == 4:
        keys = ("d", "f", "j", "k")
    elif length == 5:
        keys = ("j", "d", "f", "j", "k")
    elif length == 6:
        keys = ("j", "d", "f", "j", "k", "l")
    elif length == 7:
        keys = ("a", "j", "d", "f", "j", "k", "l")
    elif length == 8:
        keys = ("a", "j", "d", "f", "j", "k", "l", ";")
    elif length > 8:
        keys = list(map(str, range(1, length + 1)))

    candidate_dict = {key: data for key, data in zip(keys, result, strict=True)}
    print(*(f"{key}: {data.display_name}" for key, data in candidate_dict.items()))
    while (s := get_input()) not in candidate_dict:
        print(f"Invalid input: {s}")
    return candidate_dict[s]


def _parse_input_str(input_str: str, preset_filepath: PathLike | str) -> dict:
    input_words = input_str.split()
    output_dict = {"a_pokemon": None, "b_pokemon": None, "a": {}, "b": {}, "j": [], "save": None, "del": None}
    # state "a" 中に入力されたone_word_optionは output_dict["a"][option_str] = value になる。no_word_optionは output_dict["a"][option_str] = True になる。state "b" も同様。state "j"で入力されたものは output_dict["j"] にappendされる。
    one_word_options = ["to", "tox", "d", "k", "s", "m", "r", "t", "l", "w", "wx", "h", "hk", "d6", "k6", "seikaku"]
    no_word_options = [
        "akyoku",
        "ckyoku",
        "atokka",
        "ctokka",
        "bkyoku",
        "dkyoku",
        "btokka",
        "dtokka",
        "hb",
        "hd",
        "hkyoku",
        "amuburi",
        "cmuburi",
        "bmuburi",
        "dmuburi",
    ]
    state_options = ["a", "b", "j", "save", "del"]
    special_option = ["p"]
    all_options = one_word_options + no_word_options + state_options + special_option
    i = 0
    current_state = "a"
    previous_state = "a"  # "j"から戻るときに使う
    while i < len(input_words):
        if input_words[i] == "p":
            input_words = (
                input_words[:i] + get_preset(input_words[i + 1], preset_filepath).split() + input_words[i + 2 :]
            )
            i -= 1  # "p"があった場所をもう一度見る
        elif input_words[i] in state_options:
            previous_state = current_state
            current_state = input_words[i]
        elif current_state == "a" and output_dict["a_pokemon"] is None:
            output_dict["a_pokemon"] = input_words[i]
        elif current_state == "b" and output_dict["b_pokemon"] is None:
            output_dict["b_pokemon"] = input_words[i]
        elif current_state == "a" and input_words[i] not in all_options:
            output_dict["b_pokemon"] = input_words[i]
            previous_state = current_state
            current_state = "b"
        elif current_state == "save":
            output_dict["save"] = (input_words[i], " ".join(input_words[i + 1 :]))
            return output_dict
        elif current_state == "del":
            output_dict["del"] = input_words[i]
            return output_dict
        elif input_words[i] in one_word_options:
            if current_state == "j":
                current_state = previous_state
            output_dict[current_state][input_words[i]] = input_words[i + 1]
            i += 1
        elif input_words[i] in no_word_options:
            if current_state == "j":
                current_state = previous_state
            output_dict[current_state][input_words[i]] = True
        elif current_state == "j" and input_words[i] not in all_options:
            output_dict["j"].append(input_words[i])
        else:
            raise InvalidInput(f"Invalid input: {input_words[i]}")
        i += 1
    if output_dict["a_pokemon"] is None or output_dict["b_pokemon"] is None:
        raise InvalidInput("Invalid input: attacekr or defender not specified")
    return output_dict


def _make_input_args_from_str(input_str: str, all_data: AllData, preset_filepath: PathLike | str) -> InputArgs | None:
    input_args = InputArgs()
    options_dict = _parse_input_str(input_str, preset_filepath)
    if options_dict["save"] is not None:
        add_preset(options_dict["save"][0], options_dict["save"][1], preset_filepath)
        return None
    if options_dict["del"] is not None:
        delete_preset(options_dict["del"], preset_filepath)
        return None
    input_args.attacker.pokemon = retrieve_one_data(all_data.pokemons, options_dict["a_pokemon"])
    input_args.defender.pokemon = retrieve_one_data(all_data.pokemons, options_dict["b_pokemon"])
    for key, battle_pokemon in zip(["a", "b"], [input_args.attacker, input_args.defender]):
        assert battle_pokemon.pokemon is not None
        for option, value in options_dict[key].items():
            if option == "to":
                battle_pokemon.ability = retrieve_one_data(
                    all_data.abilities, value, battle_pokemon.pokemon.data.ability_names
                )
            elif option == "tox":
                battle_pokemon.ability = retrieve_one_data(all_data.abilities, value)
            elif option == "d":
                if value == "m":
                    battle_pokemon.doryokuchi = 252
                else:
                    battle_pokemon.doryokuchi = int(value)
            elif option == "k":
                battle_pokemon.kotaichi = int(value)
            elif option == "s":
                if value == "a":
                    battle_pokemon.seikaku_hosei = 1.1
                elif value == "n":
                    battle_pokemon.seikaku_hosei = 1
                elif value == "k":
                    battle_pokemon.seikaku_hosei = 0.9
                else:
                    raise InvalidInput(f"Invalid input: {value}")
            elif option == "m":
                battle_pokemon.item = retrieve_one_data(all_data.items, value)
            elif option == "r":
                battle_pokemon.rank = int(value)
            elif option == "t":
                battle_pokemon.terasu_type = retrieve_one_data(all_data.types, value)
            elif option == "l":
                battle_pokemon.level = int(value)
            elif option == "w":
                input_args.move = retrieve_one_data(all_data.moves, value, input_args.attacker.pokemon.data.move_names)
            elif option == "wx":
                input_args.move = retrieve_one_data(all_data.moves, value)
            elif option == "h":
                input_args.hp_doryokuchi = int(value)
            elif option == "hk":
                input_args.hp_kotaichi = int(value)
            elif option in ["akyoku", "ckyoku"]:
                input_args.attacker.doryokuchi = 252
                input_args.attacker.seikaku_hosei = 1
            elif option in ["atokka", "ctokka"]:
                input_args.attacker.doryokuchi = 252
                input_args.attacker.seikaku_hosei = 1.1
            elif option in ["amuburi", "cmuburi"]:
                input_args.attacker.doryokuchi = 0
                input_args.attacker.seikaku_hosei = 1
            elif option in ["bkyoku", "dkyoku"]:
                input_args.defender.doryokuchi = 252
                input_args.defender.seikaku_hosei = 1
                input_args.hp_doryokuchi = 0
            elif option in ["btokka", "dtokka"]:
                input_args.defender.doryokuchi = 252
                input_args.defender.seikaku_hosei = 1.1
                input_args.hp_doryokuchi = 0
            elif option in ["hb", "hd"]:
                input_args.defender.doryokuchi = 252
                input_args.defender.seikaku_hosei = 1.1
                input_args.hp_doryokuchi = 252
            elif option == "hkyoku":
                input_args.defender.doryokuchi = 0
                input_args.defender.seikaku_hosei = 1
                input_args.hp_doryokuchi = 252
            elif option in ["bmuburi", "dmuburi"]:
                input_args.defender.doryokuchi = 0
                input_args.defender.seikaku_hosei = 1
                input_args.hp_doryokuchi = 0
            elif option == "d6":
                if len(temp := value.split("-")) != 6:
                    raise InvalidInput("Invalid input: {value}")
                battle_pokemon.all_doryokuchi = Stats(*map(int, temp))
                battle_pokemon.doryokuchi = 0  # あとの処理で無入力とされないように0にしておく
                if key == "b":
                    input_args.hp_doryokuchi = 0
            elif option == "k6":
                if len(temp := value.split("-")) != 6:
                    raise InvalidInput("Invalid input: {value}")
                battle_pokemon.all_kotaichi = Stats(*map(int, temp))
            elif option == "seikaku":
                if len(temp := value.split("-")) != 2:
                    raise InvalidInput("Invalid input: {value}")
                battle_pokemon.seikaku_hosei_up_down = tuple(temp)

    for value in options_dict["j"]:
        input_args.states.append(retrieve_one_data(all_data.states, value))

    return input_args


def add_preset(preset_key: str, preset_value: str, preset_filepath: PathLike | str) -> None:
    preset = load_preset(preset_filepath)
    preset[preset_key] = preset_value
    with open(preset_filepath, encoding="utf-8", mode="w") as f:
        jsonc.dump(preset, f, ensure_ascii=False, indent=4)
    print(f"save preset: {preset_key}: {preset_value}")


def delete_preset(input_word: str, preset_filepath: PathLike | str) -> None:
    preset = load_preset(preset_filepath)
    if len(key := retrieve_preset(preset, input_word)) != 1:
        raise InvalidInput(f"Invalid input: {preset}")
    print(f"delete preset: {key[0]}: {preset[key[0]]}")
    del preset[key[0]]


def retrieve_one_preset(preset: dict[str, str], input_word: str) -> str:
    if len(keys := retrieve_preset(preset, input_word)) != 1:
        raise InvalidInput(f"Invalid input: {preset}")
    return preset[keys[0]]


def retrieve_preset(preset: dict[str, str], input_str: str) -> list[str]:
    return [key for key in preset if key.startswith(input_str)]


def load_preset(preset_filepath: PathLike | str) -> dict[str, str]:
    with open(preset_filepath, encoding="utf-8") as f:
        return jsonc.load(f)


def get_preset(input_word: str, preset_filepath: PathLike | str) -> str:
    preset = load_preset(preset_filepath)
    return retrieve_one_preset(preset, input_word)


def _process_specific_settings(input_args_list: list[InputArgs], all_data: AllData) -> list[InputArgs]:
    processed_input_args_list: list[InputArgs] = []
    for input_args in input_args_list:
        for battle_pokemon_args in [input_args.attacker, input_args.defender]:
            assert battle_pokemon_args.pokemon is not None
            if battle_pokemon_args.pokemon.data.name == "terapagos-stellar":
                battle_pokemon_args.terasu_type = all_data.types["stellar"]
            elif battle_pokemon_args.pokemon.data.name == "zacian-crowned":
                battle_pokemon_args.item = all_data.items["もちもの指定なし"]
            elif battle_pokemon_args.pokemon.data.name == "zamazenta-crowned":
                battle_pokemon_args.item = all_data.items["もちもの指定なし"]
            elif battle_pokemon_args.pokemon.data.name in [
                "ogerpon-wellspring-mask",
                "ogerpon-hearthflame-mask",
                "ogerpon-cornerstone-mask",
            ]:
                battle_pokemon_args.item = all_data.items["オーガポン仮面"]
        processed_input_args_list.append(input_args)
    return processed_input_args_list


def _process_ability(input_args_list: list[InputArgs], all_data: AllData) -> list[InputArgs]:
    preffered_ability_names: list[str] = [
        "multiscale",
        "galvanize",
        "pixilate",
        "iron-fist",
        "reckless",
        "supreme-overlord",
        "sheer-force",
        "tough-claws",
        "technician",
        "guts",
        "huge-power",
        "pure-power",
        "water-bubble",
        "purifying-salt",
        "tinted-lens",
        "solid-rock",
        "filter",
        "adaptability",
        "regenerator",
        "unaware",
    ]
    # "マルチスケイル", "エレキスキン", "フェアリースキン", "てつのこぶし", "すてみ", "そうだいしょう", "ちからずく", "かたいツメ", "テクニシャン", "こんじょう", "ちからもち", "ヨガパワー", "すいほう", "きよめのしお", "いろめがね", "ハードロック", "フィルター", "てきおうりょく", "さいせいりょく", "てんねん"
    # このリストが優先度の高い順になる
    processed_input_args_list: list[InputArgs] = []
    for input_args in input_args_list:
        for battle_pokemon_args in (input_args.attacker, input_args.defender):
            assert battle_pokemon_args.pokemon is not None
            if battle_pokemon_args.ability is None:
                for preffered_ability_name in preffered_ability_names:
                    if preffered_ability_name in battle_pokemon_args.pokemon.data.ability_names:
                        battle_pokemon_args.ability = all_data.abilities[preffered_ability_name]
                        break
                else:
                    battle_pokemon_args.ability = all_data.abilities[battle_pokemon_args.pokemon.data.ability_names[0]]
        processed_input_args_list.append(input_args)
    return processed_input_args_list


def _process_attacker_nouryokuchi(input_args_list: list[InputArgs], all_data: AllData) -> list[InputArgs]:
    processed_input_args_list: list[InputArgs] = []
    for input_args in input_args_list:
        if input_args.attacker.doryokuchi is None:
            if input_args.attacker.item is None:
                new_args = input_args.copy()
                new_args.attacker.doryokuchi = 252
                new_args.attacker.kotaichi = 31
                new_args.attacker.seikaku_hosei = 1.1
                new_args.attacker.item = all_data.items["こだわり"]
                processed_input_args_list.append(new_args)

                new_args = input_args.copy()
                new_args.attacker.doryokuchi = 252
                new_args.attacker.kotaichi = 31
                new_args.attacker.seikaku_hosei = 1.1
                new_args.attacker.item = all_data.items["1.2倍アイテム"]
                processed_input_args_list.append(new_args)

            new_args = input_args.copy()
            new_args.attacker.doryokuchi = 252
            new_args.attacker.kotaichi = 31
            new_args.attacker.seikaku_hosei = 1.1
            processed_input_args_list.append(new_args)

            new_args = input_args.copy()
            new_args.attacker.doryokuchi = 252
            new_args.attacker.kotaichi = 31
            new_args.attacker.seikaku_hosei = 1
            processed_input_args_list.append(new_args)

            new_args = input_args.copy()
            new_args.attacker.doryokuchi = 0
            new_args.attacker.kotaichi = 31
            new_args.attacker.seikaku_hosei = 1
            processed_input_args_list.append(new_args)
        else:
            processed_input_args_list.append(input_args)
    return processed_input_args_list


def _process_defender_nouryokuchi(input_args_list: list[InputArgs], all_data: AllData) -> list[InputArgs]:
    processed_input_args_list: list[InputArgs] = []
    for input_args in input_args_list:
        if input_args.defender.doryokuchi is None:
            new_args = input_args.copy()
            new_args.defender.doryokuchi = 0
            new_args.defender.kotaichi = 31
            new_args.defender.seikaku_hosei = 1
            new_args.hp_doryokuchi = 0
            new_args.hp_kotaichi = 31
            processed_input_args_list.append(new_args)

            new_args = input_args.copy()
            new_args.defender.doryokuchi = 0
            new_args.defender.kotaichi = 31
            new_args.defender.seikaku_hosei = 1
            new_args.hp_doryokuchi = 252
            new_args.hp_kotaichi = 31
            processed_input_args_list.append(new_args)

            new_args = input_args.copy()
            new_args.defender.doryokuchi = 252
            new_args.defender.kotaichi = 31
            new_args.defender.seikaku_hosei = 1.1
            new_args.hp_doryokuchi = 0
            new_args.hp_kotaichi = 31
            processed_input_args_list.append(new_args)

            new_args = input_args.copy()
            new_args.defender.doryokuchi = 252
            new_args.defender.kotaichi = 31
            new_args.defender.seikaku_hosei = 1.1
            new_args.hp_doryokuchi = 252
            new_args.hp_kotaichi = 31
            processed_input_args_list.append(new_args)

            assert input_args.move is not None
            if input_args.defender.item is None and input_args.move.data.damage_class == "special":
                new_args = input_args.copy()
                new_args.defender.doryokuchi = 252
                new_args.defender.kotaichi = 31
                new_args.defender.seikaku_hosei = 1.1
                new_args.defender.item = all_data.items["とつげきチョッキ"]
                new_args.hp_doryokuchi = 252
                new_args.hp_kotaichi = 31
                processed_input_args_list.append(new_args)
        else:
            processed_input_args_list.append(input_args)
    return processed_input_args_list


def check_args_set(input_args: InputArgs) -> InputArgs:
    # InputArgs.make_input(), BattlePokemonArgs.make_battle_pokemon()でエラーが出る状態であるとき、ここでInvalidInputを出して再入力させる
    if input_args.move is None:
        raise InvalidInput("no move")
    if input_args.hp_doryokuchi is None:
        raise InvalidInput("no hp doryokuchi")
    if input_args.attacker.pokemon is None:
        raise InvalidInput("no attacker")
    if input_args.attacker.ability is None:
        raise InvalidInput("no attacker ability")
    if input_args.attacker.doryokuchi is None:
        raise InvalidInput("no attacker doryokuchi")
    if input_args.defender.pokemon is None:
        raise InvalidInput("no defender")
    if input_args.defender.ability is None:
        raise InvalidInput("no defender ability")
    if input_args.defender.doryokuchi is None:
        raise InvalidInput("no defender doryokuchi")
    return input_args


def get_inputs_to_calculate(all_data: AllData, preset_filepath: PathLike | str) -> list[Input] | None:
    """入力が"save"や"del"などのコマンドのとき、Noneを返す。"""
    input_str = get_input()
    input_args = _make_input_args_from_str(input_str, all_data, preset_filepath)
    if input_args is None:
        return None
    if input_args.attacker is None:
        raise InvalidInput("no attacker")
    if input_args.defender is None:
        raise InvalidInput("no defender")
    if input_args.move is None:
        raise InvalidInput("no move")
    input_args_list: list[InputArgs] = [input_args]
    input_args_list = _process_specific_settings(input_args_list, all_data)
    input_args_list = _process_ability(input_args_list, all_data)
    input_args_list = _process_attacker_nouryokuchi(input_args_list, all_data)
    input_args_list = _process_defender_nouryokuchi(input_args_list, all_data)
    return [check_args_set(input_args).make_input() for input_args in input_args_list]
