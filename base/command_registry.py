from typing import Optional

commands: dict[str, list[str]] = {}


def register_command(owner: str, command: str, override: bool = False):
    """Register a command for the given owner.

    :param owner (str): The owner of the command.
    :param command (str): The command to register.
    :param override (bool): If True, overrides the command if it’s already registered to another owner. Defaults to False.

    :return ValueError: If the command is already registered to another owner and override is False.
    """
    current_owner = get_command_owner(command)
    if current_owner and current_owner != owner and not override:
        raise ValueError(f"Command '{command}' is already registered to '{current_owner}'.")
    
    if owner not in commands:
        commands[owner] = []
    if command not in commands[owner]:
        commands[owner].append(command)


def get_commands(owner: str) -> list[str]:
    """Get the list of commands registered by the given owner.

    :param owner (str): The owner of the commands.
    :return: The list of commands, or an empty list if the owner is not found.
    """
    return commands.get(owner, [])


def check_command(command: str) -> bool:
    """Check if the command is registered by any owner.
    
    :param command (str): The command to check.
    :return bool: True if the command is registered, False otherwise.
    """
    for cmds in commands.values():
        if command in cmds:
            return True
    return False


def get_command_owner(command: str) -> Optional[str]:
    """Get the owner of the given command.
    
    :param command (str): The command to find the owner for.
    :return Optional[str]: The owner of the command, or None if not found.
    """
    for owner, cmds in commands.items():
        if command in cmds:
            return owner
    return None


def remove_all(owner: str) -> bool:
    """Remove all commands registered by the given owner.
    
    :param owner (str): The owner whose commands to remove.
    :return bool: True if the owner's commands were removed, False if the owner was not found.
    """
    if owner in commands:
        del commands[owner]
        return True
    return False
