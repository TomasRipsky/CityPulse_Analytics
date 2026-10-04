"""List the CSV members of remote Citi Bike ZIPs, in archive order, without downloading them.

A ZIP keeps its table of contents (the central directory) at the end of the file, so a few
HTTP range requests are enough to read it. Produces data/citibike_zip_members.csv:

    python docs/audit/citibike_zip_members.py 202501 202511 202512 202601 202602
"""

import io
import sys
import urllib.request
import zipfile


class RangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD")
        self.size = int(urllib.request.urlopen(req).headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        end = self.size - 1 if n < 0 else min(self.pos + n, self.size) - 1
        if end < self.pos:
            return b""
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        data = urllib.request.urlopen(req).read()
        self.pos += len(data)
        return data


print("month,order,member,uncompressed_bytes")
for m in sys.argv[1:]:
    zf = zipfile.ZipFile(RangeFile(f"https://s3.amazonaws.com/tripdata/{m}-citibike-tripdata.zip"))
    csvs = [i for i in zf.infolist() if i.filename.endswith(".csv")]
    for k, i in enumerate(csvs):
        print(f"{m},{k},{i.filename},{i.file_size}")
