from pathlib import Path
from os import PathLike
from dataclasses import dataclass


@dataclass(eq=False)
class PokeapiFilepaths:
    pokeapi_pokemon_species_filepath: PathLike | str
    pokeapi_moves_filepath: PathLike | str
    pokeapi_types_filepath: PathLike | str
    pokeapi_abilities_filepath: PathLike | str


@dataclass(eq=False)
class NamesFilepaths:
    pokemon_names_filepath: PathLike | str
    move_names_filepath: PathLike | str
    type_names_filepath: PathLike | str
    ability_names_filepath: PathLike | str
    item_names_filepath: PathLike | str
    state_names_filepath: PathLike | str


@dataclass(eq=False)
class InputFilepaths:
    pokeapi_filepaths: PokeapiFilepaths
    names_filepaths: NamesFilepaths
    replacement_filepath: PathLike | str
    preset_filepath: PathLike | str


parent_dir_path = Path(__file__).resolve().parent
default_input_filepaths = InputFilepaths(
    PokeapiFilepaths(
        parent_dir_path / "pokeapi" / "pokeapi_pokemon_species.json",
        parent_dir_path / "pokeapi" / "pokeapi_moves.json",
        parent_dir_path / "pokeapi" / "pokeapi_types.json",
        parent_dir_path / "pokeapi" / "pokeapi_abilities.json",
    ),
    NamesFilepaths(
        parent_dir_path / "pokemon_names.json",
        parent_dir_path / "move_names.json",
        parent_dir_path / "type_names.json",
        parent_dir_path / "ability_names.json",
        parent_dir_path / "item_names.json",
        parent_dir_path / "state_names.json",
    ),
    parent_dir_path / "jp_replacement.json",
    parent_dir_path / "preset.json",
)
del parent_dir_path
