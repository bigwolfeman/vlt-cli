import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from sqlalchemy.exc import SQLAlchemyError

from vlt.core.interfaces import IVaultService, ThreadStateView, ProjectOverviewView, SearchResult, NodeView
from vlt.core.models import Project, Thread, Node, State, Tag, Reference
from vlt.db import get_db

class VaultError(Exception):
    pass

class SqliteVaultService(IVaultService):
    def add_tag(self, node_id: str, tag_name: str) -> Tag:
        try:
            # Check if tag exists
            tag = self.db.scalars(select(Tag).where(Tag.name == tag_name)).first()
            if not tag:
                tag = Tag(name=tag_name)
                self.db.add(tag)
            
            node = self.db.get(Node, node_id)
            if not node:
                raise VaultError(f"Node {node_id} not found.")
            
            if tag not in node.tags:
                node.tags.append(tag)
            
            self.db.commit()
            self.db.refresh(tag)
            return tag
        except SQLAlchemyError as e:
            self.db.rollback()
            raise VaultError(f"Database error adding tag: {str(e)}")

    def add_reference(self, source_node_id: str, target_thread_id: str, note: str) -> Reference:
        try:
            # Check if source node exists
            node = self.db.get(Node, source_node_id)
            if not node:
                raise VaultError(f"Source Node {source_node_id} not found.")
            
            # Check if target thread exists (handle project/thread slug)
            if "/" in target_thread_id:
                _, target_slug = target_thread_id.split("/")
            else:
                target_slug = target_thread_id
                
            thread = self.db.get(Thread, target_slug)
            if not thread:
                raise VaultError(f"Target Thread {target_slug} not found.")

            ref = Reference(
                id=str(uuid.uuid4()),
                source_node_id=source_node_id,
                target_thread_id=target_slug,
                note=note
            )
            self.db.add(ref)
            self.db.commit()
            self.db.refresh(ref)
            return ref
        except SQLAlchemyError as e:
            self.db.rollback()
            raise VaultError(f"Database error adding reference: {str(e)}")

    def __init__(self, db: Session = None):
        self._db = db

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = next(get_db())
        return self._db
        
    def __del__(self):
        # Optional cleanup if we created the session
        # Realistically, for a CLI tool, process exit cleans up.
        pass

    def create_project(self, name: str, description: str) -> Project:
        try:
            project_id = name.lower().replace(" ", "-")
            project = Project(id=project_id, name=name, description=description)
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
            return project
        except SQLAlchemyError as e:
            self.db.rollback()
            raise VaultError(f"Database error creating project: {str(e)}")

    def create_thread(self, project_id: str, name: str, initial_thought: str) -> Thread:
        try:
            thread_id = name.lower().replace(" ", "-")
            thread = Thread(id=thread_id, project_id=project_id, status="active")
            self.db.add(thread)
            self.db.commit() 
            
            self.add_thought(thread_id, initial_thought)
            
            self.db.refresh(thread)
            return thread
        except SQLAlchemyError as e:
            self.db.rollback()
            raise VaultError(f"Database error creating thread: {str(e)}")

    def add_thought(self, thread_id: str, content: str) -> Node:
        try:
            last_node = self.db.scalars(
                select(Node)
                .where(Node.thread_id == thread_id)
                .order_by(desc(Node.sequence_id))
                .limit(1)
            ).first()

            new_sequence_id = (last_node.sequence_id + 1) if last_node else 0
            prev_node_id = last_node.id if last_node else None

            node = Node(
                id=str(uuid.uuid4()),
                thread_id=thread_id,
                sequence_id=new_sequence_id,
                content=content,
                prev_node_id=prev_node_id,
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(node)
            self.db.commit()
            self.db.refresh(node)
            return node
        except SQLAlchemyError as e:
            self.db.rollback()
            raise VaultError(f"Database error adding thought: {str(e)}")

    def get_thread_state(self, thread_id: str) -> ThreadStateView:
        if "/" in thread_id:
            _, thread_slug = thread_id.split("/")
        else:
            thread_slug = thread_id

        state = self.db.scalars(
            select(State)
            .where(State.target_id == thread_slug)
            .where(State.target_type == "thread")
        ).first()

        nodes = self.db.scalars(
            select(Node)
            .where(Node.thread_id == thread_slug)
            .order_by(desc(Node.sequence_id))
            .limit(10)
        ).all()
        
        node_views = [
            NodeView(
                id=n.id, content=n.content, author=n.author, 
                timestamp=n.timestamp, sequence_id=n.sequence_id
            ) for n in reversed(nodes)
        ]

        return ThreadStateView(
            thread_id=thread_slug,
            summary=state.summary if state else "No summary available.",
            recent_nodes=node_views,
            meta=state.meta if state else {}
        )

    def get_project_overview(self, project_id: str) -> ProjectOverviewView:
        state = self.db.scalars(
            select(State)
            .where(State.target_id == project_id)
            .where(State.target_type == "project")
        ).first()

        threads = self.db.scalars(
            select(Thread).where(Thread.project_id == project_id)
        ).all()

        active_threads = [
            {"id": t.id, "status": t.status, "last_activity": "N/A"}
            for t in threads
        ]

        return ProjectOverviewView(
            project_id=project_id,
            summary=state.summary if state else "No project summary available.",
            active_threads=active_threads
        )

    def search(self, query: str, project_id: Optional[str] = None) -> List[SearchResult]:
        llm = OpenRouterLLMProvider()
        query_vec = llm.get_embedding(query)
        
        stmt = select(Node.id, Node.embedding).where(Node.embedding.is_not(None))
        if project_id:
            stmt = stmt.join(Thread).where(Thread.project_id == project_id)
            
        candidates = self.db.execute(stmt).all()
        
        vec_service = VectorService()
        matches = vec_service.search_memory(query_vec, candidates)
        
        if not matches:
            return []

        # Batch fetch matching nodes (Fix N+1)
        node_ids = [m[0] for m in matches]
        nodes = self.db.scalars(select(Node).where(Node.id.in_(node_ids))).all()
        node_map = {n.id: n for n in nodes}
        
        results = []
        for node_id, score in matches:
            if node_id in node_map:
                node = node_map[node_id]
                results.append(SearchResult(
                    node_id=node.id,
                    content=node.content,
                    score=score,
                    thread_id=node.thread_id
                ))
                
        return results