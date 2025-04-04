import os
import json
import pokebase
from os import PathLike

from input_filepaths import default_input_filepaths

# https://pokeapi.co/docs/v2#<typename("_"無し)> で各型のドキュメントにジャンプ

# PokemonSpecies: 図鑑ナンバーによる分類
# Pokemon: 種族値/技等が異なる形態
# PokemonForm: それ以下のフォルム。アルセウスのタイプ変化など、タイプの変更を含む場合がある。

# NamedAPIResource (Pokemon) などは、pokebaseの出力ではPokemonと同じメンバをもつオブジェクトとして使える。nameとurlはapiアクセス無しで読み出せて、他のメンバはapiアクセスして読み出すと思われる。（ただしAPIResourceListでイテレートできる対象は、NamedAPIResourceではなく、nameとidのみ取り出せる）

def download_pokemon_species(pokemon_species_name) -> dict:
    pokemon_species = pokebase.pokemon_species(pokemon_species_name)
    return {
        "id": pokemon_species.id,
        "name": pokemon_species.name,
        "order": pokemon_species.order,
        "jp_name": get_jp_name(pokemon_species.names),
        "varieties": list(map(pokemon_species_variety_dict, pokemon_species.varieties))
    }

def download_move(move_name) -> dict:
    move = pokebase.move(move_name)
    return {
        "id": move.id,
        "name": move.name,
        "accuracy": move.accuracy,
        "power": move.power,
        "damage_class.name": move.damage_class.name,
        "meta": move_meta_data_dict(move.meta) if move.meta is not None else None, # SV世代の技(id 827~)にはMoveMetaDataが実装されておらず、move.metaはNone。
        "jp_name": get_jp_name(move.names),
        "target.name": move.target.name,
        "type.name": move.type.name
    }

def download_type(type_name) -> dict:
    type_ = pokebase.type_(type_name)
    return {
        "id": type_.id,
        "name": type_.name,
        "damage_relations": type_relations_dict(type_.damage_relations),
        "jp_name": get_jp_name(type_.names)
    }

def download_ability(ability_name) -> dict:
    ability = pokebase.ability(ability_name)
    return {
        "id": ability.id,
        "name": ability.name,
        "jp_name": get_jp_name(ability.names)
    }

def pokemon_species_variety_dict(pokemon_species_variety) -> dict:
    return {
        "pokemon": pokemon_dict(pokemon_species_variety.pokemon)
    }

def pokemon_dict(pokemon) -> dict:
    return {
        "id": pokemon.id,
        "name": pokemon.name,
        "order": pokemon.order,
        "abilities": list(map(pokemon_ability_dict, pokemon.abilities)),
        "forms": list(map(pokemon_form_dict, pokemon.forms)),
        "moves": list(map(pokemon_move_dict, pokemon.moves)),
        "stats": list(map(pokemon_stat_dict, pokemon.stats)),
        "types": list(map(pokemon_type_dict, pokemon.types)),
    }

def pokemon_ability_dict(pokemon_ability) -> dict:
    return {
        "slot": pokemon_ability.slot,
        "ability.name": pokemon_ability.ability.name
    }

def pokemon_form_dict(pokemon_form) -> dict:
    return {
        "id": pokemon_form.id,
        "name": pokemon_form.name, # e.g. terapagos-terastal
        "order": pokemon_form.order,
        "form_order": pokemon_form.form_order,
        "form_name": pokemon_form.form_name, # PokeAPI上でこのformに付けられたname。nameの-以降（"デフォルト形態"のようなものには-が付かず、from_nameは空文字列） e.g. terastal
        "types": list(map(pokemon_form_type_dict, pokemon_form.types)),
        "jp_name": get_jp_name(pokemon_form.names), # 通常None。イワンコ（マイペース）のみ（おそらく誤って）ここに書かれている。
        "jp_form_name": get_jp_name(pokemon_form.form_names) # このformのゲーム上の名称の日本語名 e.g. テラスタルフォルム
    }

def pokemon_form_type_dict(pokemon_form_type) -> dict:
    return {
        "slot": pokemon_form_type.slot,
        "type.name": pokemon_form_type.type.name
    }

def pokemon_move_dict(pokemon_move) -> dict:
    return {
        "move.name": pokemon_move.move.name
    }

def pokemon_stat_dict(pokemon_stat) -> dict:
    return {
        "stat.name": pokemon_stat.stat.name,
        "base_stat": pokemon_stat.base_stat
    }


def pokemon_type_dict(pokemon_type) -> dict:
    return {
        "slot": pokemon_type.slot,
        "type.name": pokemon_type.type.name
    }

def move_meta_data_dict(move_meta_data) -> dict:
    # categoryはdamageとかailmentとかで意味がないので不要。
    return {
        "min_hits": move_meta_data.min_hits,
        "max_hits": move_meta_data.max_hits,
        "crit_rate": move_meta_data.crit_rate,
    }

def type_relations_dict(type_relations) -> dict:
    return {
        "no_damage_to": [t.name for t in type_relations.no_damage_to],
        "half_damage_to": [t.name for t in type_relations.half_damage_to],
        "double_damage_to": [t.name for t in type_relations.double_damage_to],
        "no_damage_from": [t.name for t in type_relations.no_damage_from],
        "half_damage_from": [t.name for t in type_relations.half_damage_from],
        "double_damage_from": [t.name for t in type_relations.double_damage_from],
    }


# APIResourceListの引数は https://pokeapi.co/docs/v2#pokemon-species のGETのところに書かれているURL内のendopointを表す文字列である。
def download_all_pokemon_species(output_filepath, start_from=1) -> None:
    if os.path.exists(output_filepath):
        raise Exception
    data = []
    try:
        for i, name in enumerate(pokebase.APIResourceList("pokemon-species").names, 1):
            if i < start_from:
                continue
            print(f"{i}: {name} ", end="", flush=True)
            data.append(download_pokemon_species(name))
            print("downloaded", flush=True)
    finally:
        save_to_json(data, output_filepath)

def download_all_moves(output_filepath, start_from=1) -> None:
    if os.path.exists(output_filepath):
        raise Exception
    data = []
    try:
        for i, name in enumerate(pokebase.APIResourceList("move").names, 1):
            if i < start_from:
                continue
            print(f"{i}: {name} ", end="", flush=True)
            data.append(download_move(name))
            print("downloaded", flush=True)
    finally:
        save_to_json(data, output_filepath)

def download_all_types(output_filepath) -> None:
    if os.path.exists(output_filepath):
        raise Exception
    data = []
    try:
        for i, name in enumerate(pokebase.APIResourceList("type").names):
            print(f"{i}: {name} ", end="", flush=True)
            data.append(download_type(name))
            print("downloaded", flush=True)
    finally:
        save_to_json(data, output_filepath)

def download_all_abilities(output_filepath, start_from=1) -> None:
    if os.path.exists(output_filepath):
        raise Exception
    data = []
    try:
        for i, name in enumerate(pokebase.APIResourceList("ability").names, 1):
            if i < start_from:
                continue
            print(f"{i}: {name} ", end="", flush=True)
            data.append(download_ability(name))
            print("downloaded", flush=True)
    finally:
        save_to_json(data, output_filepath)

def get_jp_name(names) -> dict | None:
    # "ja-Hrkt" はひらがなカタカナ、"ja" は漢字？
    for name in names:
        if name.language.name == "ja-Hrkt":
            return {"name": name.name, "language": "ja-Hrkt"}
    for name in names:
        if name.language.name == "ja":
            return {"name": name.name, "language": "ja"}
    return None

def save_to_json(data, output_filepath: PathLike | str) -> None:
    with open(output_filepath, mode="w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_pokeapi_data_json(input_filepath: PathLike | str) -> list[dict]:
    with open(input_filepath, encoding="utf-8") as f:
        return json.load(f)

def main() -> None:
    download_all_pokemon_species(default_input_filepaths.pokeapi_filepaths.pokeapi_pokemon_species_filepath)
    download_all_moves(default_input_filepaths.pokeapi_filepaths.pokeapi_moves_filepath)
    download_all_types(default_input_filepaths.pokeapi_filepaths.pokeapi_types_filepath)
    download_all_abilities(default_input_filepaths.pokeapi_filepaths.pokeapi_abilities_filepath)

if __name__ == "__main__":
    main()
