from koala.typing import *
from koala.storage.record import *
from koala.storage.record_meta import *


class RecordStorage(Generic[RecordType]):
    @property
    @abstractmethod
    def table_name(self) -> str:
        pass

    @property
    @abstractmethod
    def unique_key(self) -> KeyInfo:
        pass

    @abstractmethod
    async def insert_one(self, record: Record) -> bool:
        pass

    @abstractmethod
    async def delete_one(self, record: Record) -> bool:
        pass

    @abstractmethod
    async def find(self, key1: TypeID, key2: Optional[TypeID] = None) -> List[RecordType]:
        pass

    @abstractmethod
    async def find_one(self, key1: TypeID) -> Optional[RecordType]:
        pass


class IStorageEngine(ABC):
    @abstractmethod
    def init_storage(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_storage(self, record_type: Type[RecordType]) -> RecordStorage[RecordType]:
        pass
    pass

