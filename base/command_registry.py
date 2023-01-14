from typing import Optional

commands: dict[str, list[str]] = {}


def register_command(owner: str, command: str):
    if commands.get(owner) is None:
        commands[owner] = []
    commands[owner].append(command)


def get_commands(owner: str) -> list[str]:
    return commands.get(owner)
