"""
test_json_store.py — unit test tầng lưu trữ JSON.

Kiểm tra: insert, find_all, find_by_id, find_by_field, find_one_by_field,
          update_by_id, delete_by_id, count, thread-safety.
"""

import threading
import uuid
from pathlib import Path

import pytest

import app.database.json_store as store


# data_dir fixture từ conftest đã patch DATA_DIR và reset _locks


# ---------------------------------------------------------------------------
# insert / find_all
# ---------------------------------------------------------------------------

class TestInsert:
    def test_insert_returns_document(self, data_dir):
        doc = {"_id": str(uuid.uuid4()), "name": "Alice"}
        result = store.insert("col", doc)
        assert result == doc

    def test_insert_persists_to_file(self, data_dir):
        doc = {"_id": "id-1", "value": 42}
        store.insert("col", doc)
        records = store.find_all("col")
        assert len(records) == 1
        assert records[0]["value"] == 42

    def test_insert_multiple(self, data_dir):
        for i in range(5):
            store.insert("col", {"_id": str(i), "idx": i})
        assert store.count("col") == 5

    def test_insert_creates_file_if_not_exists(self, data_dir):
        assert not (data_dir / "newcol.json").exists()
        store.insert("newcol", {"_id": "x"})
        assert (data_dir / "newcol.json").exists()

    def test_multiple_collections_isolated(self, data_dir):
        store.insert("col_a", {"_id": "1", "x": "a"})
        store.insert("col_b", {"_id": "2", "x": "b"})
        assert store.count("col_a") == 1
        assert store.count("col_b") == 1


# ---------------------------------------------------------------------------
# find_by_id
# ---------------------------------------------------------------------------

class TestFindById:
    def test_found(self, data_dir):
        doc = {"_id": "abc", "data": "hello"}
        store.insert("col", doc)
        result = store.find_by_id("col", "abc")
        assert result is not None
        assert result["data"] == "hello"

    def test_not_found(self, data_dir):
        assert store.find_by_id("col", "nonexistent") is None

    def test_empty_collection(self, data_dir):
        assert store.find_by_id("empty", "x") is None


# ---------------------------------------------------------------------------
# find_by_field / find_one_by_field
# ---------------------------------------------------------------------------

class TestFindByField:
    def setup_method(self):
        """Gọi trước mỗi test method — không thể dùng data_dir ở đây,
        setup thực hiện trong test thông qua data_dir fixture."""

    def test_find_by_field_returns_all_matches(self, data_dir):
        store.insert("col", {"_id": "1", "role": "admin"})
        store.insert("col", {"_id": "2", "role": "user"})
        store.insert("col", {"_id": "3", "role": "user"})

        results = store.find_by_field("col", "role", "user")
        assert len(results) == 2

    def test_find_by_field_no_match(self, data_dir):
        store.insert("col", {"_id": "1", "role": "admin"})
        assert store.find_by_field("col", "role", "guest") == []

    def test_find_one_by_field_returns_first(self, data_dir):
        store.insert("col", {"_id": "1", "email": "a@b.com"})
        store.insert("col", {"_id": "2", "email": "a@b.com"})
        result = store.find_one_by_field("col", "email", "a@b.com")
        assert result is not None
        assert result["_id"] == "1"

    def test_find_one_by_field_none_when_missing(self, data_dir):
        result = store.find_one_by_field("col", "email", "x@y.com")
        assert result is None


# ---------------------------------------------------------------------------
# update_by_id
# ---------------------------------------------------------------------------

class TestUpdateById:
    def test_update_merges_fields(self, data_dir):
        store.insert("col", {"_id": "1", "a": 1, "b": 2})
        updated = store.update_by_id("col", "1", {"b": 99, "c": 3})
        assert updated["a"] == 1
        assert updated["b"] == 99
        assert updated["c"] == 3

    def test_update_persists(self, data_dir):
        store.insert("col", {"_id": "1", "val": "old"})
        store.update_by_id("col", "1", {"val": "new"})
        record = store.find_by_id("col", "1")
        assert record["val"] == "new"

    def test_update_nonexistent_returns_none(self, data_dir):
        result = store.update_by_id("col", "ghost", {"x": 1})
        assert result is None

    def test_update_does_not_affect_others(self, data_dir):
        store.insert("col", {"_id": "1", "val": "A"})
        store.insert("col", {"_id": "2", "val": "B"})
        store.update_by_id("col", "1", {"val": "X"})
        assert store.find_by_id("col", "2")["val"] == "B"


# ---------------------------------------------------------------------------
# delete_by_id
# ---------------------------------------------------------------------------

class TestDeleteById:
    def test_delete_returns_true(self, data_dir):
        store.insert("col", {"_id": "1"})
        assert store.delete_by_id("col", "1") is True

    def test_delete_removes_record(self, data_dir):
        store.insert("col", {"_id": "1"})
        store.delete_by_id("col", "1")
        assert store.find_by_id("col", "1") is None

    def test_delete_nonexistent_returns_false(self, data_dir):
        assert store.delete_by_id("col", "ghost") is False

    def test_delete_only_removes_target(self, data_dir):
        store.insert("col", {"_id": "1"})
        store.insert("col", {"_id": "2"})
        store.delete_by_id("col", "1")
        assert store.count("col") == 1
        assert store.find_by_id("col", "2") is not None


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------

class TestCount:
    def test_count_empty(self, data_dir):
        assert store.count("col") == 0

    def test_count_after_inserts(self, data_dir):
        for i in range(7):
            store.insert("col", {"_id": str(i)})
        assert store.count("col") == 7

    def test_count_after_delete(self, data_dir):
        store.insert("col", {"_id": "1"})
        store.insert("col", {"_id": "2"})
        store.delete_by_id("col", "1")
        assert store.count("col") == 1


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_inserts(self, data_dir):
        """100 thread đồng thời insert → không mất record, không corrupt file."""
        errors = []

        def worker(i: int):
            try:
                store.insert("concurrent", {"_id": str(i), "val": i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(100)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Lỗi trong threads: {errors}"
        assert store.count("concurrent") == 100

    def test_concurrent_update_same_doc(self, data_dir):
        """Nhiều thread cùng update 1 document — giá trị cuối cùng hợp lệ."""
        store.insert("col", {"_id": "shared", "counter": 0})
        errors = []

        def updater(val: int):
            try:
                store.update_by_id("col", "shared", {"counter": val})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=updater, args=(i,)) for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        doc = store.find_by_id("col", "shared")
        # Giá trị là 1 trong 50 giá trị hợp lệ — không crash, không None
        assert doc is not None
        assert isinstance(doc["counter"], int)
