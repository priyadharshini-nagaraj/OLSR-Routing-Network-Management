"""Message classes for OLSR protocol"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from config import MessageType

@dataclass
class OLSRMessage:
    """OLSR protocol message"""
    msg_id: str
    msg_type: MessageType
    source: str
    destination: Optional[str] = None
    timestamp: float = 0.0
    ttl: int = 32
    payload: Dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            'id': self.msg_id,
            'type': self.msg_type.value,
            'source': self.source,
            'destination': self.destination,
            'timestamp': self.timestamp,
            'ttl': self.ttl
        }
    
    def copy(self):
        """Create a copy of the message"""
        return OLSRMessage(
            msg_id=self.msg_id,
            msg_type=self.msg_type,
            source=self.source,
            destination=self.destination,
            timestamp=self.timestamp,
            ttl=self.ttl,
            payload=self.payload.copy() if self.payload else {}
        )