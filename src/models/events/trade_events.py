"""
Trade Event Schemas - Issues #5, #6, #7

#5: standard/newTrade - Trade broadcast for all players
#6: sidebetResponse - Sidebet placement confirmation
#7: buyOrder/sellOrder - Trade execution request/response

Socket.IO Protocol:
- Broadcasts use prefix 42
- Responses use prefix 43XXXX (matching request ID)

Schema Version: 1.0.0
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ISSUE #5: standard/newTrade
# =============================================================================

class NewTrade(BaseModel):
    """
    Trade broadcast event - real-time trade feed.

    Broadcast to all connected clients when ANY player makes a trade.
    Use for volume analysis, whale detection, and ML training data.

    Socket.IO Format: 42["standard/newTrade", {...}]
    Auth Required: NO - Broadcast to all connections

    Example payload:
    {
        "playerId": "did:privy:cm3xxxxxxxxxxxxxx",
        "type": "BUY",
        "amount": 0.001,
        "price": 1.234,
        "timestamp": 1765069123456
    }
    """

    playerId: str = Field(..., description="Trader's player ID")
    type: Literal['BUY', 'SELL'] = Field(..., description="Trade type")
    amount: Decimal = Field(..., description="Trade amount (SOL)")
    price: Decimal = Field(..., description="Execution price")
    timestamp: int = Field(..., description="Server timestamp (ms)")

    # Additional fields that may appear
    username: Optional[str] = Field(None, description="Trader username")
    gameId: Optional[str] = Field(None, description="Game ID")

    # Ingestion metadata
    meta_ts: Optional[datetime] = Field(None)
    meta_seq: Optional[int] = Field(None)
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None)
    meta_session_id: Optional[str] = Field(None)

    @field_validator('amount', 'price', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        extra = 'allow'

    @property
    def is_buy(self) -> bool:
        return self.type == 'BUY'

    @property
    def is_whale_trade(self, threshold: Decimal = Decimal("1.0")) -> bool:
        """True if trade amount exceeds whale threshold."""
        return self.amount >= threshold


# =============================================================================
# ISSUE #6: sidebetResponse
# =============================================================================

class SidebetRequest(BaseModel):
    """
    Sidebet placement request (client → server).

    Socket.IO Format: 42XXX["sidebet", {...}]
    """
    target: int = Field(..., description="Target multiplier (e.g., 10 for 10x)")
    betSize: Decimal = Field(..., description="Bet amount (SOL)")

    @field_validator('betSize', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class SidebetResponse(BaseModel):
    """
    Sidebet placement confirmation (server → client).

    Socket.IO Format: 43XXX[{...}] (response to request ID XXX)
    Auth Required: YES - Response to authenticated request

    Example payload:
    {
        "success": true,
        "timestamp": 1765068967229
    }
    """

    success: bool = Field(..., description="Sidebet accepted")
    timestamp: int = Field(..., description="Server timestamp (ms)")

    # Error info (if success=false)
    error: Optional[str] = Field(None, description="Error message if failed")
    reason: Optional[str] = Field(None, description="Failure reason")

    # Ingestion metadata
    meta_ts: Optional[datetime] = Field(None)
    meta_seq: Optional[int] = Field(None)
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None)
    meta_session_id: Optional[str] = Field(None)
    meta_request_id: Optional[int] = Field(None, description="Original request ID")

    class Config:
        extra = 'allow'

    def calculate_latency(self, client_timestamp: int) -> int:
        """Calculate round-trip latency in milliseconds."""
        return client_timestamp - self.timestamp


# =============================================================================
# ISSUE #7: buyOrder/sellOrder
# =============================================================================

class BuyOrderRequest(BaseModel):
    """
    Buy order request (client → server).

    Socket.IO Format: 42XXX["buyOrder", {...}]
    """
    amount: Decimal = Field(..., description="Buy amount (SOL)")

    @field_validator('amount', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if isinstance(v, float):
            return Decimal(str(v))
        return v


class SellOrderRequest(BaseModel):
    """
    Sell order request (client → server).

    Socket.IO Format: 42XXX["sellOrder", {...}]
    """
    percentage: int = Field(..., description="Sell percentage (10, 25, 50, 100)")


class TradeOrderResponse(BaseModel):
    """
    Trade order confirmation (server → client).

    Socket.IO Format: 43XXX[{...}] (response to request ID XXX)
    Auth Required: YES - Response to authenticated request

    Example payload:
    {
        "success": true,
        "executedPrice": 1.234,
        "timestamp": 1765069123456
    }
    """

    success: bool = Field(..., description="Order executed successfully")
    executedPrice: Optional[Decimal] = Field(None, description="Execution price")
    timestamp: int = Field(..., description="Server timestamp (ms)")

    # Additional response fields
    amount: Optional[Decimal] = Field(None, description="Executed amount")
    fee: Optional[Decimal] = Field(None, description="Transaction fee")

    # Error info
    error: Optional[str] = Field(None, description="Error message if failed")
    reason: Optional[str] = Field(None, description="Failure reason")

    # Ingestion metadata
    meta_ts: Optional[datetime] = Field(None)
    meta_seq: Optional[int] = Field(None)
    meta_source: Optional[Literal['cdp', 'public_ws', 'replay', 'ui']] = Field(None)
    meta_session_id: Optional[str] = Field(None)
    meta_request_id: Optional[int] = Field(None, description="Original request ID")
    meta_order_type: Optional[Literal['BUY', 'SELL']] = Field(None, description="Order type")

    @field_validator('executedPrice', 'amount', 'fee', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return v

    class Config:
        extra = 'allow'

    def calculate_latency(self, client_timestamp: int) -> int:
        """Calculate round-trip latency in milliseconds."""
        return client_timestamp - self.timestamp
