import inspect
from typing import Optional, Type
from copy import copy

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from db import FSMState


class State:
    def __init__(self):
        self.__owner_cls: Optional[Type["StateMachine"]] = None
        self.__name: Optional[str] = None

    def __set_owner__(self, owner_cls: Type["StateMachine"], name: str):
        self.__owner_cls = owner_cls
        self.__name = name

    @property
    def name(self) -> Optional[str]:
        return f"{self.__owner_cls.__name__}:{self.__name}" if self.__owner_cls is not None else None

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, State):
            return __o.name == self.name
        if isinstance(__o, str):
            return self.name == __o
        return False

    def __str__(self) -> str:
        return f"State(name={self.name})"
    __repr__ = __str__


class StateMachine:
    """
    A controller for a user's state, persisted in the database.
    An instance of this class corresponds to a single user.
    """
    def __init__(self, user_id: int, session_maker: async_sessionmaker):
        self.user_id = user_id
        self.__session_maker = session_maker

        # Init all declared states
        members = inspect.getmembers(self.__class__, lambda a: isinstance(a, State))
        for name, member in members:
            member.__set_owner__(self.__class__, name)
            setattr(self, name, copy(member))

    async def _get_db_state(self) -> Optional[FSMState]:
        """Helper to fetch the raw state object from the DB."""
        async with self.__session_maker() as session:
            return await session.scalar(
                select(FSMState).where(FSMState.user_id == self.user_id)
            )

    async def get_state(self) -> Optional[str]:
        """Get the current state name for the user."""
        db_state = await self._get_db_state()
        return db_state.state if db_state else None

    async def set_state(self, state: Optional[State], data: Optional[dict] = None):
        """Set the user's state and optionally overwrite their data."""
        state_name = state.name if state else None
        async with self.__session_maker() as session:
            db_state = await session.scalar(
                select(FSMState).where(FSMState.user_id == self.user_id)
            )
            if db_state is None:
                session.add(FSMState(
                    user_id=self.user_id,
                    state=state_name,
                    data=data if data is not None else {}
                ))
            else:
                db_state.state = state_name
                if data is not None:
                    db_state.data = data
            await session.commit()

    async def get_data(self) -> dict:
        """Get the data dictionary for the user."""
        db_state = await self._get_db_state()
        return db_state.data or {} if db_state else {}

    async def update_data(self, **kwargs):
        """Update fields in the user's data dictionary."""
        async with self.__session_maker() as session:
            db_state = await session.scalar(
                select(FSMState).where(FSMState.user_id == self.user_id)
            )
            if db_state is None:
                session.add(FSMState(
                    user_id=self.user_id,
                    state=None,
                    data=kwargs
                ))
            else:
                current = dict(db_state.data or {})
                current.update(kwargs)
                db_state.data = current
            await session.commit()
            
    async def clear(self, keep_data: bool = False):
        """Reset the machine to default state, optionally clearing data."""
        if keep_data:
            await self.set_state(None) # Only reset the state
        else:
            async with self.__session_maker() as session:
                await session.execute(
                    delete(FSMState).where(FSMState.user_id == self.user_id)
                )
                await session.commit()
