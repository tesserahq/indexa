"""Tasks run in managed transactions and call external services (Identies,
domain services, search providers) with no transaction open."""

import importlib
from unittest.mock import Mock
from uuid import uuid4

import pytest
from tessera_sdk.infra import current_session

from app.commands.index_entity_command import IndexEntityCommand, IndexPlan
from app.commands.batch_index_entities_command import BatchIndexEntitiesCommand
from app.models.event import Event
from app.models.reindex_job import ReindexJob, ReindexJobStatus
from app.models.user import User
from app.schemas.user import UserOnboard

# app.tasks re-exports the task functions under their module names.
index_module = importlib.import_module("app.tasks.index_entity_task")
nats_module = importlib.import_module("app.tasks.process_nats_event")
reindex_module = importlib.import_module("app.tasks.reindex_task")


@pytest.fixture
def task_sessions(execution_boundary, monkeypatch):
    """Each session_scope() in the tasks runs against the test session."""
    for module in (nats_module, index_module, reindex_module):
        monkeypatch.setattr(module, "session_scope", execution_boundary)


@pytest.fixture
def enqueued(monkeypatch):
    delay = Mock()
    monkeypatch.setattr(nats_module.index_entity_task, "delay", delay)
    return delay


def _message(user_id=None, subject="thing"):
    return {
        "source": "tests",
        "event_type": "thing.happened",
        "subject": subject,
        "event_data": {"a": 1},
        "user_id": str(user_id) if user_id else None,
    }


def test_event_is_stored_and_indexing_enqueued_after_commit(
    db, task_sessions, enqueued, monkeypatch
):
    subject = f"thing-{uuid4()}"

    def enqueue_after_commit(event_id):
        assert current_session() is None
        assert db.query(Event).filter(Event.subject == subject).count() == 1

    enqueued.side_effect = enqueue_after_commit

    nats_module.process_nats_event_task(_message(subject=subject))

    enqueued.assert_called_once()


def test_unknown_user_is_onboarded_without_an_open_transaction(
    db, task_sessions, enqueued, faker, monkeypatch
):
    user_id = uuid4()

    def fetch(requested_id):
        assert current_session() is None
        return UserOnboard(
            id=user_id,
            email=faker.email(),
            first_name=faker.first_name(),
            last_name=faker.last_name(),
            provider="google",
            external_id=str(uuid4()),
        )

    monkeypatch.setattr(nats_module, "_fetch_identies_user", fetch)

    nats_module.process_nats_event_task(_message(user_id))

    assert db.query(User).filter(User.id == user_id).count() == 1


def test_identies_failure_keeps_the_event(db, task_sessions, enqueued, monkeypatch):
    user_id = uuid4()
    monkeypatch.setattr(
        nats_module,
        "_fetch_identies_user",
        Mock(side_effect=RuntimeError("identies unavailable")),
    )

    nats_module.process_nats_event_task(_message(user_id))

    assert db.query(Event).filter(Event.user_id == user_id).count() == 1
    enqueued.assert_called_once()


def test_indexing_calls_providers_without_an_open_transaction(
    db, task_sessions, setup_event, monkeypatch
):
    provider = Mock()
    provider.name = "fake"
    plan = IndexPlan(
        source="tests",
        entity_type="thing",
        entity_id="1",
        base_url="http://domain",
        indexes_path_prefix=None,
        providers=[provider],
    )
    monkeypatch.setattr(IndexEntityCommand, "prepare", lambda self, event: plan)

    def get_entity(**kwargs):
        assert current_session() is None
        return {"id": "1"}

    monkeypatch.setattr(
        index_module.IndexEntityCommand, "__init__", _init_with_client(get_entity)
    )

    index_module.index_entity_task(str(setup_event.id))

    provider.upsert.assert_called_once()


def _init_with_client(get_entity):
    original = IndexEntityCommand.__init__

    def init(self, db, nats_publisher=None):
        original(self, db, nats_publisher=Mock())
        self.domain_client = Mock(get_entity=Mock(side_effect=get_entity))

    return init


def test_failed_reindex_records_failed_status(
    db, task_sessions, setup_domain_service, monkeypatch
):
    job = ReindexJob(entity_types=["thing"])
    db.add(job)
    db.flush()
    job_id = job.id
    monkeypatch.setattr(
        BatchIndexEntitiesCommand,
        "execute",
        Mock(side_effect=RuntimeError("domain service unavailable")),
    )

    with pytest.raises(RuntimeError, match="domain service unavailable"):
        reindex_module.reindex_task(str(job_id))

    db.expire_all()
    job = db.get(ReindexJob, job_id)
    assert job.status == ReindexJobStatus.FAILED
    assert job.error_message == "domain service unavailable"
    assert job.started_at is not None
