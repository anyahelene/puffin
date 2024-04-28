from typing_extensions import Annotated
from sqlalchemy import DDL, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import relationship,Mapped, mapped_column
from .database import Base
from .model_tables import User
from datetime import datetime

str_16 = Annotated[str, 16]
str_40 = Annotated[str, 40]
str_200 = Annotated[str, 200]


class OAuth1Token(Base):
    __tablename__ = 'oauth1token'
    __table_args__ = UniqueConstraint("provider_name", "user_id"),
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_name: Mapped[str_16]
    oauth_token: Mapped[str_200]
    oauth_token_secret: Mapped[str_200]
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))

    user = relationship("User")

    def to_token(self) -> dict:
        return {
            'oauth_token': self.oauth_token,
            'oauth_token_secret': self.oauth_token_secret,
        }


class OAuth2Token(Base):
    __tablename__ = 'oauth2token'
    __table_args__ = UniqueConstraint("provider_name", "user_id"),
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_name: Mapped[str_16]
    token_type: Mapped[str_40]
    access_token: Mapped[str_200]
    refresh_token: Mapped[str_200]
    expires_at: Mapped[datetime]
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))

    user = relationship("User")

    def is_expired(self):
        return self.expires_at != None and self.expires_at > datetime.now()

    def to_token(self) -> dict:
        return {
            'access_token': self.access_token,
            'token_type': self.token_type,
            'refresh_token': self.refresh_token,
            'expires_at': int(self.expires_at.timestamp())
        }
