import inspect
from typing import Optional
from copy import copy


class State:
    def __init__(self):
        self.__owner: Optional[StateMachine] = None
        self.__name: Optional[str] = None
        
    def __set_owner__(self, owner: "StateMachine", name: str):
        self.__owner = owner
        self.__name = name
    
    @property
    def name(self) -> Optional[str]:
        return f"{self.__owner.__class__.__name__}:{self.__name}" if self.__owner is not None else None
    
    def set(self):
        """
        Set this state as active. Shortcut for StateMachine.cur_state setter
        """
        self.__owner.cur_state = self
    
    def is_set(self) -> bool:
        """
        Checks if this state is active now
        """
        return (self.__owner.cur_state == self) if self.__owner is not None else False
    
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, State) and __o.name == self.name
    
    def __str__(self) -> str:
        return f"State(name={self.name}, is_set={self.is_set()})"
    
    __repr__ = __str__


class StateMachine:
    def __init__(self):
        self.__current_state: Optional[State] = None
        self.__state_data = {}

        # Init all declared states
        members = inspect.getmembers(self)
        for name, member in members:
            if isinstance(member, State):
                member.__set_owner__(self, name)
                setattr(self, name, copy(member))
    
    @property
    def cur_state(self) -> Optional[State]:
        """
        Get the current state
        """
        return self.__current_state
    
    @cur_state.setter
    def cur_state(self, data):
        """
        Set the current state
        """
        if not isinstance(data, State):
            raise ValueError("Invalid state type!")
        
        self.__current_state = data
    
    def clear(self):
        """
        Reset the machine to default state
        """
        self.__current_state = None
        self.__state_data = {}
    
    def clear_data(self):
        """
        Clear only data, preserve state
        """
        self.__state_data = {}
    
    @property
    def data(self) -> dict:
        return self.__state_data
    
    @data.setter
    def data(self, data):
        if type(data) != dict:
            raise ValueError("FSM data must be a dict!")
        
        self.__state_data = data
    
    def update_data(self, **kwargs):
        r"""
        Update fields in the data dictionary.

        :param \**kwargs: Key-value pairs for the dictionary
        """
        for key, value in kwargs.items():
            self.__state_data[key] = value
    
    def get_data(self, key: str):
        """
        Get a value from the data dictionary
        
        :param key: Key for the dictionary
        """
        return self.__state_data.get(key)
