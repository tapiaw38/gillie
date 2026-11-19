from pydantic import BaseModel
from typing import List
from fastapi import UploadFile


class FileInput:
    def __init__(self, file: UploadFile):
        if not file:
            raise ValueError("File object cannot be None")
        if not hasattr(file, "filename"):
            raise ValueError("UploadFile object missing 'filename' attribute")

        if not hasattr(file, "file"):
            raise ValueError("UploadFile object missing 'file' attribute")

        self.filename = file.filename
        self.file = file.file
        self.file_header = getattr(file, "headers", {})

        try:
            if hasattr(file, "size") and file.size is not None:
                self.filesize = file.size
                print(f"FileInput init - size from file.size: {self.filesize}")
            elif (
                self.file
                and hasattr(self.file, "_file")
                and hasattr(self.file._file, "tell")
            ):
                current_pos = self.file._file.tell()
                self.file._file.seek(0, 2)
                self.filesize = self.file._file.tell()
                self.file._file.seek(current_pos)
                print(f"FileInput init - size from file._file.tell(): {self.filesize}")
            else:
                self.filesize = 0
                print("FileInput init - size defaulted to 0")
        except (AttributeError, OSError, TypeError) as e:
            print(f"FileInput init - error getting size: {e}")
            self.filesize = 0

        if not self.file:
            raise ValueError(f"File content is None for file: {self.filename}")

        print(
            f"FileInput init completed - filename: {self.filename}, size: {self.filesize}"
        )

    def __repr__(self):
        return f"FileInput(filename='{self.filename}', filesize={self.filesize}, file_type={type(self.file)})"


class FileOutputData(BaseModel):
    id: str
    name: str
    url: str


class FileOutput(BaseModel):
    data: FileOutputData

    @staticmethod
    def from_output(file: FileOutputData):
        return FileOutput(
            data=FileOutputData(
                id=file.id,
                name=file.name,
                url=file.url,
            )
        )


class FileListOutput(BaseModel):
    data: List[FileOutputData]

    @staticmethod
    def from_output(files: list[FileOutputData]):
        return FileListOutput(
            data=[FileOutput.from_output(file).data for file in files]
        )


class FileVectorStatusData(BaseModel):
    # status: "indexed" | "processing" | "not_indexed"
    statuses: dict[str, str]


class FileVectorStatusOutput(BaseModel):
    data: FileVectorStatusData

    @staticmethod
    def from_output(statuses: dict[str, str]):
        return FileVectorStatusOutput(data=FileVectorStatusData(statuses=statuses))


class FileDeleteOutputData(BaseModel):
    id: str


class FileDeleteOutput(BaseModel):
    data: FileDeleteOutputData

    @staticmethod
    def from_output(file_id: str):
        return FileDeleteOutput(
            data=FileDeleteOutputData(
                id=file_id,
            )
        )
