from typing import Optional

commands: dict[str, list[str]] = {}


def register_command(owner: str, command: str):
    if commands.get(owner) is None:
        commands[owner] = []
    commands[owner].append(command)


def get_commands(owner: str) -> list[str]:
    return commands.get(owner)


def check_command(command: str) -> bool:
    for cmds in commands.values():
        if command in cmds:
            return True

    return False


def get_command_owner(command: str) -> Optional[str]:
    for owner, cmds in commands.items():
        if command in cmds:
            return owner

    return None


def remove_all(owner: str) -> bool:
    try:
        commands.pop(owner)
        return True
    except KeyError:
        return False
