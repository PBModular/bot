import inspect
from typing import Optional
from copy import copy


class State:
    def __init__(self):
        self._owner: Optional[StateMachine] = None
        self._name: Optional[str] = None
        
    def __set_owner__(self, owner: "StateMachine", name: str):
        self._owner = owner
        self._name = name
    
    @property
    def name(self) -> Optional[str]:
        return f"{self._owner.__class__.__name__}:{self._name}" if self._owner is not None else None
    
    def set(self):
        """
        Set this state as active. Shortcut for StateMachine.set_state()
        """
        self._owner.set_state(self)
    
    def is_set(self) -> bool:
        """
        Checks if this state is active now
        """
        return (self._owner.get_state() == self) if self._owner is not None else False
    
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, State) and __o.name == self.name
    
    def __str__(self) -> str:
        return f"State(name={self.name}, is_set={self.is_set()})"
    
    __repr__ = __str__


class StateMachine:
    def __init__(self):
        self._current_state: Optional[State] = None
        self._state_data = {}

        # Init all declared states
        members = inspect.getmembers(self)
        for name, member in members:
            if isinstance(member, State):
                member.__set_owner__(self, name)
                setattr(self, name, copy(member))
    
    def get_state(self) -> Optional[State]:
        """
        Get the current state
        """
        return self._current_state
    
    def set_state(self, state: State):
        """
        Set the current state
        """
        if not isinstance(state, State):
            raise ValueError("Invalid state type!")
        
        self._current_state = state
    
    def clear(self):
        """
        Reset the machine to default state
        """
        self._current_state = None
        self._state_data = {}
    
    def clear_data(self):
        """
        Clear only data, preserve state
        """
        self._state_data = {}
    
    @property
    def data(self) -> dict:
        return self._state_data
    
    @data.setter
    def data_set(self, data):
        if type(data) != dict:
            raise ValueError("FSM data must be a dict!")
        
        self._state_data = data
    
    def update_data(self, **kwargs):
        r"""
        Update fields in the data dictionary.
        :param \**kwargs: Key-value pairs for the dictionary
        """
        for key, value in kwargs.items():
            self._state_data[key] = value
    
    def get_data(self, key: str):
        """
        Get a value from the data dictionary
        :param key: Key for the dictionary
        """
        return self._state_data.get(key)
