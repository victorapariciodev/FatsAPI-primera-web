"""Cliente Supabase falso, en memoria, para tests.

Motivo: los servicios hablan con PostgREST a traves de supabase-py. Para
probar la logica de negocio no hace falta una base de datos real ni red: hace
falta un doble que respete el contrato que usamos (select/insert/update/delete,
filtros, count exacto, range y RPC).

Lo que NO modela, a proposito: RLS, transacciones y concurrencia. Esas se
verifican contra Postgres de verdad (db/store_schema.sql), no con un fake.
"""

from __future__ import annotations

from copy import deepcopy
from itertools import count
from types import SimpleNamespace
from typing import Any, Callable


class FakeResponse:
    def __init__(self, data: Any, count_: int | None = None) -> None:
        self.data = data
        self.count = count_


class FakeUserResponse:
    """Imita la respuesta de ``auth.admin``: expone ``.user``."""

    def __init__(self, user_id: str, datos: dict[str, Any]) -> None:
        self.user = SimpleNamespace(
            id=user_id,
            email=datos.get("email"),
            app_metadata=deepcopy(datos.get("app_metadata") or {}),
            user_metadata=deepcopy(datos.get("user_metadata") or {}),
        )


class FakeUserAdmin:
    """Doble minimo de ``auth.admin``: leer y actualizar metadata.

    ``update_user_by_id`` REEMPLAZA ``app_metadata`` en vez de fusionarla.
    Se elige a proposito la semantica mas estricta: si el codigo enviara solo
    la clave nueva, el test borraria el rol y lo delataria. Asi no dependemos
    de una semantica de GoTrue que no controlamos.
    """

    def __init__(self, db: "FakeDB") -> None:
        self._db = db

    def _usuario(self, user_id: str) -> dict[str, Any]:
        datos = self._db.users.get(user_id)
        if datos is None:
            raise AssertionError(
                f"usuario '{user_id}' no existe en el test; "
                f"agrega db.users['{user_id}'] = {{...}}"
            )
        return datos

    def get_user_by_id(self, user_id: str) -> FakeUserResponse:
        return FakeUserResponse(user_id, self._usuario(user_id))

    def update_user_by_id(self, user_id: str, payload: dict[str, Any]) -> FakeUserResponse:
        datos = self._usuario(user_id)
        for campo in ("app_metadata", "user_metadata"):
            if campo in payload:
                datos[campo] = deepcopy(payload[campo])
        return FakeUserResponse(user_id, datos)


class FakeAuth:
    def __init__(self, db: "FakeDB") -> None:
        self.admin = FakeUserAdmin(db)


class FakeRpc:
    def __init__(self, db: "FakeDB", name: str, params: dict[str, Any]) -> None:
        self._db = db
        self._name = name
        self._params = params

    def execute(self) -> FakeResponse:
        handler: Callable[[dict[str, Any]], Any] | None = self._db.rpc_handlers.get(
            self._name
        )
        if handler is None:
            raise AssertionError(
                f"RPC '{self._name}' no definida en el test. "
                f"Define db.rpc_handlers['{self._name}']."
            )
        return FakeResponse(handler(self._params))


class FakeQuery:
    def __init__(self, db: "FakeDB", table: str) -> None:
        self._db = db
        self._table = table
        self._op = "select"
        self._payload: Any = None
        self._columns = "*"
        self._count_mode: str | None = None
        self._filters: list[tuple[str, str, Any]] = []
        self._order: tuple[str, bool] | None = None
        self._limit: int | None = None
        self._range: tuple[int, int] | None = None

    # ---------------- operaciones ----------------
    def select(self, columns: str = "*", count: str | None = None) -> "FakeQuery":
        self._op = "select"
        self._columns = columns
        self._count_mode = count
        return self

    def insert(self, payload: Any) -> "FakeQuery":
        self._op = "insert"
        self._payload = payload
        return self

    def upsert(self, payload: Any) -> "FakeQuery":
        """Aproxima el upsert de PostgREST.

        PostgREST resuelve el conflicto por la primary key o por un unique del
        esquema, y el fake no conoce el esquema. Se usa ``profile_id`` cuando
        viene en el payload, que es justo el unique de las tablas de perfil;
        para cualquier otra tabla se comporta como un insert.
        """
        self._op = "upsert"
        self._payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> "FakeQuery":
        self._op = "update"
        self._payload = payload
        return self

    def delete(self) -> "FakeQuery":
        self._op = "delete"
        return self

    # ---------------- filtros ----------------
    def eq(self, column: str, value: Any) -> "FakeQuery":
        self._filters.append(("eq", column, value))
        return self

    def gt(self, column: str, value: Any) -> "FakeQuery":
        self._filters.append(("gt", column, value))
        return self

    def gte(self, column: str, value: Any) -> "FakeQuery":
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column: str, value: Any) -> "FakeQuery":
        self._filters.append(("lte", column, value))
        return self

    def ilike(self, column: str, value: str) -> "FakeQuery":
        self._filters.append(("ilike", column, value))
        return self

    def in_(self, column: str, values: Any) -> "FakeQuery":
        self._filters.append(("in", column, set(values)))
        return self

    def limit(self, value: int) -> "FakeQuery":
        self._limit = value
        return self

    def order(self, column: str, desc: bool = False, **_: Any) -> "FakeQuery":
        self._order = (column, desc)
        return self

    def range(self, start: int, end: int) -> "FakeQuery":
        self._range = (start, end)
        return self

    # ---------------- motor ----------------
    def _matches(self, row: dict[str, Any]) -> bool:
        for kind, column, value in self._filters:
            current = row.get(column)
            if kind == "eq" and current != value:
                return False
            if kind == "gt" and not (current is not None and current > value):
                return False
            if kind == "gte" and not (current is not None and current >= value):
                return False
            if kind == "lte" and not (current is not None and current <= value):
                return False
            if kind == "ilike":
                needle = value.strip("%").lower()
                if needle not in str(current or "").lower():
                    return False
            if kind == "in" and current not in value:
                return False
        return True

    def _embed(self, row: dict[str, Any]) -> dict[str, Any]:
        """Adjunta el recurso embebido que el servicio pide en el select."""
        out = dict(row)
        if self._table == "products" and "product_variants(*)" in self._columns:
            out["product_variants"] = [
                deepcopy(v)
                for v in self._db.tables["product_variants"]
                if v.get("product_id") == row.get("id")
            ]
        if self._table == "orders" and "order_items(*)" in self._columns:
            out["order_items"] = [
                deepcopy(i)
                for i in self._db.tables["order_items"]
                if i.get("order_id") == row.get("id")
            ]
        return out

    def execute(self) -> FakeResponse:
        table = self._db.tables.setdefault(self._table, [])

        if self._op == "upsert":
            item = deepcopy(
                self._payload if isinstance(self._payload, dict) else self._payload[0]
            )
            clave = item.get("profile_id")
            existente = next(
                (
                    row
                    for row in table
                    if clave is not None and row.get("profile_id") == clave
                ),
                None,
            )
            if existente is not None:
                existente.update(item)
                return FakeResponse([deepcopy(existente)])
            self._op = "insert"
            self._payload = item

        if self._op == "insert":
            items = self._payload if isinstance(self._payload, list) else [self._payload]
            created = []
            for item in items:
                row = deepcopy(item)
                for key, value in self._db.defaults.get(self._table, {}).items():
                    row.setdefault(key, value)
                row.setdefault("id", self._db.next_id(self._table))
                table.append(row)
                created.append(deepcopy(row))
            return FakeResponse(created)

        matched = [row for row in table if self._matches(row)]

        if self._op == "update":
            for row in matched:
                row.update(deepcopy(self._payload))
            return FakeResponse([deepcopy(row) for row in matched])

        if self._op == "delete":
            removed = [deepcopy(row) for row in matched]
            self._db.tables[self._table] = [
                row for row in table if not self._matches(row)
            ]
            return FakeResponse(removed)

        rows = [deepcopy(row) for row in matched]
        total = len(rows)

        if self._order:
            column, desc = self._order
            rows.sort(
                key=lambda r: (r.get(column) is None, r.get(column)),
                reverse=desc,
            )

        if self._range:
            start, end = self._range
            rows = rows[start : end + 1]
        if self._limit is not None:
            rows = rows[: self._limit]

        rows = [self._embed(row) for row in rows]
        return FakeResponse(rows, total if self._count_mode == "exact" else None)


class FakeDB:
    """Doble del cliente supabase.Client."""

    def __init__(
        self,
        tables: dict[str, list[dict[str, Any]]] | None = None,
        users: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = deepcopy(tables or {})
        # Usuarios para ``auth.admin``: metadata real de cada uno.
        self.users: dict[str, dict[str, Any]] = deepcopy(users or {
            "u1": {"email": "u1@test.dev", "app_metadata": {"role": "user"}},
            "u9": {"email": "admin@test.dev", "app_metadata": {"role": "admin"}},
        })
        self.auth = FakeAuth(self)
        self.rpc_handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        # Defaults que en Postgres aplica el DDL (sendos en db/store_schema.sql).
        # Sin esto, un insert falso devolveria filas que la base real no devuelve.
        self.defaults: dict[str, dict[str, Any]] = {
            "products": {"currency": "USD", "is_active": True},
            "product_variants": {"stock": 0},
            "orders": {"status": "pending"},
        }
        self._ids = count(1)

    def next_id(self, table: str) -> str:
        return f"{table}-{next(self._ids)}"

    def table(self, name: str) -> FakeQuery:
        self.tables.setdefault(name, [])
        return FakeQuery(self, name)

    def rpc(self, name: str, params: dict[str, Any]) -> FakeRpc:
        return FakeRpc(self, name, params)
