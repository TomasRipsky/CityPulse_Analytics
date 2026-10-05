"""The lake: one root (a local folder, file:// or gs://) and the one place its layout is written.

Layout
    bronze/<source>/date=YYYY-MM-DD/<source>.json            weather, air quality: as received
    bronze/citibike/month=YYYY-MM/YYYYMM-citibike-tripdata.zip
    silver/<source>/date=YYYY-MM-DD/part.parquet             typed, true UTC instants
    silver/citibike/month=YYYY-MM/part-NNN.parquet           one part per CSV in the ZIP
    _manifests/<source>/<period>.json                        written last: "complete, and how much"
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow import fs


def bronze_day(source: str, day: date) -> str:
    return f"bronze/{source}/date={day.isoformat()}/{source}.json"


def bronze_trips(month: date) -> str:
    return f"bronze/citibike/month={month:%Y-%m}/{month:%Y%m}-citibike-tripdata.zip"


def silver_day(source: str, day: date) -> str:
    return f"silver/{source}/date={day.isoformat()}/part.parquet"


def silver_trips_dir(month: date) -> str:
    return f"silver/citibike/month={month:%Y-%m}"


def silver_trips_part(month: date, index: int) -> str:
    return f"{silver_trips_dir(month)}/part-{index:03d}.parquet"


def manifest_path(source: str, period: str) -> str:
    return f"_manifests/{source}/{period}.json"


def _resolve(uri: str) -> tuple[fs.FileSystem, str]:
    parsed = urlparse(uri)
    if parsed.scheme in ("", "file"):  # plain paths may contain spaces; file URIs may hold %20
        path = unquote(parsed.path) if parsed.scheme else uri
        return fs.LocalFileSystem(), str(Path(path).resolve())
    return fs.FileSystem.from_uri(uri)


class Lake:
    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._fs, self._root = _resolve(uri.rstrip("/"))
        self.is_local = isinstance(self._fs, fs.LocalFileSystem)

    def _path(self, rel: str) -> str:
        return f"{self._root}/{rel}"

    def _prepare(self, rel: str) -> str:
        path = self._path(rel)
        if self.is_local:  # object stores have no directories; create_dir could create buckets
            self._fs.create_dir(path.rsplit("/", 1)[0], recursive=True)
        return path

    def uri_of(self, rel: str) -> str:
        """Address of `rel` for other systems (e.g. BigQuery load jobs)."""
        return self._path(rel) if self.is_local else f"gs://{self._path(rel)}"

    def write_bytes(self, rel: str, data: bytes) -> None:
        with self._fs.open_output_stream(self._prepare(rel)) as handle:
            handle.write(data)

    def read_bytes(self, rel: str) -> bytes:
        with self._fs.open_input_stream(self._path(rel)) as handle:
            return handle.read()

    def write_json(self, rel: str, obj: Any) -> None:
        self.write_bytes(rel, json.dumps(obj, indent=2, sort_keys=True).encode())

    def read_json(self, rel: str) -> Any:
        return json.loads(self.read_bytes(rel))

    def put_file(self, rel: str, local: Path) -> None:
        fs.copy_files(str(local), self._prepare(rel), destination_filesystem=self._fs)

    def parquet_writer(self, rel: str, schema: pa.Schema) -> pq.ParquetWriter:
        return pq.ParquetWriter(self._prepare(rel), schema, filesystem=self._fs)

    def parquet_rows(self, rel: str) -> int:
        """Rows in a Parquet file, from its footer only (no data is read)."""
        with self._fs.open_input_file(self._path(rel)) as handle:
            return pq.ParquetFile(handle).metadata.num_rows

    def read_table(self, rel: str) -> pa.Table:
        # Through a file handle so pyarrow does not add hive partition columns from the path.
        with self._fs.open_input_file(self._path(rel)) as handle:
            return pq.read_table(handle)

    def exists(self, rel: str) -> bool:
        return self._fs.get_file_info(self._path(rel)).type != fs.FileType.NotFound

    def delete(self, rel: str) -> None:
        if self.exists(rel):
            self._fs.delete_file(self._path(rel))

    def list(self, rel: str) -> list[str]:
        """Files under `rel`, relative to the root, sorted."""
        selector = fs.FileSelector(self._path(rel), recursive=True, allow_not_found=True)
        prefix = f"{self._root}/"
        return sorted(
            info.path.removeprefix(prefix)
            for info in self._fs.get_file_info(selector)
            if info.type == fs.FileType.File
        )

    def delete_dir(self, rel: str) -> None:
        for path in self.list(rel):
            self._fs.delete_file(self._path(path))
