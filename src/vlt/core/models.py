from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, ForeignKey, Integer, Text, LargeBinary, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from vlt.db import Base

class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[str] = mapped_column(String, primary_key=True) # Slug
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    threads: Mapped[List["Thread"]] = relationship(back_populates="project")

class Thread(Base):
    __tablename__ = "threads"
    
    id: Mapped[str] = mapped_column(String, primary_key=True) # Slug
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String, default="active") # Active, Archived, Blocked
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    project: Mapped["Project"] = relationship(back_populates="threads")
    nodes: Mapped[List["Node"]] = relationship(back_populates="thread")

class Node(Base):
    __tablename__ = "nodes"
    
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    thread_id: Mapped[str] = mapped_column(ForeignKey("threads.id"))
    sequence_id: Mapped[int] = mapped_column(Integer) # Ordered within thread
    content: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(String, default="user")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    embedding: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    prev_node_id: Mapped[Optional[str]] = mapped_column(ForeignKey("nodes.id"), nullable=True)

    thread: Mapped["Thread"] = relationship(back_populates="nodes")
    prev_node: Mapped[Optional["Node"]] = relationship(remote_side=[id])

class State(Base):
    __tablename__ = "states"
    
    id: Mapped[str] = mapped_column(String, primary_key=True) # UUID
    target_id: Mapped[str] = mapped_column(String) # Thread.id or Project.id
    target_type: Mapped[str] = mapped_column(String) # "thread" or "project"
    summary: Mapped[str] = mapped_column(Text)
    head_node_id: Mapped[Optional[str]] = mapped_column(ForeignKey("nodes.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    meta: Mapped[dict] = mapped_column(JSON, default={})

    head_node: Mapped[Optional["Node"]] = relationship()
